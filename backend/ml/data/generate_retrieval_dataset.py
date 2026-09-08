"""
generate_retrieval_dataset.py — Phase 1

Builds synthetic (query, passage, relevance) triples to domain-adapt the
RAG reranker and multilingual embedder to Indian-government-scheme content,
without needing real query logs.

Passages come from `app.services.recommendation_service.SCHEME_REGISTRY`
(read-only import) — each scheme's name + ministry + description is treated
as a retrievable passage, standing in for the real scraped scheme documents
that live in Pinecone (which this offline training script has no network
access to pull from). Queries are templated per scheme, in both plain
English and Hinglish/transliterated form using the keyword vocabulary
already defined in `app.services.multilingual_service.KEYWORD_EXPANSIONS`
(also read-only).

Positive pairs: (query about scheme X, passage for scheme X) -> label 1
Negative pairs: (query about scheme X, passage for a different scheme) -> label 0

Output: backend/ml/data/retrieval_dataset.csv  (columns: query,passage,label,lang)
"""

from __future__ import annotations

import csv
import random
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.recommendation_service import SCHEME_REGISTRY  # noqa: E402
from app.services.multilingual_service import KEYWORD_EXPANSIONS  # noqa: E402

random.seed(42)

EN_QUERY_TEMPLATES = [
    "What is {name}?",
    "Tell me about {name}",
    "What are the benefits of {name}",
    "Who is eligible for {name}",
    "How do I apply for {name}",
    "Which ministry runs {name}",
    "What documents do I need for {name}",
]

# Hindi/regional keyword -> scheme-domain concept map (subset reused from
# multilingual_service.KEYWORD_EXPANSIONS), used to build plausible
# code-mixed/Hinglish queries without needing a live translation API.
HINGLISH_TEMPLATES = [
    "{keyword} yojana ke baare mein batao",
    "{keyword} ke liye {name} kaise milega",
    "mujhe {name} ke baare mein jaankari chahiye",
    "{name} ke liye kya documents chahiye",
]


def passage_for(scheme: dict) -> str:
    return f"{scheme['name']} ({scheme['ministry']}): {scheme['description']}"


def build_rows() -> list[tuple[str, str, int, str]]:
    rows: list[tuple[str, str, int, str]] = []
    keywords = list(KEYWORD_EXPANSIONS.keys())

    for scheme in SCHEME_REGISTRY:
        passage = passage_for(scheme)

        # Positives — English
        for template in EN_QUERY_TEMPLATES:
            query = template.format(name=scheme["name"])
            rows.append((query, passage, 1, "en"))

        # Positives — Hinglish
        for template in HINGLISH_TEMPLATES:
            query = template.format(name=scheme["name"], keyword=random.choice(keywords))
            rows.append((query, passage, 1, "hi-mix"))

        # Negatives — pair this scheme's query against 2 other schemes' passages
        other_schemes = [s for s in SCHEME_REGISTRY if s["id"] != scheme["id"]]
        for _ in range(2):
            other = random.choice(other_schemes)
            template = random.choice(EN_QUERY_TEMPLATES)
            query = template.format(name=scheme["name"])
            rows.append((query, passage_for(other), 0, "en"))

    random.shuffle(rows)
    return rows


def main():
    rows = build_rows()
    out_path = Path(__file__).resolve().parent / "retrieval_dataset.csv"
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["query", "passage", "label", "lang"])
        writer.writerows(rows)

    pos = sum(1 for r in rows if r[2] == 1)
    neg = len(rows) - pos
    print(f"Wrote {len(rows)} pairs to {out_path}  ({pos} positive / {neg} negative)")


if __name__ == "__main__":
    main()
