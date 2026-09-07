"""
bandit_features.py — fixed-length context vectorizer shared by
simulate_bandit.py and app/services/ml_bandit_service.py.
"""

from __future__ import annotations

import numpy as np

OCCUPATIONS = ["farmer", "student", "self_employed", "salaried", "daily_wage", "unemployed", "other"]
GENDERS = ["male", "female", "other"]
CATEGORIES = ["general", "obc", "sc", "st"]

N_FEATURES = 6 + len(OCCUPATIONS) + len(GENDERS) + len(CATEGORIES)


def profile_to_context(profile: dict) -> np.ndarray:
    features = [
        profile.get("age", 0) / 100.0,
        profile.get("annual_income", 0) / 1_000_000.0,
        profile.get("land_owned_acres", 0) / 10.0,
        float(profile.get("is_bpl", False)),
        float(profile.get("is_disabled", False)),
        1.0,  # bias term
    ]
    features += [1.0 if profile.get("occupation") == o else 0.0 for o in OCCUPATIONS]
    features += [1.0 if profile.get("gender") == g else 0.0 for g in GENDERS]
    features += [1.0 if profile.get("category") == c else 0.0 for c in CATEGORIES]
    return np.array(features, dtype=float)
