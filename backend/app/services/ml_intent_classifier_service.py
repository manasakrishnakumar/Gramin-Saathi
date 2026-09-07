"""
ml_intent_classifier_service.py — Phase 1, serving side

Loads the trained TF-IDF + Logistic Regression model produced by
ml/train_intent_classifier.py and serves predictions from it.

This is intentionally a SEPARATE service from
`app.services.intent_service.py` (which is completely untouched) — this
lets the two be compared side by side (see the /ml/intent/compare
endpoint) before ever deciding to route real traffic through the trained
model instead of the existing rule+LLM hybrid.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

MODEL_PATH = Path(__file__).resolve().parents[1] / "models" / "intent_classifier_v1.joblib"
MANIFEST_PATH = Path(__file__).resolve().parents[1] / "models" / "intent_classifier_v1.manifest.json"


class MLIntentClassifierService:

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
                    f"python ml/data/generate_intent_dataset.py && python ml/train_intent_classifier.py"
                )
                return
            self._model = joblib.load(MODEL_PATH)
            if MANIFEST_PATH.exists():
                self._manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
            logger.info(f"Loaded trained intent classifier from {MODEL_PATH}")
        except Exception as e:
            self._load_error = str(e)
            logger.warning(f"Could not load trained intent classifier: {e}")

    @property
    def is_ready(self) -> bool:
        return self._model is not None

    def classify(self, text: str) -> dict:
        if not self.is_ready:
            return {"intent": None, "confidence": None, "error": self._load_error}

        pred = self._model.predict([text])[0]
        proba = self._model.predict_proba([text])[0]
        classes = list(self._model.classes_)
        confidence = float(proba[classes.index(pred)])

        return {
            "intent": pred,
            "confidence": round(confidence, 4),
            "method": "trained_classifier",
            "model_version": self._manifest.get("version") if self._manifest else None,
        }

    def manifest(self) -> Optional[dict]:
        return self._manifest


# Singleton
ml_intent_classifier_service = MLIntentClassifierService()
