"""
train_profile_clusters.py — User segmentation / clustering

Unsupervised KMeans over the same realistic synthetic profile
distribution used for anomaly detection (data/generate_profile_distribution.py
— reused as-is, no need to regenerate). No labels needed. Produces
human-readable cluster summaries (auto-generated from each cluster's own
centroid statistics, not hand-written) for a "who's actually using this"
descriptive-analytics view.

Usage:
    cd backend
    python ml/data/generate_profile_distribution.py   # if not already run
    python ml/train_profile_clusters.py
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
MODEL_PATH = MODEL_DIR / "profile_clusters_v1.joblib"
MANIFEST_PATH = MODEL_DIR / "profile_clusters_v1.manifest.json"

N_CLUSTERS = 5
CATEGORICAL_COLS = ["occupation", "gender", "category", "education"]
NUMERIC_COLS = ["age", "annual_income", "land_owned_acres", "is_bpl", "is_disabled"]


def summarize_cluster(df_cluster) -> dict:
    """Auto-generates a human-readable label + stats from a cluster's own data — not hand-written per cluster."""
    avg_age = df_cluster["age"].mean()
    avg_income = df_cluster["annual_income"].mean()
    avg_land = df_cluster["land_owned_acres"].mean()
    bpl_rate = df_cluster["is_bpl"].mean()
    dominant_occupation = df_cluster["occupation"].mode().iloc[0]
    dominant_education = df_cluster["education"].mode().iloc[0]

    age_desc = "young" if avg_age < 28 else "senior" if avg_age > 55 else "middle-aged"
    income_desc = "low-income" if avg_income < 100000 else "high-income" if avg_income > 500000 else "moderate-income"
    bpl_desc = ", mostly BPL" if bpl_rate > 0.3 else ""

    label = f"{age_desc}, {income_desc} {dominant_occupation.replace('_', ' ')}s{bpl_desc}"

    return {
        "label": label,
        "size": int(len(df_cluster)),
        "avg_age": round(float(avg_age), 1),
        "avg_annual_income": round(float(avg_income), 0),
        "avg_land_owned_acres": round(float(avg_land), 2),
        "bpl_rate": round(float(bpl_rate), 3),
        "dominant_occupation": dominant_occupation,
        "dominant_education": dominant_education,
    }


def main():
    import pandas as pd
    import joblib
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import StandardScaler

    if not DATA_PATH.exists():
        raise FileNotFoundError(f"{DATA_PATH} not found — run ml/data/generate_profile_distribution.py first.")

    df = pd.read_csv(DATA_PATH)
    print(f"Loaded {len(df)} profiles")

    X = pd.get_dummies(df[CATEGORICAL_COLS + NUMERIC_COLS], columns=CATEGORICAL_COLS)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    t0 = time.time()
    kmeans = KMeans(n_clusters=N_CLUSTERS, random_state=42, n_init=10)
    labels = kmeans.fit_predict(X_scaled)
    train_seconds = round(time.time() - t0, 2)

    df["cluster"] = labels
    summaries = {}
    for c in range(N_CLUSTERS):
        summaries[str(c)] = summarize_cluster(df[df["cluster"] == c])

    print(f"Trained in {train_seconds}s. {N_CLUSTERS} clusters:")
    for c, s in summaries.items():
        print(f"  Cluster {c} ({s['size']} profiles): {s['label']} — "
              f"avg age {s['avg_age']}, avg income Rs.{s['avg_annual_income']:.0f}, BPL rate {s['bpl_rate']:.0%}")

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump({
        "kmeans": kmeans, "scaler": scaler, "feature_columns": list(X.columns), "summaries": summaries,
    }, MODEL_PATH)

    manifest = {
        "model": "sklearn KMeans (unsupervised)",
        "version": "v1",
        "trained_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "n_clusters": N_CLUSTERS,
        "train_rows": len(df),
        "train_seconds": train_seconds,
        "cluster_summaries": summaries,
        "training_data": "Realistic synthetic profile distribution (data/generate_profile_distribution.py) — unsupervised, no labels used or needed.",
        "artifact": str(MODEL_PATH.relative_to(BACKEND_ROOT)),
    }
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"Saved model  -> {MODEL_PATH}")
    print(f"Saved manifest -> {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
