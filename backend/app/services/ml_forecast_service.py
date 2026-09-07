"""
ml_forecast_service.py — Query volume forecasting, serving side

Loads the trained model from ml/train_query_forecast.py and predicts
expected query volume per hour. See that script for the real-vs-synthetic
data source note carried in the manifest — surfaced here in every
response via `data_source` so callers know which mode it's in.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

MODEL_PATH = Path(__file__).resolve().parents[1] / "models" / "query_forecast_v1.joblib"
MANIFEST_PATH = Path(__file__).resolve().parents[1] / "models" / "query_forecast_v1.manifest.json"


class MLForecastService:

    def __init__(self):
        self._model = None
        self._manifest: Optional[dict] = None
        self._load_error: Optional[str] = None
        self._try_load()

    def _try_load(self):
        try:
            import joblib
            if not MODEL_PATH.exists():
                self._load_error = (
                    f"No trained model at {MODEL_PATH}. Run: "
                    f"python ml/data/generate_query_volume_bootstrap.py && python ml/train_query_forecast.py"
                )
                return
            self._model = joblib.load(MODEL_PATH)
            if MANIFEST_PATH.exists():
                self._manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
            logger.info(f"Loaded query forecast model from {MODEL_PATH}")
        except Exception as e:
            self._load_error = str(e)
            logger.warning(f"Could not load query forecast model: {e}")

    @property
    def is_ready(self) -> bool:
        return self._model is not None

    def forecast_next_24h(self) -> dict:
        if not self.is_ready:
            return {"forecast": [], "error": self._load_error}

        import pandas as pd

        now = datetime.now()
        rows = []
        for i in range(24):
            t = now + timedelta(hours=i)
            rows.append({"hour_of_day": t.hour, "day_of_week": t.weekday(), "is_weekend": int(t.weekday() >= 5)})
        X = pd.DataFrame(rows)
        preds = self._model.predict(X)

        forecast = [
            {
                "hour": (now + timedelta(hours=i)).strftime("%Y-%m-%d %H:00"),
                "predicted_queries": round(max(0, float(p)), 1),
            }
            for i, p in enumerate(preds)
        ]
        return {
            "forecast": forecast,
            "data_source": self._manifest.get("data_source") if self._manifest else "unknown",
        }

    def manifest(self) -> Optional[dict]:
        return self._manifest


# Singleton
ml_forecast_service = MLForecastService()
