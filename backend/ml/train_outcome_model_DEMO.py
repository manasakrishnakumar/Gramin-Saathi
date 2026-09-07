"""
train_outcome_model_DEMO.py — Phase 3 (SYNTHETIC DEMO ONLY)

Trains a classifier on the SYNTHETIC data from
data/generate_outcome_bootstrap.py. Read that file's docstring — this is a
demonstration of the modeling technique, built at the user's explicit
request overriding the original Phase 3 decision in PHASE3_NOTES.md, not
a claim to predict real application outcomes. Every artifact this
produces is tagged "SYNTHETIC_DEMO" so it can't be mistaken for the real
thing downstream.

This is intentionally kept completely separate from
app/services/ml_outcome_service.py, which stores REAL reported outcomes
(if/when a trustworthy source reports them) and which this script does
NOT read from or write to. If real outcome data ever exists in
sufficient quantity, write a `train_outcome_model_from_events.py`
following the same pattern as train_ranker_from_events.py — do not
repurpose this synthetic model for that; retrain from scratch on real
data with its own honest label.

Usage:
    cd backend
    python ml/data/generate_outcome_bootstrap.py
    python ml/train_outcome_model_DEMO.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

DATA_PATH = Path(__file__).resolve().parent / "data" / "outcome_bootstrap_SYNTHETIC.csv"
MODEL_DIR = BACKEND_ROOT / "app" / "models"
MODEL_PATH = MODEL_DIR / "outcome_model_v1_SYNTHETIC_DEMO.joblib"
MANIFEST_PATH = MODEL_DIR / "outcome_model_v1_SYNTHETIC_DEMO.manifest.json"

DISCLAIMER = (
    "SYNTHETIC DEMO MODEL — trained entirely on fabricated/simulated data, "
    "not real application outcomes. This project has no access to real "
    "government approval/rejection data. Any score from this model is a "
    "demonstration of the modeling technique only and must never be "
    "presented to a real user as a real prediction of their chances. "
    "See backend/ml/PHASE3_NOTES.md."
)

CATEGORICAL_COLS = ["occupation", "gender", "category", "education"]
NUMERIC_COLS = ["age", "annual_income", "land_owned_acres", "is_bpl", "is_disabled",
                 "rule_score_pct", "matched_count", "missed_count"]


def main():
    import pandas as pd
    import joblib
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import roc_auc_score, average_precision_score

    if not DATA_PATH.exists():
        raise FileNotFoundError(f"{DATA_PATH} not found — run ml/data/generate_outcome_bootstrap.py first.")

    df = pd.read_csv(DATA_PATH)
    df = df[df["is_disqualified"] == 0].reset_index(drop=True)  # disqualified -> always "rejected", not worth modeling
    print(f"Loaded {len(df)} SYNTHETIC (profile, eligible-scheme) rows")

    X = pd.get_dummies(df[CATEGORICAL_COLS + NUMERIC_COLS], columns=CATEGORICAL_COLS)
    y = df["synthetic_outcome_approved"]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42, stratify=y)

    model = HistGradientBoostingClassifier(max_iter=200, max_depth=5, learning_rate=0.05, random_state=42)
    t0 = time.time()
    model.fit(X_train, y_train)
    train_seconds = round(time.time() - t0, 2)

    y_prob = model.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test, y_prob)
    ap = average_precision_score(y_test, y_prob)
    print(f"Trained in {train_seconds}s on {len(X_train)} rows, evaluated on {len(X_test)} held-out rows")
    print(f"ROC-AUC: {auc:.3f}  |  Average Precision: {ap:.3f}")
    print(f"(These numbers describe how well the model fits the SYNTHETIC heuristic — not real-world accuracy.)")

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "feature_columns": list(X.columns)}, MODEL_PATH)

    manifest = {
        "model": "sklearn HistGradientBoostingClassifier",
        "version": "v1-SYNTHETIC-DEMO",
        "trained_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "train_rows": len(X_train),
        "test_rows": len(X_test),
        "train_seconds": train_seconds,
        "roc_auc": round(auc, 4),
        "average_precision": round(ap, 4),
        "disclaimer": DISCLAIMER,
        "training_data": "100% SYNTHETIC — fabricated outcome labels from a hand-written heuristic, not real government decisions. See ml/data/generate_outcome_bootstrap.py and ml/PHASE3_NOTES.md.",
        "artifact": str(MODEL_PATH.relative_to(BACKEND_ROOT)),
    }
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"Saved model  -> {MODEL_PATH}")
    print(f"Saved manifest -> {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
