"""
groundedness_features.py — shared feature extraction

Used by BOTH train_groundedness_classifier.py and
app/services/ml_groundedness_service.py, so training and serving can
never drift out of sync with each other (a lesson from earlier in this
build: keep feature engineering in exactly one place).

Reuses `all-MiniLM-L6-v2` (already a dependency via sentence-transformers,
the same bi-encoder hybrid_retriever.py uses) rather than adding a new
model just for this.
"""

from __future__ import annotations

import re

FEATURE_NAMES = ["word_overlap_ratio", "embedding_cosine_sim", "length_ratio", "numeric_mismatch"]

_embedder = None


def _get_embedder():
    global _embedder
    if _embedder is None:
        from sentence_transformers import SentenceTransformer
        _embedder = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedder


def extract_features(context: str, answer: str) -> dict:
    context = context or ""
    answer = answer or ""

    context_words = set(re.findall(r"[a-z]+", context.lower()))
    answer_words = re.findall(r"[a-z]+", answer.lower())
    answer_word_set = set(answer_words)
    overlap = len(context_words & answer_word_set) / max(1, len(answer_word_set))

    embedder = _get_embedder()
    from sentence_transformers.util import cos_sim
    emb = embedder.encode([context, answer], convert_to_tensor=True, normalize_embeddings=True)
    cosine_sim = float(cos_sim(emb[0:1], emb[1:2])[0][0])

    length_ratio = min(len(answer) / max(1, len(context)), 5.0)  # cap outliers

    context_numbers = set(re.findall(r"\d[\d,]*", context))
    answer_numbers = set(re.findall(r"\d[\d,]*", answer))
    numeric_mismatch = 1 if (answer_numbers - context_numbers) else 0

    return {
        "word_overlap_ratio": round(overlap, 4),
        "embedding_cosine_sim": round(cosine_sim, 4),
        "length_ratio": round(length_ratio, 4),
        "numeric_mismatch": numeric_mismatch,
    }
