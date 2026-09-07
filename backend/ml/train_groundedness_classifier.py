"""
train_groundedness_classifier.py — Answer groundedness / hallucination scoring

Trains a classifier on the synthetic (context, answer, grounded?) pairs
from data/generate_groundedness_dataset.py, using the shared feature
extraction in groundedness_features.py (word overlap, embedding cosine
similarity, length ratio, numeric-mismatch flag).

Usage:
    cd backend
    python ml/data/generate_groundedness_dataset.py
    python ml/train_groundedness_classifier.py
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

from groundedness_features import extract_features, FEATURE_NAMES  # noqa: E402

DATA_PATH = Path(__file__).resolve().parent / "data" / "groundedness_dataset.csv"
MODEL_DIR = BACKEND_ROOT / "app" / "models"
MODEL_PATH = MODEL_DIR / "groundedness_classifier_v1.joblib"
MANIFEST_PATH = MODEL_DIR / "groundedness_classifier_v1.manifest.json"


def main():
    import pandas as pd
    import joblib
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import roc_auc_score, accuracy_score

    if not DATA_PATH.exists():
        raise FileNotFoundError(f"{DATA_PATH} not found — run ml/data/generate_groundedness_dataset.py first.")

    rows = []
    with open(DATA_PATH, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows.append(row)
    print(f"Loaded {len(rows)} (context, answer) pairs — extracting features "
          f"(loads the bi-encoder on first call, may take a few seconds)…")

    feats = [extract_features(r["context"], r["answer"]) for r in rows]
    X = pd.DataFrame(feats)[FEATURE_NAMES]
    y = pd.Series([int(r["grounded"]) for r in rows])

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42, stratify=y)

    model = HistGradientBoostingClassifier(max_iter=100, max_depth=3, learning_rate=0.1, random_state=42)
    t0 = time.time()
    model.fit(X_train, y_train)
    train_seconds = round(time.time() - t0, 2)

    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]
    acc = accuracy_score(y_test, y_pred)
    auc = roc_auc_score(y_test, y_prob)
    print(f"Trained in {train_seconds}s on {len(X_train)} rows, evaluated on {len(X_test)} held-out rows")
    print(f"Accuracy: {acc:.3f}  |  ROC-AUC: {auc:.3f}")

    # Feature importances (permutation-based — HistGradientBoostingClassifier
    # has no built-in feature_importances_) — sanity check that the model is
    # using signal that makes sense (embedding similarity + word overlap
    # should matter, not some spurious artifact).
    from sklearn.inspection import permutation_importance
    perm = permutation_importance(model, X_test, y_test, n_repeats=10, random_state=42)
    importances = {name: round(float(imp), 4) for name, imp in zip(FEATURE_NAMES, perm.importances_mean)}
    print(f"Feature importances (permutation): {importances}")

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)

    manifest = {
        "model": "sklearn HistGradientBoostingClassifier",
        "version": "v1",
        "trained_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "train_rows": len(X_train),
        "test_rows": len(X_test),
        "train_seconds": train_seconds,
        "accuracy": round(acc, 4),
        "roc_auc": round(auc, 4),
        "features": FEATURE_NAMES,
        "training_data": "SYNTHETIC — templated grounded/ungrounded pairs built from SCHEME_REGISTRY descriptions (topic mismatch, fabricated numbers, off-topic filler). See ml/data/generate_groundedness_dataset.py.",
        "artifact": str(MODEL_PATH.relative_to(BACKEND_ROOT)),
    }
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"Saved model  -> {MODEL_PATH}")
    print(f"Saved manifest -> {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
