"""
train_transcript_quality_classifier.py — Voice transcription quality classifier

Trains a classifier distinguishing clean text from simulated-ASR-noise
corrupted text, using the shared features in transcript_quality_features.py
(out-of-vocabulary rate, repeated-word ratio, average word length, etc.
— a lightweight perplexity-proxy that needs no real language model).

Usage:
    cd backend
    python ml/data/generate_transcript_quality_dataset.py
    python ml/train_transcript_quality_classifier.py
"""

from __future__ import annotations

import csv
import json
import sys
import time
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from transcript_quality_features import build_vocab, build_bigrams, extract_features, FEATURE_NAMES  # noqa: E402

DATA_PATH = Path(__file__).resolve().parent / "data" / "transcript_quality_dataset.csv"
MODEL_DIR = BACKEND_ROOT / "app" / "models"
MODEL_PATH = MODEL_DIR / "voice_quality_classifier_v1.joblib"
MANIFEST_PATH = MODEL_DIR / "voice_quality_classifier_v1.manifest.json"


def main():
    import pandas as pd
    import joblib
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score, roc_auc_score

    if not DATA_PATH.exists():
        raise FileNotFoundError(f"{DATA_PATH} not found — run ml/data/generate_transcript_quality_dataset.py first.")

    rows = []
    with open(DATA_PATH, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows.append(row)
    print(f"Loaded {len(rows)} examples")

    texts_train_split, _ = train_test_split(rows, test_size=0.25, random_state=42)
    # Vocab/bigrams built ONLY from clean texts in the training split —
    # using corrupted or held-out text to build them would leak signal.
    clean_train_texts = [r["text"] for r in texts_train_split if r["is_clean"] == "1"]
    vocab = build_vocab(clean_train_texts)
    bigrams = build_bigrams(clean_train_texts)
    print(f"Reference vocabulary: {len(vocab)} words, {len(bigrams)} bigrams")

    feats = [extract_features(r["text"], vocab, bigrams) for r in rows]
    X = pd.DataFrame(feats)[FEATURE_NAMES]
    y = pd.Series([int(r["is_clean"]) for r in rows])

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42, stratify=y)

    model = LogisticRegression(max_iter=1000, class_weight="balanced")
    t0 = time.time()
    model.fit(X_train, y_train)
    train_seconds = round(time.time() - t0, 3)

    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]
    acc = accuracy_score(y_test, y_pred)
    auc = roc_auc_score(y_test, y_prob)
    print(f"Trained in {train_seconds}s on {len(X_train)} rows, evaluated on {len(X_test)} held-out rows")
    print(f"Accuracy: {acc:.3f}  |  ROC-AUC: {auc:.3f}")

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "vocab": vocab, "bigrams": bigrams}, MODEL_PATH)

    manifest = {
        "model": "sklearn LogisticRegression",
        "version": "v1",
        "trained_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "train_rows": len(X_train),
        "test_rows": len(X_test),
        "train_seconds": train_seconds,
        "accuracy": round(acc, 4),
        "roc_auc": round(auc, 4),
        "vocab_size": len(vocab),
        "features": FEATURE_NAMES,
        "training_data": "SYNTHETIC — real sentences from this codebase, corrupted with simulated ASR-style noise (word deletion/duplication/shuffling, char substitution, filler insertion). No real Sarvam STT transcripts used. See ml/data/generate_transcript_quality_dataset.py.",
        "artifact": str(MODEL_PATH.relative_to(BACKEND_ROOT)),
    }
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"Saved model  -> {MODEL_PATH}")
    print(f"Saved manifest -> {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
