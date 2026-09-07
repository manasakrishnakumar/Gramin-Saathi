"""
train_ranker_bootstrap.py — Phase 2 (cold-start bootstrap)

Trains a gradient-boosted ranker on the SYNTHETIC weak-supervision data from
data/generate_ranker_bootstrap.py — see that file's docstring for why this
is a placeholder, not a "real Phase 2 model". Real Phase 2 needs actual
user interaction events; this exists so the pipeline has something real
and runnable today, and so the code/plumbing for Phase 2 is already
in place the moment real event data exists (train_ranker_from_events.py
reuses the same feature engineering + training code path).

IMPORTANT — by design, this model is never used to filter or hide
schemes. `recommendation_service.py`'s hard-criteria rule check remains
the sole authority on eligibility (untouched, not imported for
modification, only for read access to run the rule engine when
generating training data). This ranker only ever *reorders* schemes
that already passed the rule engine — see ml_ranker_service.py.

Usage:
    cd backend
    python ml/data/generate_ranker_bootstrap.py
    python ml/train_ranker_bootstrap.py

Model choice note: this uses scikit-learn's HistGradientBoostingClassifier
rather than LightGBM/XGBoost. On this Windows dev environment, loading a
scikit-learn model (as ml_intent_classifier_service.py already does) and
then calling LightGBM's native predict in the same process reliably
crashes with "OSError: exception: access violation reading 0x0..." — a
known class of conflict between two different bundled OpenMP runtimes on
Windows. Reproduced directly while building this, see ml/README.md.
scikit-learn's own gradient boosting has no such conflict since it's the
same native stack already used elsewhere in this app, and it requires no
new dependency (scikit-learn was already in requirements.txt).
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

DATA_PATH = Path(__file__).resolve().parent / "data" / "ranker_bootstrap.csv"
MODEL_DIR = BACKEND_ROOT / "app" / "models"
MODEL_PATH = MODEL_DIR / "ranker_bootstrap_v1.joblib"
MANIFEST_PATH = MODEL_DIR / "ranker_bootstrap_v1.manifest.json"

CATEGORICAL_COLS = ["occupation", "gender", "category", "education"]
NUMERIC_COLS = ["age", "annual_income", "land_owned_acres", "is_bpl", "is_disabled",
                 "rule_score_pct", "matched_count", "missed_count"]
LABEL_COL = "engagement_label"


def build_features(df):
    import pandas as pd
    X = pd.get_dummies(df[CATEGORICAL_COLS + NUMERIC_COLS], columns=CATEGORICAL_COLS)
    return X


def main():
    import pandas as pd
    import joblib
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import roc_auc_score, average_precision_score

    if not DATA_PATH.exists():
        raise FileNotFoundError(f"{DATA_PATH} not found — run ml/data/generate_ranker_bootstrap.py first.")

    df = pd.read_csv(DATA_PATH)
    df = df[df["is_disqualified"] == 0].reset_index(drop=True)  # disqualified schemes never get ranked at all
    print(f"Loaded {len(df)} (profile, eligible-scheme) rows for training")

    X = build_features(df)
    y = df[LABEL_COL]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42, stratify=y)

    model = HistGradientBoostingClassifier(max_iter=200, max_depth=5, learning_rate=0.05, random_state=42)

    t0 = time.time()
    model.fit(X_train, y_train)
    train_seconds = round(time.time() - t0, 2)

    y_prob = model.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test, y_prob)
    ap = average_precision_score(y_test, y_prob)

    # How much does the learned score change the ranking vs just using
    # rule_score_pct directly? Correlate the two so it's clear this isn't
    # just re-deriving what the rule engine already gives for free.
    corr_with_rule_score = float(pd.Series(y_prob).corr(X_test["rule_score_pct"].reset_index(drop=True)))

    print(f"\nTrained in {train_seconds}s on {len(X_train)} rows, evaluated on {len(X_test)} held-out rows")
    print(f"ROC-AUC: {auc:.3f}  |  Average Precision: {ap:.3f}")
    print(f"Correlation between learned score and raw rule_score_pct: {corr_with_rule_score:.3f}")

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "feature_columns": list(X.columns)}, MODEL_PATH)

    manifest = {
        "model": "sklearn HistGradientBoostingClassifier (used as a reranking score)",
        "version": "v1-bootstrap",
        "trained_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "train_rows": len(X_train),
        "test_rows": len(X_test),
        "train_seconds": train_seconds,
        "roc_auc": round(auc, 4),
        "average_precision": round(ap, 4),
        "correlation_with_raw_rule_score": round(corr_with_rule_score, 4),
        "training_data": "SYNTHETIC weak-supervision bootstrap — labels are derived FROM the rule engine's own score_pct plus noise, not real user clicks. This is a cold-start placeholder. Retrain with train_ranker_from_events.py once real Phase 0 event data exists.",
        "design_constraint": "This model NEVER determines eligibility or filters schemes — disqualified schemes are excluded before this model ever sees them, and the rule engine's hard-criteria check remains untouched and authoritative. This model only reorders already-eligible schemes.",
        "not_wired_in": "recommendation_service.py and its API endpoint are unmodified and still return pure rule-engine order — this artifact is standalone until explicitly wired in behind a flag.",
        "artifact": str(MODEL_PATH.relative_to(BACKEND_ROOT)),
    }
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"Saved model  -> {MODEL_PATH}")
    print(f"Saved manifest -> {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
