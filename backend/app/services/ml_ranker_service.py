"""
ml_ranker_service.py — Phase 2, serving side

Loads the trained gradient-boosted cold-start ranker (ml/train_ranker_bootstrap.py)
— or, once it exists, the real-events version from
ml/train_ranker_from_events.py — and scores (profile, scheme) pairs.

By construction this NEVER decides eligibility. It only produces a
"predicted engagement" score meant to reorder schemes that
`recommendation_service.py`'s unmodified rule engine has already deemed
eligible. `recommendation_service.py` is not imported for modification
here, and this service does not call it — the caller is expected to run
the rule engine first (exactly as the existing /recommend/schemes endpoint
already does) and only pass this service the already-eligible results.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

MODELS_DIR = Path(__file__).resolve().parents[1] / "models"
# Prefer the real-events model if it exists; fall back to the synthetic bootstrap.
_CANDIDATES = [
    ("v1-real-events", MODELS_DIR / "ranker_events_v1.joblib", MODELS_DIR / "ranker_events_v1.manifest.json"),
    ("v1-bootstrap", MODELS_DIR / "ranker_bootstrap_v1.joblib", MODELS_DIR / "ranker_bootstrap_v1.manifest.json"),
]


class MLRankerService:

    def __init__(self):
        self._model = None
        self._feature_columns: list[str] = []
        self._manifest: Optional[dict] = None
        self._load_error: Optional[str] = None
        self._try_load()

    def _try_load(self):
        import joblib
        for version, model_path, manifest_path in _CANDIDATES:
            if model_path.exists():
                try:
                    bundle = joblib.load(model_path)
                    self._model = bundle["model"]
                    self._feature_columns = bundle["feature_columns"]
                    if manifest_path.exists():
                        self._manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                    logger.info(f"Loaded ranker ({version}) from {model_path}")
                    return
                except Exception as e:
                    self._load_error = str(e)
                    logger.warning(f"Failed loading ranker {model_path}: {e}")
        self._load_error = (
            "No trained ranker found. Run: python ml/data/generate_ranker_bootstrap.py "
            "&& python ml/train_ranker_bootstrap.py"
        )

    @property
    def is_ready(self) -> bool:
        return self._model is not None

    def score(self, profile: dict, scheme_result: dict) -> Optional[float]:
        """
        profile: dict with age/annual_income/occupation/gender/category/
                 education/land_owned_acres/is_bpl/is_disabled
        scheme_result: dict with rule_score_pct/matched_count/missed_count
        Returns predicted engagement probability (0-1), or None if unavailable.
        """
        if not self.is_ready:
            return None
        import pandas as pd

        row = {
            "age": profile.get("age", 0),
            "annual_income": profile.get("annual_income", 0),
            "land_owned_acres": profile.get("land_owned_acres", 0),
            "is_bpl": int(profile.get("is_bpl", False)),
            "is_disabled": int(profile.get("is_disabled", False)),
            "rule_score_pct": scheme_result.get("rule_score_pct", 0),
            "matched_count": scheme_result.get("matched_count", 0),
            "missed_count": scheme_result.get("missed_count", 0),
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

        proba = self._model.predict_proba(X)[0][1]
        return round(float(proba), 4)

    def manifest(self) -> Optional[dict]:
        return self._manifest


# Singleton
ml_ranker_service = MLRankerService()
