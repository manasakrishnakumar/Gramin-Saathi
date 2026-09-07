"""
ner_features.py — shared CRF feature extraction for scheme-data NER.

Used by BOTH train_ner_model.py and app/services/ml_ner_service.py, same
reasoning as groundedness_features.py: one place for feature engineering,
so training and serving can't drift apart.

Also exposes the tokenizer, so span reconstruction (turning predicted BIO
tags back into entity text + type) is identical between training-time
evaluation and live serving.
"""

from __future__ import annotations

import re

TOKEN_RE = re.compile(r"₹?[\w%.,-]+")


def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text)


def word2features(tokens: list[str], i: int) -> dict:
    word = tokens[i]
    features = {
        "bias": 1.0,
        "word.lower": word.lower(),
        "word[-3:]": word[-3:],
        "word[-2:]": word[-2:],
        "word.isupper": word.isupper(),
        "word.istitle": word.istitle(),
        "word.isdigit": word.isdigit(),
        "word.has_rupee": word.startswith("₹"),
        "word.has_pct": "%" in word,
        "word.has_comma_digits": bool(re.search(r"\d,\d", word)),
    }
    if i > 0:
        prev = tokens[i - 1]
        features.update({
            "-1:word.lower": prev.lower(),
            "-1:word.istitle": prev.istitle(),
        })
    else:
        features["BOS"] = True

    if i < len(tokens) - 1:
        nxt = tokens[i + 1]
        features.update({
            "+1:word.lower": nxt.lower(),
            "+1:word.istitle": nxt.istitle(),
        })
    else:
        features["EOS"] = True

    return features


def sentence_features(tokens: list[str]) -> list[dict]:
    return [word2features(tokens, i) for i in range(len(tokens))]


def tags_to_entities(tokens: list[str], tags: list[str]) -> list[dict]:
    """Reconstruct entity spans (text + type) from a BIO tag sequence."""
    entities = []
    current_tokens: list[str] = []
    current_type: str | None = None

    def flush():
        nonlocal current_tokens, current_type
        if current_tokens and current_type:
            entities.append({"text": " ".join(current_tokens), "type": current_type})
        current_tokens = []
        current_type = None

    for token, tag in zip(tokens, tags):
        if tag.startswith("B-"):
            flush()
            current_type = tag[2:]
            current_tokens = [token]
        elif tag.startswith("I-") and current_type == tag[2:]:
            current_tokens.append(token)
        else:
            flush()
    flush()
    return entities
