"""
generate_ner_dataset.py — NER for automatic scheme-data extraction

`SCHEME_REGISTRY` (read-only import) is hand-curated today — name,
ministry, description, and structured eligibility criteria are typed in
by a person. This is the one piece of the whole pipeline still 100%
manual, and the highest real-world-value ML addition of everything built
in this pass: a named-entity-recognition model that can pull structured
facts (benefit amounts, age eligibility, interest rates, the scheme name
and ministry itself) back out of newly scraped free-text scheme
documents (scraper_service.py already fetches these), so extending the
registry stops requiring someone to hand-transcribe every new document.

Entity types: SCHEME, MINISTRY, AMOUNT (₹ figures), AGE (age eligibility
phrases), PCT (interest/percentage figures).

Templated sentences built from real SCHEME_REGISTRY data (names,
ministries, descriptions already contain real ₹ amounts and percentages;
age criteria come from each scheme's own `criteria` list) — BIO tags are
assigned automatically since we know exactly which substring is which
entity by construction.

Output: backend/ml/data/ner_dataset.json — list of {tokens: [...], tags: [...]}
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.recommendation_service import SCHEME_REGISTRY  # noqa: E402

MONEY_RE = re.compile(r"₹[\d,]+(?:\.\d+)?\s*(?:lakh|crore)?")
PCT_RE = re.compile(r"\d+(?:\.\d+)?%")
TOKEN_RE = re.compile(r"₹?[\w%.,-]+")


def tokenize_with_spans(text: str):
    """Whitespace/punct tokenizer that also returns each token's (start, end) span."""
    tokens, spans = [], []
    for m in TOKEN_RE.finditer(text):
        tokens.append(m.group())
        spans.append((m.start(), m.end()))
    return tokens, spans


def bio_tags_for_spans(spans: list[tuple[int, int]], entity_spans: list[tuple[int, int, str]]) -> list[str]:
    """entity_spans: list of (start, end, label). Returns BIO tag per token."""
    tags = ["O"] * len(spans)
    for ent_start, ent_end, label in entity_spans:
        first = True
        for i, (tok_start, tok_end) in enumerate(spans):
            if tok_start >= ent_start and tok_end <= ent_end:
                tags[i] = f"B-{label}" if first else f"I-{label}"
                first = False
    return tags


def age_phrase_for(scheme: dict) -> str | None:
    for c in scheme["criteria"]:
        if c["field"] == "age":
            if c["op"] == "range":
                lo, hi = c["value"]
                return f"{lo} to {hi} years"
            if c["op"] == "gte":
                return f"{c['value']}+ years"
    return None


def find_entity_spans(sentence: str, scheme: dict) -> list[tuple[int, int, str]]:
    spans = []
    for m in re.finditer(re.escape(scheme["name"]), sentence):
        spans.append((m.start(), m.end(), "SCHEME"))
    for m in re.finditer(re.escape(scheme["ministry"]), sentence):
        spans.append((m.start(), m.end(), "MINISTRY"))
    for m in MONEY_RE.finditer(sentence):
        spans.append((m.start(), m.end(), "AMOUNT"))
    for m in PCT_RE.finditer(sentence):
        spans.append((m.start(), m.end(), "PCT"))
    age = age_phrase_for(scheme)
    if age:
        for m in re.finditer(re.escape(age), sentence):
            spans.append((m.start(), m.end(), "AGE"))
    return spans


def build_examples_for(scheme: dict) -> list[dict]:
    examples = []
    sentences = [
        f"{scheme['name']} is administered by {scheme['ministry']} and provides {scheme['description']}",
        f"Under {scheme['name']}, run by {scheme['ministry']}: {scheme['description']}",
        f"{scheme['description']} This is provided under {scheme['name']} ({scheme['ministry']}).",
        f"{scheme['name']} gives eligible applicants {scheme['description']}",
        f"You can benefit from {scheme['name']}, a programme by {scheme['ministry']}, which offers {scheme['description']}",
        f"{scheme['ministry']} runs {scheme['name']}, which offers {scheme['description']}",
        f"For more on {scheme['name']}: {scheme['description']} It is managed by {scheme['ministry']}.",
    ]
    age = age_phrase_for(scheme)
    if age:
        sentences.append(f"Applicants must be {age} old to apply for {scheme['name']}.")
        sentences.append(f"{scheme['name']} is open to applicants aged {age}.")
        sentences.append(f"To apply for {scheme['name']}, you need to be {age} old.")

    for sentence in sentences:
        tokens, spans = tokenize_with_spans(sentence)
        entity_spans = find_entity_spans(sentence, scheme)
        tags = bio_tags_for_spans(spans, entity_spans)
        examples.append({"tokens": tokens, "tags": tags})
    return examples


def main():
    examples = []
    for scheme in SCHEME_REGISTRY:
        examples.extend(build_examples_for(scheme))

    out_path = Path(__file__).resolve().parent / "ner_dataset.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(examples, f, indent=2)

    entity_counts: dict[str, int] = {}
    for ex in examples:
        for tag in ex["tags"]:
            if tag.startswith("B-"):
                entity_counts[tag[2:]] = entity_counts.get(tag[2:], 0) + 1

    print(f"Wrote {len(examples)} BIO-tagged sentences to {out_path}")
    print(f"Entity counts: {entity_counts}")


if __name__ == "__main__":
    main()
