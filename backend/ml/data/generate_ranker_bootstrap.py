"""
generate_ranker_bootstrap.py — Phase 2 (cold-start bootstrap only)

Real Phase 2 (a learned ranker on top of the rule engine) needs real user
interaction data — which clicks/applies real users made on real
recommendations. That data doesn't exist yet; it only starts accumulating
once the Phase 0 feedback events endpoints below are actually called by
the live frontend (which they aren't yet — see ml_feedback_service.py).

This script instead produces a COLD-START placeholder dataset: it samples
random synthetic user profiles, runs them through the real, unmodified
rule engine (`app.services.recommendation_service.RecommendationService`,
read-only import — nothing there is touched), and derives a weakly-supervised
"engagement" label from the rule engine's own score_pct plus noise — i.e.
"assume higher-scoring, non-disqualified schemes are more likely to be
clicked, all else equal." This is a deliberately weak, synthetic proxy for
real behavior, NOT real user signal. It exists so the training pipeline
(train_ranker_bootstrap.py) has something to run against today, producing
a real trained artifact that should be thrown away and retrained on real
events the moment real events exist (train_ranker_from_events.py is ready
for that day).

Output: backend/ml/data/ranker_bootstrap.csv
  columns: profile features (age, income, occupation one-hots, ...),
           scheme_id, rule_score_pct, is_disqualified, engagement_label
"""

from __future__ import annotations

import csv
import random
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.recommendation_service import (  # noqa: E402
    RecommendationService,
    UserProfile,
    SCHEME_REGISTRY,
)

random.seed(42)

OCCUPATIONS = ["farmer", "student", "self_employed", "salaried", "daily_wage", "unemployed", "other"]
GENDERS = ["male", "female", "other"]
CATEGORIES = ["general", "obc", "sc", "st"]
STATES = ["", "Karnataka", "Maharashtra", "Uttar Pradesh", "Tamil Nadu", "Bihar"]
EDUCATION = ["none", "primary", "secondary", "graduate", "postgraduate"]
MARITAL = ["single", "married", "widowed", "divorced"]

N_PROFILES = 400
service = RecommendationService()


def random_profile() -> UserProfile:
    return UserProfile(
        age=random.randint(16, 80),
        annual_income=random.choice([0, 40000, 90000, 150000, 250000, 400000, 800000, 1500000]),
        occupation=random.choice(OCCUPATIONS),
        gender=random.choice(GENDERS),
        category=random.choice(CATEGORIES),
        state=random.choice(STATES),
        land_owned_acres=round(random.choice([0, 0, 0.5, 1, 2.5, 5, 8]), 1),
        is_bpl=random.random() < 0.3,
        is_disabled=random.random() < 0.1,
        education=random.choice(EDUCATION),
        marital_status=random.choice(MARITAL),
    )


def weak_engagement_label(score_pct: float, is_disqualified: bool) -> int:
    """
    Synthetic proxy label: higher rule-engine score => more likely to
    "engage" (click Apply/Eligibility), with noise. Disqualified schemes
    never engage. This is NOT real behavior — see module docstring.
    """
    if is_disqualified:
        return 0
    p_click = min(0.95, max(0.02, score_pct / 100))
    # add noise so the model can't just trivially memorize score_pct
    p_click = min(0.97, max(0.01, p_click + random.uniform(-0.15, 0.15)))
    return 1 if random.random() < p_click else 0


def main():
    rows = []
    for _ in range(N_PROFILES):
        profile = random_profile()
        results = service.score_schemes(profile, top_n=len(SCHEME_REGISTRY), min_score_pct=0.0)
        for r in results:
            label = weak_engagement_label(r.score_pct, r.is_disqualified)
            rows.append({
                "age": profile.age,
                "annual_income": profile.annual_income,
                "occupation": profile.occupation,
                "gender": profile.gender,
                "category": profile.category,
                "land_owned_acres": profile.land_owned_acres,
                "is_bpl": int(profile.is_bpl),
                "is_disabled": int(profile.is_disabled),
                "education": profile.education,
                "scheme_id": r.scheme_id,
                "rule_score_pct": r.score_pct,
                "matched_count": len(r.matched_criteria),
                "missed_count": len(r.missed_criteria),
                "is_disqualified": int(r.is_disqualified),
                "engagement_label": label,
            })

    out_path = Path(__file__).resolve().parent / "ranker_bootstrap.csv"
    fieldnames = list(rows[0].keys())
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    pos = sum(r["engagement_label"] for r in rows)
    print(f"Wrote {len(rows)} (profile, scheme) rows from {N_PROFILES} synthetic profiles to {out_path}")
    print(f"Positive (engaged) label rate: {pos}/{len(rows)} = {pos/len(rows):.2%}")


if __name__ == "__main__":
    main()
