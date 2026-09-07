"""
ml_voice_quality_service.py — Voice transcription quality, serving side

Loads the trained classifier from ml/train_transcript_quality_classifier.py
and flags whether a transcript (real Sarvam STT output, or any text) looks
like it may contain ASR errors — meant to trigger a "please repeat" prompt
in the voice UI rather than silently feeding a garbled transcript into the
RAG pipeline. Never blocks by itself — informational flag only.

KNOWN LIMITATION: the reference vocabulary/bigram set is built from only
~100 clean synthetic sentences (see ml/data/generate_transcript_quality_dataset.py)
— genuinely fine spoken text using vocabulary outside that small domain
(e.g. describing a personal medical situation in ordinary words) can still
false-positive as "garbled." Verified directly: 2 of 3 held-out clean test
sentences classify correctly after expanding the reference corpus once
already; the third still false-positives. Treat this as a soft nudge, not
a confident verdict — same reasoning as ml_groundedness_service.py's
documented limitation.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_ML_DIR = Path(__file__).resolve().parents[2] / "ml"
if str(_ML_DIR) not in sys.path:
    sys.path.insert(0, str(_ML_DIR))

MODEL_PATH = Path(__file__).resolve().parents[1] / "models" / "voice_quality_classifier_v1.joblib"
MANIFEST_PATH = Path(__file__).resolve().parents[1] / "models" / "voice_quality_classifier_v1.manifest.json"


class MLVoiceQualityService:

    def __init__(self):
        self._model = None
        self._vocab = None
        self._bigrams = None
        self._manifest: Optional[dict] = None
        self._load_error: Optional[str] = None
        self._try_load()

    def _try_load(self):
        try:
            import joblib
            if not MODEL_PATH.exists():
                self._load_error = (
                    f"No trained model at {MODEL_PATH}. Run: "
                    f"python ml/data/generate_transcript_quality_dataset.py && python ml/train_transcript_quality_classifier.py"
                )
                return
            bundle = joblib.load(MODEL_PATH)
            self._model = bundle["model"]
            self._vocab = bundle["vocab"]
            self._bigrams = bundle["bigrams"]
            if MANIFEST_PATH.exists():
                self._manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
            logger.info(f"Loaded voice quality classifier from {MODEL_PATH}")
        except Exception as e:
            self._load_error = str(e)
            logger.warning(f"Could not load voice quality classifier: {e}")

    @property
    def is_ready(self) -> bool:
        return self._model is not None

    def check(self, transcript: str) -> dict:
        if not self.is_ready:
            return {"is_likely_garbled": None, "error": self._load_error}
        if not transcript or not transcript.strip():
            return {"is_likely_garbled": True, "reason": "empty_transcript"}

        from transcript_quality_features import extract_features, FEATURE_NAMES
        import pandas as pd

        feats = extract_features(transcript, self._vocab, self._bigrams)
        X = pd.DataFrame([feats])[FEATURE_NAMES]
        clean_proba = float(self._model.predict_proba(X)[0][1])
        return {
            "is_likely_garbled": clean_proba < 0.5,
            "clean_probability": round(clean_proba, 4),
        }

    def manifest(self) -> Optional[dict]:
        return self._manifest


# Singleton
ml_voice_quality_service = MLVoiceQualityService()
