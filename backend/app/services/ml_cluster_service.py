"""
ml_cluster_service.py — User segmentation, serving side

Loads the trained KMeans + auto-generated cluster summaries from
ml/train_profile_clusters.py. Descriptive analytics only — assigns a
profile to its nearest segment and lists all segments; doesn't feed back
into eligibility, recommendation ranking, or anything user-facing that
affects outcomes.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

MODEL_PATH = Path(__file__).resolve().parents[1] / "models" / "profile_clusters_v1.joblib"


class MLClusterService:

    def __init__(self):
        self._kmeans = None
        self._scaler = None
        self._feature_columns: list[str] = []
        self._summaries: dict = {}
        self._load_error: Optional[str] = None
        self._try_load()

    def _try_load(self):
        try:
            import joblib
            if not MODEL_PATH.exists():
                self._load_error = (
                    f"No trained model at {MODEL_PATH}. Run: "
                    f"python ml/data/generate_profile_distribution.py && python ml/train_profile_clusters.py"
                )
                return
            bundle = joblib.load(MODEL_PATH)
            self._kmeans = bundle["kmeans"]
            self._scaler = bundle["scaler"]
            self._feature_columns = bundle["feature_columns"]
            self._summaries = bundle["summaries"]
            logger.info(f"Loaded profile cluster model from {MODEL_PATH}")
        except Exception as e:
            self._load_error = str(e)
            logger.warning(f"Could not load cluster model: {e}")

    @property
    def is_ready(self) -> bool:
        return self._kmeans is not None

    def segments(self) -> dict:
        if not self.is_ready:
            return {"segments": [], "error": self._load_error}
        return {"segments": [{"cluster_id": int(c), **s} for c, s in self._summaries.items()]}

    def assign(self, profile: dict) -> dict:
        if not self.is_ready:
            return {"cluster_id": None, "error": self._load_error}

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
        X_scaled = self._scaler.transform(X)

        cluster_id = int(self._kmeans.predict(X_scaled)[0])
        return {"cluster_id": cluster_id, "segment": self._summaries.get(str(cluster_id))}


# Singleton
ml_cluster_service = MLClusterService()
