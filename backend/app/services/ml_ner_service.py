"""
ml_ner_service.py — Scheme-data NER, serving side

Loads the trained CRF from ml/train_ner_model.py and extracts structured
entities (SCHEME, MINISTRY, AMOUNT, AGE, PCT) from free text — meant for
newly scraped scheme documents (scraper_service.py), to reduce how much
of SCHEME_REGISTRY has to be hand-transcribed.
"""

from __future__ import annotations

import json
import logging
import pickle
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_ML_DIR = Path(__file__).resolve().parents[2] / "ml"
if str(_ML_DIR) not in sys.path:
    sys.path.insert(0, str(_ML_DIR))

MODEL_PATH = Path(__file__).resolve().parents[1] / "models" / "ner_crf_v1.pkl"
MANIFEST_PATH = Path(__file__).resolve().parents[1] / "models" / "ner_crf_v1.manifest.json"


class MLNERService:

    def __init__(self):
        self._model = None
        self._manifest: Optional[dict] = None
        self._load_error: Optional[str] = None
        self._try_load()

    def _try_load(self):
        try:
            if not MODEL_PATH.exists():
                self._load_error = (
                    f"No trained model at {MODEL_PATH}. Run: "
                    f"python ml/data/generate_ner_dataset.py && python ml/train_ner_model.py"
                )
                return
            with open(MODEL_PATH, "rb") as f:
                self._model = pickle.load(f)
            if MANIFEST_PATH.exists():
                self._manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
            logger.info(f"Loaded NER CRF model from {MODEL_PATH}")
        except Exception as e:
            self._load_error = str(e)
            logger.warning(f"Could not load NER model: {e}")

    @property
    def is_ready(self) -> bool:
        return self._model is not None

    def extract(self, text: str) -> dict:
        if not self.is_ready:
            return {"entities": [], "error": self._load_error}

        from ner_features import tokenize, sentence_features, tags_to_entities

        tokens = tokenize(text)
        if not tokens:
            return {"entities": []}

        features = sentence_features(tokens)
        tags = self._model.predict([features])[0]
        entities = tags_to_entities(tokens, tags)
        return {"entities": entities}

    def manifest(self) -> Optional[dict]:
        return self._manifest


# Singleton
ml_ner_service = MLNERService()
