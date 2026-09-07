"""
train_anomaly_detector.py — Profile anomaly detection

Trains an unsupervised IsolationForest on the realistic profile
distribution from data/generate_profile_distribution.py. No labels
needed — this is genuine unsupervised ML: the model learns what a
"normal" profile in this population looks like, then flags anything
that's a statistical outlier (garbage input, bot traffic, or just wildly
inconsistent field combinations) before it wastes a rule-engine pass.

Usage:
    cd backend
    python ml/data/generate_profile_distribution.py
    python ml/train_anomaly_detector.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

DATA_PATH = Path(__file__).resolve().parent / "data" / "profile_distribution.csv"
MODEL_DIR = BACKEND_ROOT / "app" / "models"
MODEL_PATH = MODEL_DIR / "anomaly_detector_v1.joblib"
MANIFEST_PATH = MODEL_DIR / "anomaly_detector_v1.manifest.json"

CATEGORICAL_COLS = ["occupation", "gender", "category", "education"]
NUMERIC_COLS = ["age", "annual_income", "land_owned_acres", "is_bpl", "is_disabled"]


def main():
    import pandas as pd
    import joblib
    from sklearn.ensemble import IsolationForest

    if not DATA_PATH.exists():
        raise FileNotFoundError(f"{DATA_PATH} not found — run ml/data/generate_profile_distribution.py first.")

    df = pd.read_csv(DATA_PATH)
    print(f"Loaded {len(df)} realistic profiles")

    X = pd.get_dummies(df[CATEGORICAL_COLS + NUMERIC_COLS], columns=CATEGORICAL_COLS)

    model = IsolationForest(n_estimators=200, contamination=0.05, random_state=42)
    t0 = time.time()
    model.fit(X)
    train_seconds = round(time.time() - t0, 2)

    scores = model.decision_function(X)  # higher = more normal
    preds = model.predict(X)  # -1 = anomaly, 1 = normal
    n_flagged = int((preds == -1).sum())
    print(f"Trained in {train_seconds}s on {len(X)} profiles. Flagged {n_flagged} ({n_flagged/len(X):.1%}) as anomalous "
          f"on the training set itself (expected ~5%, matches contamination setting).")

    # Sanity check: manually construct an obviously nonsensical profile and
    # confirm it scores as more anomalous than a typical one.
    typical = pd.DataFrame([{"age": 35, "annual_income": 150000, "land_owned_acres": 1.0,
                              "is_bpl": 0, "is_disabled": 0}])
    weird = pd.DataFrame([{"age": 14, "annual_income": 5000000, "land_owned_acres": 200.0,
                            "is_bpl": 1, "is_disabled": 0}])
    for df_, label, occ, gen, cat, edu in [
        (typical, "typical (age 35, farmer, moderate income)", "farmer", "male", "general", "secondary"),
        (weird, "nonsensical (age 14, 50 lakh income, 200 acres)", "student", "male", "general", "none"),
    ]:
        row = df_.iloc[0].to_dict()
        row.update({f"occupation_{occ}": 1, f"gender_{gen}": 1, f"category_{cat}": 1, f"education_{edu}": 1})
        row_df = pd.DataFrame([row])
        for col in X.columns:
            if col not in row_df.columns:
                row_df[col] = 0
        row_df = row_df[X.columns]
        s = model.decision_function(row_df)[0]
        p = model.predict(row_df)[0]
        print(f"  sanity check — {label}: anomaly_score={s:.3f}, flagged_anomaly={p == -1}")

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "feature_columns": list(X.columns)}, MODEL_PATH)

    manifest = {
        "model": "sklearn IsolationForest (unsupervised)",
        "version": "v1",
        "trained_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "train_rows": len(X),
        "train_seconds": train_seconds,
        "contamination": 0.05,
        "flagged_on_training_set_pct": round(n_flagged / len(X), 4),
        "training_data": "Realistic synthetic profile distribution (data/generate_profile_distribution.py) — unsupervised, no labels used or needed.",
        "artifact": str(MODEL_PATH.relative_to(BACKEND_ROOT)),
    }
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"Saved model  -> {MODEL_PATH}")
    print(f"Saved manifest -> {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
