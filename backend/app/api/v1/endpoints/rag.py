from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Any, List
from app.schemas.rag import QueryRequest, QueryResponse, Step
from app.services.rag_service import rag_service
from app.services.hybrid_retriever import hybrid_retriever
from app.services.multilingual_service import multilingual_service

router = APIRouter()


# Models are imported from app.schemas.rag


@router.post("/query", response_model=QueryResponse)
async def query_rag(request: QueryRequest):
    try:
        # Convert Pydantic models to dicts for the service
        history_dicts = [msg.model_dump() for msg in request.history]
        
        result = rag_service.query(
            request.query, 
            target_language=request.target_language,
            history=history_dicts
        )
        
        if isinstance(result, dict):
            return QueryResponse(
                response=result.get("answer", "No answer found."),
                source=result.get("source", "Unknown"),
                score=result.get("score"),
                steps=result.get("steps", [])
            )
        else:
            return QueryResponse(response=str(result), source="Legacy RAG")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/stream")
async def stream_rag(request: QueryRequest):
    """
    Streams the response using a simple JSON-line protocol.
    """
    # Convert Pydantic models to dicts
    history_dicts = [msg.model_dump() for msg in request.history] if request.history else []
    
    return StreamingResponse(
        rag_service.stream_query(request.query, request.target_language, history_dicts),
        media_type="application/x-ndjson" 
    )


# ─── Hybrid Retrieval debug / info endpoints ──────────────────────────────────

class RetrieveRequest(BaseModel):
    query: str
    top_k: int = 5


class IndexRequest(BaseModel):
    docs: list[dict]   # [{id: str, text: str}, ...]


@router.get("/retrieval-info")
async def get_retrieval_info():
    """
    Returns current hybrid retriever status: model loading state,
    BM25 corpus size, FAISS index size.
    """
    return {
        "retriever": "Hybrid RAG",
        "dense_stage": "Pinecone (Gemini embeddings)",
        "sparse_stage": "BM25 (rank-bm25 BM25Okapi)",
        "reranker": "ms-marco-MiniLM-L-6-v2 (CrossEncoder)",
        "local_encoder": "all-MiniLM-L6-v2 (SentenceTransformer)",
        "fusion": "Reciprocal Rank Fusion (k=60)",
        "models_loaded": hybrid_retriever._loaded,
        "bm25_corpus_size": hybrid_retriever._bm25_index.size,
        "faiss_index_size": hybrid_retriever._faiss_index.size if hybrid_retriever._faiss_index else 0,
    }


@router.post("/retrieve")
async def hybrid_retrieve(request: RetrieveRequest):
    """
    Debug endpoint: run hybrid retrieval for a query and return
    the ranked chunks with scores. Does NOT call the LLM.
    """
    try:
        context_text, chunks = hybrid_retriever.retrieve_text_context(
            query=request.query,
            pinecone_retriever=rag_service.retriever,
            top_k_final=request.top_k,
        )
        return {
            "query": request.query,
            "chunks_returned": len(chunks),
            "context_preview": context_text[:500] if context_text else "",
            "chunks": [
                {
                    "doc_id": c.doc_id,
                    "score": round(c.score, 4),
                    "dense_rank": c.dense_rank,
                    "bm25_rank": c.bm25_rank,
                    "rrf_score": round(c.rrf_score, 6),
                    "text_preview": c.text[:200],
                }
                for c in chunks
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/index-local")
async def build_local_index(request: IndexRequest):
    """
    Load a list of {id, text} documents into the local BM25 + FAISS index.
    Useful after scraping new documents. Existing Pinecone index is unaffected.
    """
    try:
        docs = [(d["id"], d["text"]) for d in request.docs if "id" in d and "text" in d]
        if not docs:
            raise HTTPException(status_code=400, detail="docs must be a list of {id, text} objects")
        hybrid_retriever.build_local_index(docs)
        return {
            "status": "ok",
            "docs_indexed": len(docs),
            "bm25_size": hybrid_retriever._bm25_index.size,
            "faiss_size": hybrid_retriever._faiss_index.size if hybrid_retriever._faiss_index else 0,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Multilingual endpoints ──────────────────────────────────────────────────

class DetectLanguageRequest(BaseModel):
    text: str


@router.get("/multilingual-status")
async def get_multilingual_status():
    """
    Returns the multilingual service status:
    model name, loading state, supported languages, keyword expansion count.
    """
    return multilingual_service.get_status()


@router.post("/detect-language")
async def detect_language(request: DetectLanguageRequest):
    """
    Debug endpoint: detect language of text and preview keyword expansion.
    Returns lang_code, lang_name, confidence, is_multilingual,
    expanded_query, and scheme_hints.
    """
    try:
        result = multilingual_service.process_query(request.text)
        # Don't return the embedding array (not JSON serialisable)
        return {
            "lang_code":       result["lang_code"],
            "lang_name":       result["lang_name"],
            "confidence":      result["confidence"],
            "is_multilingual": result["is_multilingual"],
            "original_query":  result["original_query"],
            "expanded_query":  result["expanded_query"],
            "scheme_hints":    result["scheme_hints"],
            "sarvam_lang_code": result["sarvam_lang_code"],
            "ml_embedding_ready": result["ml_embedding"] is not None,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
