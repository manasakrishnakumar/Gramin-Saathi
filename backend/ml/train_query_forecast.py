"""
train_query_forecast.py — Query volume forecasting

Trains a regressor predicting expected query count per (hour_of_day,
day_of_week) bucket. Checks metrics.db for real logged queries first —
uses them if there are enough to fit anything meaningful (>= MIN_REAL_ROWS),
otherwise falls back to the synthetic seasonal bootstrap from
data/generate_query_volume_bootstrap.py, and says clearly in the manifest
which source it used. Real queries win the moment there are enough of them
— no code change needed, just re-run this script.

Usage:
    cd backend
    python ml/data/generate_query_volume_bootstrap.py   # only needed if going the synthetic route
    python ml/train_query_forecast.py
"""

from __future__ import annotations

import json
import sqlite3
import sys
import time
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

BOOTSTRAP_CSV = Path(__file__).resolve().parent / "data" / "query_volume_bootstrap.csv"
MODEL_DIR = BACKEND_ROOT / "app" / "models"
MODEL_PATH = MODEL_DIR / "query_forecast_v1.joblib"
MANIFEST_PATH = MODEL_DIR / "query_forecast_v1.manifest.json"

MIN_REAL_ROWS = 500  # below this, real hourly buckets are too sparse/noisy to fit


def load_real_hourly_counts() -> "list[dict] | None":
    """Aggregate real metrics.db rows into (hour_of_day, day_of_week, query_count) buckets."""
    try:
        from app.core.config import settings
        db_path = settings.DATA_DIR / "metrics.db"
    except Exception:
        return None
    if not db_path.exists():
        return None

    with sqlite3.connect(db_path) as conn:
        total = conn.execute("SELECT COUNT(*) FROM query_metrics").fetchone()[0]
        if total < MIN_REAL_ROWS:
            print(f"Only {total} real rows in metrics.db (< {MIN_REAL_ROWS} needed) — using synthetic bootstrap instead.")
            return None
        cursor = conn.execute("SELECT timestamp FROM query_metrics")
        from collections import Counter
        from datetime import datetime
        buckets = Counter()
        for (ts,) in cursor.fetchall():
            dt = datetime.fromisoformat(ts) if isinstance(ts, str) else ts
            buckets[(dt.hour, dt.weekday())] += 1
        rows = [
            {"hour_of_day": h, "day_of_week": d, "is_weekend": int(d >= 5), "query_count": c}
            for (h, d), c in buckets.items()
        ]
        print(f"Using {total} REAL logged queries, aggregated into {len(rows)} hour/day buckets.")
        return rows


def main():
    import pandas as pd
    import joblib
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import mean_absolute_error, r2_score

    real_rows = load_real_hourly_counts()
    if real_rows:
        df = pd.DataFrame(real_rows)
        source = "real"
    else:
        if not BOOTSTRAP_CSV.exists():
            raise FileNotFoundError(f"{BOOTSTRAP_CSV} not found — run ml/data/generate_query_volume_bootstrap.py first.")
        df = pd.read_csv(BOOTSTRAP_CSV)
        source = "synthetic"
        print(f"Loaded {len(df)} SYNTHETIC hourly rows")

    X = df[["hour_of_day", "day_of_week", "is_weekend"]]
    y = df["query_count"]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = RandomForestRegressor(n_estimators=150, max_depth=6, random_state=42)
    t0 = time.time()
    model.fit(X_train, y_train)
    train_seconds = round(time.time() - t0, 2)

    y_pred = model.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)
    print(f"Trained in {train_seconds}s on {len(X_train)} rows. MAE: {mae:.2f} queries/hour, R²: {r2:.3f}")

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)

    manifest = {
        "model": "sklearn RandomForestRegressor",
        "version": "v1",
        "trained_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "data_source": source,
        "train_rows": len(X_train),
        "test_rows": len(X_test),
        "train_seconds": train_seconds,
        "mae_queries_per_hour": round(mae, 3),
        "r2": round(r2, 4),
        "note": (
            "Trained on SYNTHETIC seasonal data (see ml/data/generate_query_volume_bootstrap.py) "
            "— not enough real logged queries yet. Re-run this script once metrics.db has "
            f"{MIN_REAL_ROWS}+ real rows to switch to real data automatically."
            if source == "synthetic" else
            "Trained on REAL logged query timestamps from metrics.db."
        ),
        "artifact": str(MODEL_PATH.relative_to(BACKEND_ROOT)),
    }
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"Saved model  -> {MODEL_PATH}")
    print(f"Saved manifest -> {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
