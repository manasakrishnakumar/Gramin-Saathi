"""
transcript_quality_features.py — shared feature extraction for the voice
transcription quality classifier.

Used by BOTH train_transcript_quality_classifier.py and
app/services/ml_voice_quality_service.py. The reference vocabulary
(built once from the clean training corpus) is saved inside the model
bundle so serving never needs to rebuild it — same "identical feature
engineering at train and serve time" discipline as the other classifiers
in this pass.
"""

from __future__ import annotations

import re

FEATURE_NAMES = [
    "avg_word_length", "oov_rate", "repeated_word_ratio",
    "non_alpha_ratio", "unique_word_ratio", "num_words", "bigram_oov_rate",
]


def build_vocab(clean_texts: list[str]) -> set[str]:
    vocab = set()
    for text in clean_texts:
        vocab.update(re.findall(r"[a-z]+", text.lower()))
    return vocab


def build_bigrams(clean_texts: list[str]) -> set[tuple[str, str]]:
    """
    Adjacent-word-pair set from clean text — a lightweight n-gram
    perplexity proxy. This is the feature that actually catches word-order
    corruption (e.g. shuffled words): shuffling doesn't change which words
    appear (so unigram/oov_rate is blind to it) but it does break almost
    every natural word-adjacency pair, which this feature detects.
    """
    bigrams = set()
    for text in clean_texts:
        words = re.findall(r"[a-z]+", text.lower())
        bigrams.update(zip(words, words[1:]))
    return bigrams


def extract_features(text: str, vocab: set[str], bigrams: set[tuple[str, str]] | None = None) -> dict:
    words = re.findall(r"[a-z]+", text.lower())
    n = len(words)
    if n == 0:
        return {name: 0.0 for name in FEATURE_NAMES}

    avg_word_length = sum(len(w) for w in words) / n
    oov_rate = sum(1 for w in words if w not in vocab) / n
    repeats = sum(1 for i in range(1, n) if words[i] == words[i - 1])
    repeated_word_ratio = repeats / max(1, n - 1)
    non_alpha_chars = len(re.findall(r"[^a-zA-Z\s]", text))
    non_alpha_ratio = non_alpha_chars / max(1, len(text))
    unique_word_ratio = len(set(words)) / n

    if bigrams and n > 1:
        pairs = list(zip(words, words[1:]))
        bigram_oov_rate = sum(1 for p in pairs if p not in bigrams) / len(pairs)
    else:
        bigram_oov_rate = 0.0

    return {
        "avg_word_length": round(avg_word_length, 4),
        "oov_rate": round(oov_rate, 4),
        "repeated_word_ratio": round(repeated_word_ratio, 4),
        "non_alpha_ratio": round(non_alpha_ratio, 4),
        "unique_word_ratio": round(unique_word_ratio, 4),
        "num_words": n,
        "bigram_oov_rate": round(bigram_oov_rate, 4),
    }
