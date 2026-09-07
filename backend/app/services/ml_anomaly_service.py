"""
ml_anomaly_service.py — Profile anomaly detection, serving side

Loads the trained IsolationForest from ml/train_anomaly_detector.py and
scores a submitted profile. Never blocks a submission by itself — this is
meant as a flag for review/logging, not a hard gate, since a false
positive here would incorrectly stop someone from finding real
government benefits they're entitled to.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

MODEL_PATH = Path(__file__).resolve().parents[1] / "models" / "anomaly_detector_v1.joblib"
MANIFEST_PATH = Path(__file__).resolve().parents[1] / "models" / "anomaly_detector_v1.manifest.json"


class MLAnomalyService:

    def __init__(self):
        self._model = None
        self._feature_columns: list[str] = []
        self._manifest: Optional[dict] = None
        self._load_error: Optional[str] = None
        self._try_load()

    def _try_load(self):
        try:
            import joblib
            if not MODEL_PATH.exists():
                self._load_error = (
                    f"No trained model at {MODEL_PATH}. Run: "
                    f"python ml/data/generate_profile_distribution.py && python ml/train_anomaly_detector.py"
                )
                return
            bundle = joblib.load(MODEL_PATH)
            self._model = bundle["model"]
            self._feature_columns = bundle["feature_columns"]
            if MANIFEST_PATH.exists():
                self._manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
            logger.info(f"Loaded anomaly detector from {MODEL_PATH}")
        except Exception as e:
            self._load_error = str(e)
            logger.warning(f"Could not load anomaly detector: {e}")

    @property
    def is_ready(self) -> bool:
        return self._model is not None

    def check(self, profile: dict) -> dict:
        if not self.is_ready:
            return {"is_anomaly": None, "anomaly_score": None, "error": self._load_error}

        import pandas as pd

        row = {
            "age": profile.get("age", 0),
            "annual_income": profile.get("annual_income", 0),
            "land_owned_acres": profile.get("land_owned_acres", 0),
            "is_bpl": int(profile.get("is_bpl", False)),
            "is_disabled": int(profile.get("is_disabled", False)),
        }
        for col, val in [
            ("occupation", profile.get("occupation", "other")),
            ("gender", profile.get("gender", "other")),
            ("category", profile.get("category", "general")),
            ("education", profile.get("education", "none")),
        ]:
            for feature_col in self._feature_columns:
                if feature_col == f"{col}_{val}":
                    row[feature_col] = 1

        X = pd.DataFrame([row])
        for col in self._feature_columns:
            if col not in X.columns:
                X[col] = 0
        X = X[self._feature_columns]

        score = float(self._model.decision_function(X)[0])
        is_anomaly = bool(self._model.predict(X)[0] == -1)
        return {"is_anomaly": is_anomaly, "anomaly_score": round(score, 4)}

    def manifest(self) -> Optional[dict]:
        return self._manifest


# Singleton
ml_anomaly_service = MLAnomalyService()
