"""
hybrid_retriever.py
Hybrid RAG Retrieval + Cross-Encoder Re-ranking Pipeline.

Architecture:
  Stage 1 — DUAL RETRIEVAL (run in parallel):
    A) Dense (Semantic)  : Pinecone vector search via existing retriever
    B) Sparse (Keyword)  : BM25 on an in-memory corpus built from Pinecone docs

  Stage 2 — FUSION:
    Reciprocal Rank Fusion (RRF) merges A + B into a single deduplicated candidate list
    without needing a shared score scale.

  Stage 3 — CROSS-ENCODER RE-RANKING:
    ms-marco-MiniLM-L-6-v2 cross-encoder scores each (query, doc) pair precisely.
    Returns top-K re-ranked results.

No fine-tuning — purely inference-time use of pretrained models:
  - Bi-encoder : all-MiniLM-L6-v2     (fast candidate encoding for FAISS local index)
  - Cross-encoder: ms-marco-MiniLM-L-6-v2  (precise reranking)
  - BM25       : rank-bm25 BM25Okapi   (lexical keyword matching)

The existing Pinecone/Gemini RAG is preserved and enhanced — this replaces
the single self.retriever.retrieve(query) call with the full hybrid pipeline.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

import numpy as np
import faiss
from rank_bm25 import BM25Okapi

# sentence_transformers is imported lazily inside _ensure_loaded()
# so that torch DLL issues don't crash the server on startup.
# The models are downloaded and loaded on the first actual query.

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pretrained models (inference-only, no fine-tuning)
# ---------------------------------------------------------------------------

BIENCODER_MODEL    = "all-MiniLM-L6-v2"
CROSSENCODER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
MULTILINGUAL_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class RetrievedChunk:
    """A single retrieved document chunk with its provenance."""
    doc_id: str
    text: str
    score: float          # Final score after re-ranking (cross-encoder logit)
    dense_rank: int = 0   # Rank from Pinecone dense retrieval (0 = not in dense)
    bm25_rank: int = 0    # Rank from BM25 sparse retrieval (0 = not in sparse)
    rrf_score: float = 0.0
    metadata: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Reciprocal Rank Fusion
# ---------------------------------------------------------------------------

def reciprocal_rank_fusion(
    *ranked_lists: list[tuple[str, Any]],
    k: int = 60,
) -> list[tuple[str, float]]:
    """
    Merge multiple ranked lists via RRF.
    Each list is [(doc_id, _), ...] ordered best-first.
    Returns [(doc_id, rrf_score), ...] sorted descending.
    k=60 is the standard RRF constant (Robertson & Zaragoza, 2009).
    """
    scores: dict[str, float] = {}
    for ranked in ranked_lists:
        for rank, (doc_id, _) in enumerate(ranked, start=1):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)


# ---------------------------------------------------------------------------
# BM25 In-Memory Index
# ---------------------------------------------------------------------------

class BM25Index:
    """
    Thin wrapper around rank-bm25 BM25Okapi.
    Built lazily from a corpus of (doc_id, text) pairs.
    """

    def __init__(self):
        self._doc_ids: list[str] = []
        self._texts: list[str] = []
        self._bm25: BM25Okapi | None = None

    def build(self, docs: list[tuple[str, str]]):
        """Build index from list of (doc_id, text) pairs."""
        if not docs:
            return
        self._doc_ids = [d[0] for d in docs]
        self._texts   = [d[1] for d in docs]

        # Tokenise: simple whitespace split (sufficient for BM25)
        tokenised = [t.lower().split() for t in self._texts]
        self._bm25 = BM25Okapi(tokenised)
        logger.info(f"BM25 index built with {len(self._doc_ids)} docs")

    def query(self, query_text: str, top_k: int = 10) -> list[tuple[str, float]]:
        """Returns [(doc_id, bm25_score), ...] best-first."""
        if self._bm25 is None or not self._doc_ids:
            return []
        tokens = query_text.lower().split()
        scores = self._bm25.get_scores(tokens)
        ranked = sorted(zip(self._doc_ids, scores), key=lambda x: x[1], reverse=True)
        return ranked[:top_k]

    @property
    def size(self) -> int:
        return len(self._doc_ids)


# ---------------------------------------------------------------------------
# FAISS Local Dense Index (bi-encoder)
# ---------------------------------------------------------------------------

class FAISSIndex:
    """
    Local FAISS flat L2 index backed by all-MiniLM-L6-v2 embeddings.
    Used as an alternative/supplement to Pinecone for dense retrieval
    when a local corpus is available (e.g., scraped docs in memory).
    Falls back gracefully if corpus is empty.
    """

    def __init__(self, model: Any):  # model is SentenceTransformer, lazy-imported
        self._model = model
        self._index: faiss.IndexFlatIP | None = None
        self._doc_ids: list[str] = []
        self._texts: list[str] = []

    def build(self, docs: list[tuple[str, str]], batch_size: int = 32):
        """Build FAISS index from (doc_id, text) pairs."""
        if not docs:
            return
        self._doc_ids = [d[0] for d in docs]
        self._texts   = [d[1] for d in docs]

        logger.info(f"Encoding {len(docs)} docs with bi-encoder…")
        embeddings = self._model.encode(
            [d[1] for d in docs],
            batch_size=batch_size,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        dim = embeddings.shape[1]
        self._index = faiss.IndexFlatIP(dim)   # Inner-product = cosine on normalised vecs
        self._index.add(embeddings.astype(np.float32))
        logger.info(f"FAISS index built: {self._index.ntotal} vectors, dim={dim}")

    def query(self, query_text: str, top_k: int = 10) -> list[tuple[str, float]]:
        """Returns [(doc_id, cosine_score), ...] best-first."""
        if self._index is None or self._index.ntotal == 0:
            return []
        q_emb = self._model.encode(
            [query_text], normalize_embeddings=True, convert_to_numpy=True
        ).astype(np.float32)
        scores, idxs = self._index.search(q_emb, min(top_k, self._index.ntotal))
        results = []
        for score, idx in zip(scores[0], idxs[0]):
            if idx >= 0:
                results.append((self._doc_ids[idx], float(score)))
        return results

    @property
    def size(self) -> int:
        return len(self._doc_ids)


# ---------------------------------------------------------------------------
# Hybrid Retriever
# ---------------------------------------------------------------------------

class HybridRetriever:
    """
    Full Hybrid RAG retrieval pipeline:
      1. Pinecone dense retrieval  (existing Gemini embeddings)
      2. BM25 sparse retrieval     (local in-memory index)
      3. RRF fusion                (merge ranks without score normalisation)
      4. Cross-encoder re-ranking  (ms-marco-MiniLM-L-6-v2)

    Designed to plug in alongside the existing RAGService — it wraps the
    existing `retriever` and augments it with BM25 + re-ranking.
    """

    def __init__(self):
        self._loaded = False
        self._bi_encoder = None   # SentenceTransformer, lazy-loaded
        self._cross_encoder = None  # CrossEncoder, lazy-loaded
        self._bm25_index = BM25Index()
        self._faiss_index: FAISSIndex | None = None

    # ── Lazy model loading ────────────────────────────────────────────────

    def _ensure_loaded(self):
        """Load models on first use (lazy — imports sentence_transformers here
        so that torch DLL issues don't crash server startup)."""
        if self._loaded:
            return
        t0 = time.time()
        try:
            from sentence_transformers import SentenceTransformer, CrossEncoder  # noqa: PLC0415
        except ImportError as e:
            raise RuntimeError(
                "sentence-transformers not installed or torch DLL failed to load. "
                "Run: pip install sentence-transformers"
            ) from e

        logger.info("Loading bi-encoder (all-MiniLM-L6-v2)…")
        self._bi_encoder = SentenceTransformer(BIENCODER_MODEL)
        self._faiss_index = FAISSIndex(self._bi_encoder)

        logger.info("Loading cross-encoder (ms-marco-MiniLM-L-6-v2)…")
        self._cross_encoder = CrossEncoder(CROSSENCODER_MODEL, max_length=512)
        self._loaded = True
        logger.info(f"Hybrid retriever models loaded in {time.time()-t0:.1f}s")

    # ── Corpus building ───────────────────────────────────────────────────

    def build_local_index(self, docs: list[tuple[str, str]]):
        """
        Build BM25 + FAISS from a list of (doc_id, text) pairs.
        Call this after scraping / loading documents into memory.
        Pinecone dense retrieval still works independently for its own corpus.
        """
        self._ensure_loaded()
        self._bm25_index.build(docs)
        self._faiss_index.build(docs)
        logger.info(f"Local hybrid index built: {len(docs)} docs")

    # ── Core retrieval ────────────────────────────────────────────────────

    def retrieve(
        self,
        query: str,
        pinecone_retriever,          # existing llama-index retriever
        top_k_dense: int = 10,
        top_k_sparse: int = 10,
        top_k_final: int = 5,
        ml_info: dict | None = None,  # output of multilingual_service.process_query()
    ) -> list[RetrievedChunk]:
        """
        Full hybrid retrieval + cross-encoder re-ranking.

        Args:
            query            : User query string
            pinecone_retriever: existing self.retriever from RAGService
            top_k_dense      : candidates from Pinecone dense stage
            top_k_sparse     : candidates from BM25 sparse stage
            top_k_final      : final results after cross-encoder re-ranking
            ml_info          : optional dict from multilingual_service.process_query()
                               Enables Stage 1D: multilingual FAISS retrieval

        Returns:
            list[RetrievedChunk] sorted by cross-encoder score descending
        """
        self._ensure_loaded()
        t_start = time.time()

        # ── Stage 1A: Pinecone Dense Retrieval ──────────────────────────
        dense_nodes = []
        dense_ranked: list[tuple[str, float]] = []
        try:
            # Use the existing llama-index retriever (Gemini embeddings → Pinecone)
            raw_nodes = pinecone_retriever.retrieve(query)
            for i, node in enumerate(raw_nodes[:top_k_dense]):
                doc_id = str(node.node_id or f"dense_{i}")
                text = node.get_content()
                score = float(node.score or 0.0)
                dense_nodes.append((doc_id, text, score, node.metadata if hasattr(node, 'metadata') else {}))
                dense_ranked.append((doc_id, score))
            logger.info(f"Dense retrieval: {len(dense_ranked)} results")
        except Exception as e:
            logger.warning(f"Dense (Pinecone) retrieval failed: {e}")

        # ── Stage 1B: BM25 Sparse Retrieval ─────────────────────────────
        # Use expanded query if available (adds English synonyms for Indian-language queries)
        bm25_query = ml_info["expanded_query"] if ml_info else query
        bm25_ranked: list[tuple[str, float]] = []
        bm25_texts: dict[str, str] = {}
        if self._bm25_index.size > 0:
            try:
                bm25_ranked = self._bm25_index.query(bm25_query, top_k=top_k_sparse)
                for doc_id, score in bm25_ranked:
                    idx = self._bm25_index._doc_ids.index(doc_id)
                    bm25_texts[doc_id] = self._bm25_index._texts[idx]
                logger.info(f"BM25 retrieval: {len(bm25_ranked)} results")
            except Exception as e:
                logger.warning(f"BM25 retrieval failed: {e}")
        else:
            logger.debug("BM25 index empty — sparse stage skipped")

        # ── Stage 1C: Local FAISS Dense (if local corpus available) ──────
        faiss_ranked: list[tuple[str, float]] = []
        if self._faiss_index and self._faiss_index.size > 0:
            try:
                faiss_ranked = self._faiss_index.query(query, top_k=top_k_dense)
                logger.info(f"FAISS retrieval: {len(faiss_ranked)} results")
            except Exception as e:
                logger.warning(f"FAISS retrieval failed: {e}")

        # ── Stage 1D: Multilingual FAISS (non-English queries only) ──────
        ml_faiss_ranked: list[tuple[str, float]] = []
        if ml_info and ml_info.get("is_multilingual") and ml_info.get("ml_embedding") is not None:
            if self._faiss_index and self._faiss_index.size > 0 and self._faiss_index._index is not None:
                try:
                    q_emb = ml_info["ml_embedding"].astype(np.float32)
                    # Resize embedding if dimension mismatch (multilingual=512, bi-encoder=384)
                    if self._faiss_index._index.d != q_emb.shape[1]:
                        logger.debug(f"ML embedding dim {q_emb.shape[1]} != FAISS dim {self._faiss_index._index.d} — skipping ML FAISS")
                    else:
                        scores, idxs = self._faiss_index._index.search(q_emb, min(top_k_dense, self._faiss_index._index.ntotal))
                        for score, idx in zip(scores[0], idxs[0]):
                            if idx >= 0:
                                ml_faiss_ranked.append((self._faiss_index._doc_ids[idx], float(score)))
                        logger.info(f"Multilingual FAISS retrieval: {len(ml_faiss_ranked)} results")
                except Exception as e:
                    logger.warning(f"Multilingual FAISS retrieval failed: {e}")

        # ── Stage 2: RRF Fusion ──────────────────────────────────────────
        active_lists = [l for l in [dense_ranked, bm25_ranked, faiss_ranked, ml_faiss_ranked] if l]
        if not active_lists:
            logger.warning("All retrieval stages returned empty — returning no results")
            return []

        fused = reciprocal_rank_fusion(*active_lists)  # [(doc_id, rrf_score), ...]
        logger.info(f"RRF fusion: {len(fused)} unique candidates")

        # ── Build candidate text map ─────────────────────────────────────
        # dense_nodes provides (doc_id, text, score, metadata) for Pinecone results
        dense_map: dict[str, tuple[str, float, dict]] = {
            dn[0]: (dn[1], dn[2], dn[3]) for dn in dense_nodes
        }

        # ── Stage 3: Collect candidate texts ────────────────────────────
        candidates: list[RetrievedChunk] = []
        dense_id_set = {dn[0] for dn in dense_ranked}
        bm25_id_set  = {b[0] for b in bm25_ranked}

        for rank_pos, (doc_id, rrf_score) in enumerate(fused):
            # Find text
            if doc_id in dense_map:
                text, orig_score, meta = dense_map[doc_id]
            elif doc_id in bm25_texts:
                text = bm25_texts[doc_id]
                orig_score = 0.0
                meta = {}
            else:
                continue  # Can't find text — skip

            if not text or len(text.strip()) < 10:
                continue

            # Determine which retrieval ranks contributed
            dr = next((i+1 for i, (d, _) in enumerate(dense_ranked) if d == doc_id), 0)
            br = next((i+1 for i, (d, _) in enumerate(bm25_ranked)  if d == doc_id), 0)

            candidates.append(RetrievedChunk(
                doc_id=doc_id,
                text=text,
                score=orig_score,
                dense_rank=dr,
                bm25_rank=br,
                rrf_score=rrf_score,
                metadata=meta,
            ))

        if not candidates:
            return []

        # ── Stage 4: Cross-Encoder Re-ranking ────────────────────────────
        # Truncate candidate text to avoid token overflow in cross-encoder
        MAX_CHARS = 800
        pairs = [(query, c.text[:MAX_CHARS]) for c in candidates]

        try:
            ce_scores = self._cross_encoder.predict(pairs, show_progress_bar=False)
            for chunk, ce_score in zip(candidates, ce_scores):
                chunk.score = float(ce_score)
            candidates.sort(key=lambda c: c.score, reverse=True)
            logger.info(
                f"Cross-encoder re-ranked {len(candidates)} candidates. "
                f"Top score: {candidates[0].score:.3f}"
            )
        except Exception as e:
            logger.warning(f"Cross-encoder failed, using RRF order: {e}")
            # Fall back to RRF order
            for chunk in candidates:
                chunk.score = chunk.rrf_score

        elapsed = time.time() - t_start
        logger.info(f"Hybrid retrieval complete in {elapsed:.2f}s — returning top {top_k_final}")
        return candidates[:top_k_final]

    def retrieve_text_context(
        self,
        query: str,
        pinecone_retriever,
        top_k_final: int = 5,
        ml_info: dict | None = None,
    ) -> tuple[str, list[RetrievedChunk]]:
        """
        Convenience wrapper: returns (context_text, chunks).
        context_text is the concatenated text of top_k_final chunks,
        ready to paste directly into the LLM prompt.
        ml_info: optional output from multilingual_service.process_query()
        """
        chunks = self.retrieve(query, pinecone_retriever, top_k_final=top_k_final, ml_info=ml_info)
        if not chunks:
            return "", []
        # Note what retrieval paths contributed per chunk
        context = "\n\n---\n\n".join(
            f"[Source {i+1} | Score: {c.score:.2f} | Dense:{c.dense_rank} BM25:{c.bm25_rank}]\n{c.text}"
            for i, c in enumerate(chunks)
        )
        return context, chunks


# Singleton — shared across app (models loaded once)
hybrid_retriever = HybridRetriever()
