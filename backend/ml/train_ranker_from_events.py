"""
train_ranker_from_events.py — Phase 2 (REAL — not runnable yet)

This is the actual Phase 2 script: it trains the same gradient-boosted ranker as
train_ranker_bootstrap.py, but on REAL logged interaction events instead
of synthetic weak-supervision — reading from the events database that
`app.services.ml_feedback_service.MLFeedbackService` writes to whenever
the (currently unwired — see ml/README.md) feedback endpoints are called
by the live frontend.

It will raise immediately if there isn't enough real data yet — this is
intentional: don't silently fall back to fabricating a result. Point this
at the events DB once Phase 0 has been live long enough to accumulate a
meaningful number of "recommendation_action" events (some real clicks,
some real dismissals, ideally per unique profile/scheme combination).

Usage (once ready):
    cd backend
    python ml/train_ranker_from_events.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

MODEL_DIR = BACKEND_ROOT / "app" / "models"
MODEL_PATH = MODEL_DIR / "ranker_events_v1.joblib"
MANIFEST_PATH = MODEL_DIR / "ranker_events_v1.manifest.json"

MIN_EVENTS_REQUIRED = 500  # arbitrary floor — a ranker trained on fewer than this is not trustworthy

CATEGORICAL_COLS = ["occupation", "gender", "category", "education"]
NUMERIC_COLS = ["age", "annual_income", "land_owned_acres", "is_bpl", "is_disabled",
                 "rule_score_pct", "matched_count", "missed_count"]


def load_real_events():
    """
    Pulls labeled (profile, scheme, engaged?) rows from the events DB
    written by ml_feedback_service.py's `log_recommendation_action`.
    `engaged` = 1 for "clicked_apply" / "checked_eligibility" actions,
    0 for "dismissed" / a "viewed" event with no follow-up action.
    """
    from app.services.ml_feedback_service import ml_feedback_service
    return ml_feedback_service.export_ranker_training_rows()


def main():
    import pandas as pd
    import joblib
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import roc_auc_score, average_precision_score

    rows = load_real_events()
    if len(rows) < MIN_EVENTS_REQUIRED:
        raise RuntimeError(
            f"Only {len(rows)} real recommendation-interaction events logged so far "
            f"(need at least {MIN_EVENTS_REQUIRED}). This is expected right after Phase 0 "
            f"ships — the feedback endpoints need to actually be called by the live "
            f"frontend for a while first. Use train_ranker_bootstrap.py's synthetic "
            f"model in the meantime; re-run this script once enough real events exist."
        )

    df = pd.DataFrame(rows)
    print(f"Loaded {len(df)} REAL logged (profile, scheme) interaction rows")

    X = pd.get_dummies(df[CATEGORICAL_COLS + NUMERIC_COLS], columns=CATEGORICAL_COLS)
    y = df["engaged"]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    model = HistGradientBoostingClassifier(max_iter=200, max_depth=5, learning_rate=0.05, random_state=42)
    t0 = time.time()
    model.fit(X_train, y_train)
    train_seconds = round(time.time() - t0, 2)

    y_prob = model.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test, y_prob)
    ap = average_precision_score(y_test, y_prob)
    print(f"Trained in {train_seconds}s. ROC-AUC: {auc:.3f}  |  Average Precision: {ap:.3f}")

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "feature_columns": list(X.columns)}, MODEL_PATH)

    manifest = {
        "model": "sklearn HistGradientBoostingClassifier (used as a reranking score)",
        "version": "v1-real-events",
        "trained_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "train_rows": len(X_train),
        "test_rows": len(X_test),
        "train_seconds": train_seconds,
        "roc_auc": round(auc, 4),
        "average_precision": round(ap, 4),
        "training_data": "REAL logged user interaction events from ml_feedback_service.",
        "design_constraint": "This model NEVER determines eligibility or filters schemes — only reorders already rule-eligible schemes. See ml_ranker_service.py.",
        "artifact": str(MODEL_PATH.relative_to(BACKEND_ROOT)),
    }
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"Saved model -> {MODEL_PATH}")


if __name__ == "__main__":
    main()
