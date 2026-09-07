"""
multilingual_service.py
========================
Multilingual support for Gramin Saathi RAG pipeline.

Capabilities
------------
1. Language Detection
   - Uses `langdetect` (fast, offline, no API key).
   - Maps ISO 639-1 codes to human-readable names and script families.

2. Query Normalisation
   - Transliterates Roman-script Indian-language queries (Hinglish etc.)
     to a canonical ASCII form that BM25 / keyword matching can handle.

3. Multilingual Dense Embedding
   - Model: `paraphrase-multilingual-MiniLM-L12-v2`
     • 118MB, supports 50+ languages incl. hi, ta, te, kn, ml, gu, mr, bn, pa
     • Inference-only, no fine-tuning.
   - Used as a SECOND dense retrieval stage specifically for non-English queries,
     alongside the existing Gemini (English-optimised) embeddings.

4. Language-Aware Hybrid Retrieval Hook
   - `enrich_query_for_retrieval(query, detected_lang)` returns a dict the
     hybrid retriever uses to decide whether to run the multilingual encoder path.

Design
------
- All model loading is lazy (first call only) — does NOT slow down server startup.
- Falls back gracefully: if detection or encoding fails, the original query
  is returned unchanged and the English RAG path continues.
- No training data, no fine-tuning, no API calls for NLP tasks.

Supported Indian Languages
--------------------------
hi  Hindi        | bn  Bengali     | mr  Marathi
ta  Tamil        | te  Telugu      | kn  Kannada
ml  Malayalam    | gu  Gujarati    | pa  Punjabi
ur  Urdu         | or  Odia        | as  Assamese
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Human-readable language names (ISO 639-1 → display name)
LANGUAGE_NAMES: dict[str, str] = {
    "en": "English",
    "hi": "Hindi",
    "ta": "Tamil",
    "te": "Telugu",
    "kn": "Kannada",
    "ml": "Malayalam",
    "gu": "Gujarati",
    "mr": "Marathi",
    "bn": "Bengali",
    "pa": "Punjabi",
    "ur": "Urdu",
    "or": "Odia",
    "as": "Assamese",
    "sa": "Sanskrit",
}

# Languages that benefit from multilingual embedding (non-English)
MULTILINGUAL_LANGS = set(LANGUAGE_NAMES.keys()) - {"en"}

# Pretrained multilingual bi-encoder (inference-only)
# Trained on 50+ languages, 512-dim embeddings, 118MB
MULTILINGUAL_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"

# Sarvam/Google translate language codes for each ISO 639-1 code
SARVAM_LANG_MAP: dict[str, str] = {
    "hi": "hi-IN", "ta": "ta-IN", "te": "te-IN",
    "kn": "kn-IN", "ml": "ml-IN", "gu": "gu-IN",
    "mr": "mr-IN", "bn": "bn-IN", "pa": "pa-IN",
}

# Keyword expansions for common Hinglish/Indian-language scheme-related terms
# These are appended to queries to improve BM25 recall
KEYWORD_EXPANSIONS: dict[str, list[str]] = {
    # Hindi scheme keywords → English equivalents
    "kisan": ["farmer", "agriculture", "PM-KISAN"],
    "kisaan": ["farmer", "agriculture", "PM-KISAN"],
    "yojana": ["scheme", "government scheme", "welfare"],
    "sarkar": ["government", "central government", "state government"],
    "pension": ["pension", "retirement benefit", "social security"],
    "berojgari": ["unemployment", "employment", "job"],
    "beti": ["girl child", "daughter", "girl education"],
    "swasthya": ["health", "healthcare", "medical"],
    "awas": ["housing", "home", "shelter", "pradhan mantri awas"],
    "ujjwala": ["LPG", "cooking gas", "fuel subsidy"],
    "ration": ["food security", "PDS", "public distribution"],
    "aadhar": ["Aadhaar", "identity", "biometric"],
    "mudra": ["MUDRA loan", "business loan", "micro enterprise"],
    "fasal": ["crop", "agriculture", "farm", "kharif", "rabi"],
    "bima": ["insurance", "crop insurance", "PMFBY"],
    "shiksha": ["education", "school", "scholarship"],
    "rozgar": ["employment", "job", "MGNREGA", "work"],
    "mahila": ["women", "female", "women empowerment"],
    "divyang": ["disabled", "disability", "specially abled"],
    "vriddha": ["elderly", "senior citizen", "old age"],
    "garib": ["poor", "below poverty line", "BPL"],
    "gramin": ["rural", "village", "gram panchayat"],
    "sahayata": ["assistance", "support", "subsidy", "help"],
}


# ---------------------------------------------------------------------------
# Language Detector
# ---------------------------------------------------------------------------

class LanguageDetector:
    """
    Wraps langdetect for robust language identification.
    Returns ISO 639-1 codes ('hi', 'ta', 'en', etc.)
    """

    def __init__(self):
        self._ready = False

    def _ensure_ready(self):
        if self._ready:
            return
        try:
            import langdetect  # noqa: F401
            from langdetect import DetectorFactory
            DetectorFactory.seed = 42  # deterministic results
            self._ready = True
            logger.info("langdetect initialised")
        except ImportError:
            logger.warning("langdetect not installed — language detection disabled")

    def detect(self, text: str) -> str:
        """
        Detect language of text. Returns ISO 639-1 code.
        Returns 'en' if detection fails or text is too short.
        """
        self._ensure_ready()
        if not self._ready or not text or len(text.strip()) < 5:
            return "en"
        try:
            from langdetect import detect as _detect
            lang = _detect(text.strip())
            # Normalise: langdetect returns 'zh-cn' etc. — take first part
            return lang.split("-")[0].lower()
        except Exception:
            return "en"

    def detect_with_confidence(self, text: str) -> tuple[str, float]:
        """
        Returns (lang_code, probability). Falls back to ('en', 1.0).
        """
        self._ensure_ready()
        if not self._ready or not text or len(text.strip()) < 5:
            return "en", 1.0
        try:
            from langdetect import detect_langs
            results = detect_langs(text.strip())
            if results:
                top = results[0]
                return top.lang.split("-")[0].lower(), round(top.prob, 3)
        except Exception:
            pass
        return "en", 1.0


# ---------------------------------------------------------------------------
# Multilingual Embedder
# ---------------------------------------------------------------------------

class MultilingualEmbedder:
    """
    Wraps `paraphrase-multilingual-MiniLM-L12-v2` for producing
    multilingual dense embeddings. Lazy-loaded on first use.
    """

    def __init__(self):
        self._model = None
        self._loaded = False

    def _ensure_loaded(self):
        if self._loaded:
            return
        try:
            from sentence_transformers import SentenceTransformer  # noqa: PLC0415
            import torch
            logger.info(f"Loading multilingual bi-encoder: {MULTILINGUAL_MODEL}…")
            device = "cuda" if torch.cuda.is_available() else "cpu"
            self._model = SentenceTransformer(MULTILINGUAL_MODEL, device=device)
            self._loaded = True
            logger.info(f"Multilingual embedder ready on {device}")
        except Exception as e:
            logger.warning(f"Failed to load multilingual embedder: {e}")
            self._model = None

    def encode(self, texts: list[str], normalize: bool = True):
        """
        Encode texts into multilingual embeddings.
        Returns numpy float32 array of shape (N, 512) or None on failure.
        """
        self._ensure_loaded()
        if self._model is None:
            return None
        try:
            import numpy as np
            embeddings = self._model.encode(
                texts,
                normalize_embeddings=normalize,
                convert_to_numpy=True,
                show_progress_bar=False,
                batch_size=32,
            )
            return embeddings.astype(np.float32)
        except Exception as e:
            logger.warning(f"Multilingual encoding failed: {e}")
            return None

    def encode_query(self, query: str):
        """Encode a single query. Returns (1, 512) array or None."""
        result = self.encode([query])
        return result[0:1] if result is not None else None

    @property
    def is_loaded(self) -> bool:
        return self._loaded and self._model is not None


# ---------------------------------------------------------------------------
# Query Expander (keyword-level BM25 enrichment for Indian languages)
# ---------------------------------------------------------------------------

class QueryExpander:
    """
    Adds English keyword synonyms to non-English queries so that
    BM25 can still find relevant English documents.

    Example:
      Input:  "PM kisan yojana ke liye kya documents chahiye"
      Output: "PM kisan yojana ke liye kya documents chahiye
               farmer agriculture PM-KISAN scheme government scheme welfare"
    """

    @staticmethod
    def expand(query: str, detected_lang: str) -> str:
        """
        Returns enriched query string.
        Appends English equivalents for recognised Indian-language keywords.
        """
        if detected_lang == "en":
            return query   # No expansion needed

        expansions: list[str] = []
        q_lower = query.lower()
        for keyword, synonyms in KEYWORD_EXPANSIONS.items():
            if keyword in q_lower:
                expansions.extend(synonyms)

        if not expansions:
            return query

        expanded = query.strip() + "\n" + " ".join(dict.fromkeys(expansions))  # deduplicate
        logger.debug(f"Query expanded: added {len(expansions)} English terms")
        return expanded

    @staticmethod
    def extract_scheme_hints(query: str) -> list[str]:
        """
        Extract likely scheme names or keywords from query for metadata filtering.
        Returns a list of candidate scheme name tokens.
        """
        # Common scheme name patterns
        SCHEME_PATTERNS = [
            r"PM[- ]?KISAN",
            r"PMAY", r"Pradhan Mantri Awas",
            r"Ayushman Bharat", r"PMJAY",
            r"MGNREGA", r"MNREGA",
            r"PMFBY",
            r"Ujjwala",
            r"Sukanya Samriddhi",
            r"Atal Pension",
            r"Jan Dhan",
            r"Mudra",
            r"Stand[- ]?Up India",
            r"Start[- ]?Up India",
        ]
        found = []
        for pat in SCHEME_PATTERNS:
            if re.search(pat, query, re.IGNORECASE):
                found.append(re.search(pat, query, re.IGNORECASE).group())
        return found


# ---------------------------------------------------------------------------
# Main Multilingual Service
# ---------------------------------------------------------------------------

class MultilingualService:
    """
    Orchestrator for all multilingual NLP operations in the RAG pipeline.

    Usage in stream_query / retrieve:
        result = multilingual_service.process_query(query)
        # result.expanded_query → use for BM25
        # result.lang_code      → pass to LLM for response language
        # result.ml_embedding   → use as extra dense retrieval stage (FAISS)
    """

    def __init__(self):
        self.detector = LanguageDetector()
        self.embedder = MultilingualEmbedder()
        self.expander = QueryExpander()

    def detect_language(self, query: str) -> tuple[str, str, float]:
        """
        Returns (lang_code, lang_name, confidence).
        e.g. ('hi', 'Hindi', 0.97)
        """
        code, conf = self.detector.detect_with_confidence(query)
        name = LANGUAGE_NAMES.get(code, code.upper())
        return code, name, conf

    def process_query(self, query: str) -> dict:
        """
        Full multilingual query processing.

        Returns dict with:
          lang_code        : ISO 639-1 code ('hi', 'en', ...)
          lang_name        : Human-readable ('Hindi', 'English', ...)
          confidence       : Detection confidence 0–1
          is_multilingual  : True if non-English
          expanded_query   : Query + English keyword expansions (for BM25)
          scheme_hints     : List of likely scheme names found in query
          ml_embedding     : numpy array (1, 512) or None (lazy — first call loads model)
          sarvam_lang_code : e.g. 'hi-IN' for TTS/translation
        """
        lang_code, lang_name, confidence = self.detect_language(query)
        is_multilingual = lang_code in MULTILINGUAL_LANGS

        # Expand query with English synonyms for BM25
        expanded = self.expander.expand(query, lang_code)
        scheme_hints = self.expander.extract_scheme_hints(query)

        # Generate multilingual embedding (lazy — loads model on first call)
        ml_embedding = None
        if is_multilingual:
            try:
                ml_embedding = self.embedder.encode_query(expanded)
            except Exception as e:
                logger.warning(f"ML embedding skipped: {e}")

        sarvam_code = SARVAM_LANG_MAP.get(lang_code, "en-IN")

        logger.info(
            f"[Multilingual] lang={lang_code}({confidence:.2f}) "
            f"expanded={len(expanded)-len(query)} chars added "
            f"ml_embedding={'yes' if ml_embedding is not None else 'no'}"
        )

        return {
            "lang_code": lang_code,
            "lang_name": lang_name,
            "confidence": confidence,
            "is_multilingual": is_multilingual,
            "expanded_query": expanded,
            "original_query": query,
            "scheme_hints": scheme_hints,
            "ml_embedding": ml_embedding,
            "sarvam_lang_code": sarvam_code,
        }

    def get_status(self) -> dict:
        return {
            "multilingual_model": MULTILINGUAL_MODEL,
            "multilingual_model_loaded": self.embedder.is_loaded,
            "langdetect_ready": self.detector._ready,
            "supported_languages": LANGUAGE_NAMES,
            "keyword_expansion_terms": len(KEYWORD_EXPANSIONS),
        }


# Singleton
multilingual_service = MultilingualService()
