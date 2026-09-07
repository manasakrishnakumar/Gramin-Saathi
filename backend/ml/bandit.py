"""
bandit.py — LinUCB contextual bandit

A genuinely different ML technique from everything else built in this
pass: every other model here is trained once (batch) and served frozen.
This is online learning — it updates incrementally after every single
observed reward, no retraining step, no batch job. That's the actual
point of a bandit over the static Phase 2 ranker: the moment real click
events start flowing in (ml_feedback_service.py), this can learn from
each one immediately instead of waiting to accumulate enough rows for a
periodic retrain.

LinUCB (Li et al., 2010 — "A Contextual-Bandit Approach to Personalized
News Article Recommendation") — one linear model per arm (here: one per
scheme), each maintaining a running (A, b) pair. Predicted score for an
arm = estimated reward (θᵀx) + an uncertainty bonus that shrinks as more
data accumulates for that arm — this is what lets it explore
under-tried arms early and exploit confident ones later, without needing
a separate exploration schedule.

Not tied to Pinecone/Gemini/any paid API — pure numpy, no new dependency.
"""

from __future__ import annotations

import numpy as np


class LinUCBBandit:
    def __init__(self, n_features: int, alpha: float = 1.0):
        self.n_features = n_features
        self.alpha = alpha
        self.A: dict[str, np.ndarray] = {}
        self.b: dict[str, np.ndarray] = {}
        self.n_updates: dict[str, int] = {}

    def _ensure_arm(self, arm_id: str):
        if arm_id not in self.A:
            self.A[arm_id] = np.identity(self.n_features)
            self.b[arm_id] = np.zeros(self.n_features)
            self.n_updates[arm_id] = 0

    def score(self, arm_id: str, context: np.ndarray) -> float:
        self._ensure_arm(arm_id)
        A_inv = np.linalg.inv(self.A[arm_id])
        theta = A_inv @ self.b[arm_id]
        mean = float(theta @ context)
        uncertainty = self.alpha * float(np.sqrt(max(0.0, context @ A_inv @ context)))
        return mean + uncertainty

    def select(self, candidate_arms: list[str], context: np.ndarray) -> tuple[str, dict[str, float]]:
        scores = {arm: self.score(arm, context) for arm in candidate_arms}
        best = max(scores, key=scores.get)
        return best, scores

    def update(self, arm_id: str, context: np.ndarray, reward: float):
        self._ensure_arm(arm_id)
        self.A[arm_id] += np.outer(context, context)
        self.b[arm_id] += reward * context
        self.n_updates[arm_id] += 1

    def state_dict(self) -> dict:
        return {
            "n_features": self.n_features,
            "alpha": self.alpha,
            "A": {k: v.tolist() for k, v in self.A.items()},
            "b": {k: v.tolist() for k, v in self.b.items()},
            "n_updates": self.n_updates,
        }

    @classmethod
    def from_state_dict(cls, state: dict) -> "LinUCBBandit":
        bandit = cls(n_features=state["n_features"], alpha=state["alpha"])
        bandit.A = {k: np.array(v) for k, v in state["A"].items()}
        bandit.b = {k: np.array(v) for k, v in state["b"].items()}
        bandit.n_updates = state["n_updates"]
        return bandit
