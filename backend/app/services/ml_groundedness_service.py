"""
ml_groundedness_service.py — Answer groundedness scoring, serving side

Loads the trained classifier from ml/train_groundedness_classifier.py and
scores whether a generated answer is supported by its retrieved context.
Used by rag_service.py to flag low-confidence answers with a "verify with
the official source" note, alongside (never instead of) the normal answer.

KNOWN LIMITATION (found and documented while building this, not glossed
over): the synthetic training data's "paraphrases" come from a rule-based
synonym substitution, not a real LLM rewrite — so the classifier learned
to weight literal word/number overlap fairly heavily. It reliably catches
fabricated numbers, topic mismatches, and "same vocabulary but wrong
target audience" hallucinations (all tested directly), but can
false-positive (flag as "ungrounded") on a genuinely correct answer that
happens to be very heavily reworded in vocabulary the model never saw
during training. Real Gemini answers asked to "answer based on the
context above" tend to retain key terms/numbers rather than write that
kind of free paraphrase, so this is a narrower real-world gap than the
adversarial test case that exposed it — but it's real, so this is wired
in as a soft/informational signal (low threshold, no hard warning icon),
not a confident verdict. See ml/README.md.
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

MODEL_PATH = Path(__file__).resolve().parents[1] / "models" / "groundedness_classifier_v1.joblib"
MANIFEST_PATH = Path(__file__).resolve().parents[1] / "models" / "groundedness_classifier_v1.manifest.json"


class MLGroundednessService:

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
                    f"python ml/data/generate_groundedness_dataset.py && python ml/train_groundedness_classifier.py"
                )
                return
            self._model = joblib.load(MODEL_PATH)
            if MANIFEST_PATH.exists():
                self._manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
            logger.info(f"Loaded groundedness classifier from {MODEL_PATH}")
        except Exception as e:
            self._load_error = str(e)
            logger.warning(f"Could not load groundedness classifier: {e}")

    @property
    def is_ready(self) -> bool:
        return self._model is not None

    def score(self, context: str, answer: str) -> dict:
        if not self.is_ready:
            return {"grounded_probability": None, "error": self._load_error}
        if not context or not context.strip():
            # No retrieved context to check against (e.g. general-knowledge
            # fallback) — groundedness isn't a meaningful question here.
            return {"grounded_probability": None, "reason": "no_context_to_check"}

        try:
            from groundedness_features import extract_features, FEATURE_NAMES
            import pandas as pd

            feats = extract_features(context, answer)
            X = pd.DataFrame([feats])[FEATURE_NAMES]
            proba = float(self._model.predict_proba(X)[0][1])
            return {
                "grounded_probability": round(proba, 4),
                "is_likely_grounded": proba >= 0.5,
                "features": feats,
            }
        except Exception as e:
            logger.warning(f"Groundedness scoring failed: {e}")
            return {"grounded_probability": None, "error": str(e)}

    def manifest(self) -> Optional[dict]:
        return self._manifest


# Singleton
ml_groundedness_service = MLGroundednessService()
