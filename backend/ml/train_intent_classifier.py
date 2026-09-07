"""
train_intent_classifier.py — Phase 1

Trains a real, small, fast intent classifier (TF-IDF + Logistic Regression)
on the synthetic dataset produced by data/generate_intent_dataset.py, as a
distilled/cheaper alternative to calling Gemini for zero-shot classification
on every chat turn.

This is genuinely trained ML — not a rule table, not a prompt — but it is
trained on synthetic/templated data, not real user queries. Treat its
accuracy numbers as "does it separate the intent taxonomy at all", not as
a production-quality guarantee. Retrain on real labeled queries (e.g. by
sampling from ml_feedback events + human review) once that data exists.

Usage:
    cd backend
    python ml/data/generate_intent_dataset.py   # writes ml/data/intent_dataset.csv
    python ml/train_intent_classifier.py

Output:
    backend/app/models/intent_classifier_v1.joblib      (vectorizer + classifier pipeline)
    backend/app/models/intent_classifier_v1.manifest.json (metrics, labels, training info)
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

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, accuracy_score, f1_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

DATA_PATH = Path(__file__).resolve().parent / "data" / "intent_dataset.csv"
MODEL_DIR = BACKEND_ROOT / "app" / "models"
MODEL_PATH = MODEL_DIR / "intent_classifier_v1.joblib"
MANIFEST_PATH = MODEL_DIR / "intent_classifier_v1.manifest.json"


def load_dataset() -> tuple[list[str], list[str]]:
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"{DATA_PATH} not found — run `python ml/data/generate_intent_dataset.py` first."
        )
    texts, labels = [], []
    with open(DATA_PATH, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            texts.append(row["text"])
            labels.append(row["label"])
    return texts, labels


def main():
    texts, labels = load_dataset()
    print(f"Loaded {len(texts)} examples across {len(set(labels))} intents")

    X_train, X_test, y_train, y_test = train_test_split(
        texts, labels, test_size=0.25, random_state=42, stratify=labels
    )

    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=1, sublinear_tf=True)),
        ("clf", LogisticRegression(max_iter=1000, class_weight="balanced")),
    ])

    t0 = time.time()
    pipeline.fit(X_train, y_train)
    train_seconds = round(time.time() - t0, 3)

    y_pred = pipeline.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    f1_macro = f1_score(y_test, y_pred, average="macro")
    report = classification_report(y_test, y_pred, output_dict=True)

    print(f"\nTrained in {train_seconds}s on {len(X_train)} examples, evaluated on {len(X_test)} held-out examples")
    print(f"Accuracy: {acc:.3f}  |  Macro F1: {f1_macro:.3f}\n")
    print(classification_report(y_test, y_pred))

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, MODEL_PATH)

    manifest = {
        "model": "tfidf+logistic_regression",
        "version": "v1",
        "trained_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "train_examples": len(X_train),
        "test_examples": len(X_test),
        "train_seconds": train_seconds,
        "accuracy": round(acc, 4),
        "macro_f1": round(f1_macro, 4),
        "per_class": {k: v for k, v in report.items() if isinstance(v, dict)},
        "labels": sorted(set(labels)),
        "training_data": "SYNTHETIC — templated queries, not real user data. See ml/README.md.",
        "artifact": str(MODEL_PATH.relative_to(BACKEND_ROOT)),
    }
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"Saved model  -> {MODEL_PATH}")
    print(f"Saved manifest -> {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
