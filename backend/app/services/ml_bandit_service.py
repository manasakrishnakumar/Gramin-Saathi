"""
ml_bandit_service.py — Contextual bandit ranker, serving side

Loads the bandit state warmed by ml/simulate_bandit.py's simulation and
exposes it for (a) a read-only "preview" of what it would currently
choose, and (b) `update()`, meant to be called with REAL reward signals
from ml_feedback_service.py as they arrive — unlike every other model in
this pass, this one is designed to keep learning online, in-process,
without a separate retrain step. Persists its state back to disk after
each update so it survives a restart.

Same "never affects eligibility" constraint as the Phase 2 static ranker:
only ever selects among schemes recommendation_service has already
deemed eligible.
"""

from __future__ import annotations

import json
import logging
import sys
import threading
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_ML_DIR = Path(__file__).resolve().parents[2] / "ml"
if str(_ML_DIR) not in sys.path:
    sys.path.insert(0, str(_ML_DIR))

STATE_PATH = Path(__file__).resolve().parents[1] / "models" / "bandit_v1_state.json"
MANIFEST_PATH = Path(__file__).resolve().parents[1] / "models" / "bandit_v1.manifest.json"


class MLBanditService:

    def __init__(self):
        self._bandit = None
        self._manifest: Optional[dict] = None
        self._load_error: Optional[str] = None
        self._lock = threading.Lock()
        self._try_load()

    def _try_load(self):
        try:
            from bandit import LinUCBBandit
            if not STATE_PATH.exists():
                self._load_error = f"No saved bandit state at {STATE_PATH}. Run: python ml/simulate_bandit.py"
                return
            state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
            self._bandit = LinUCBBandit.from_state_dict(state)
            if MANIFEST_PATH.exists():
                self._manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
            logger.info(f"Loaded bandit state from {STATE_PATH} ({len(self._bandit.A)} arms)")
        except Exception as e:
            self._load_error = str(e)
            logger.warning(f"Could not load bandit state: {e}")

    @property
    def is_ready(self) -> bool:
        return self._bandit is not None

    def preview(self, profile: dict, candidate_scheme_ids: list[str]) -> dict:
        if not self.is_ready:
            return {"chosen_scheme_id": None, "error": self._load_error}
        from bandit_features import profile_to_context
        context = profile_to_context(profile)
        chosen, scores = self._bandit.select(candidate_scheme_ids, context)
        return {"chosen_scheme_id": chosen, "scores": scores}

    def update(self, profile: dict, scheme_id: str, reward: float) -> dict:
        """reward: 1.0 for a positive engagement (clicked_apply/checked_eligibility), 0.0 otherwise."""
        if not self.is_ready:
            return {"status": "error", "error": self._load_error}
        from bandit_features import profile_to_context
        with self._lock:
            context = profile_to_context(profile)
            self._bandit.update(scheme_id, context, reward)
            STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
            STATE_PATH.write_text(json.dumps(self._bandit.state_dict()), encoding="utf-8")
        return {"status": "updated", "arm": scheme_id, "n_updates_for_arm": self._bandit.n_updates.get(scheme_id, 0)}

    def manifest(self) -> Optional[dict]:
        return self._manifest


# Singleton
ml_bandit_service = MLBanditService()
