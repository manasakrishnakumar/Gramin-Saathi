"""
generate_outcome_bootstrap.py — Phase 3 (SYNTHETIC DEMO ONLY)

Built on explicit user instruction overriding the original Phase 3 caveat
in backend/ml/PHASE3_NOTES.md. Read that file for the full reasoning this
overrides: there is no real approval/rejection outcome data anywhere in
this project, and there is no honest way to synthesize it, because the
label being predicted — "did a real government process approve this real
person" — isn't something a rule engine or template generator can stand
in for the way it could for every other phase.

This script exists anyway, at the user's explicit request, as a CLEARLY
LABELED DEMONSTRATION of the modeling technique — every artifact it
produces is tagged "SYNTHETIC_DEMO" end to end (filename, manifest,
service response, and the UI element that displays it), specifically so
it can never be mistaken for a real prediction. It is a teaching/demo
artifact, not a claim about real approval odds.

Synthetic label heuristic (NOT derived from any real data or process):
  - All hard criteria matched -> baseline required for approval at all
    (a hard failure -> outcome is always "rejected", matching the
    existing rule engine's own disqualification logic; this part is at
    least consistent with the deterministic rules already in this app)
  - More matched *soft* criteria (income comfortably under threshold,
    land comfortably under threshold, etc.) -> more "documentation
    margin" -> higher simulated approval probability
  - BPL/disability status matching a scheme's targeting -> simulated
    small approval boost (plausible, not verified)
  - Substantial injected randomness, representing the many real-world
    factors (budget caps, clerical delays, verification backlogs) that
    a synthetic model obviously cannot know about

This is a heuristic simulation, not a fact. See the manifest + every
service response for the disclaimer text.

Output: backend/ml/data/outcome_bootstrap_SYNTHETIC.csv
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

random.seed(7)

OCCUPATIONS = ["farmer", "student", "self_employed", "salaried", "daily_wage", "unemployed", "other"]
GENDERS = ["male", "female", "other"]
CATEGORIES = ["general", "obc", "sc", "st"]
EDUCATION = ["none", "primary", "secondary", "graduate", "postgraduate"]

N_PROFILES = 350
service = RecommendationService()


def random_profile() -> UserProfile:
    return UserProfile(
        age=random.randint(16, 80),
        annual_income=random.choice([0, 40000, 90000, 150000, 250000, 400000, 800000]),
        occupation=random.choice(OCCUPATIONS),
        gender=random.choice(GENDERS),
        category=random.choice(CATEGORIES),
        state=random.choice(["", "Karnataka", "Bihar", "Maharashtra"]),
        land_owned_acres=round(random.choice([0, 0.5, 1, 2.5, 5]), 1),
        is_bpl=random.random() < 0.35,
        is_disabled=random.random() < 0.1,
        education=random.choice(EDUCATION),
        marital_status=random.choice(["single", "married", "widowed"]),
    )


def synthetic_outcome(score_pct: float, matched: int, missed: int, is_disqualified: bool, is_bpl: bool) -> int:
    """Returns 1 = "approved" (simulated), 0 = "rejected" (simulated). See module docstring."""
    if is_disqualified:
        return 0
    total = matched + missed
    documentation_margin = matched / total if total > 0 else 0.0
    p_approve = 0.25 + 0.55 * documentation_margin + 0.10 * (score_pct / 100)
    if is_bpl:
        p_approve += 0.05
    p_approve = min(0.95, max(0.05, p_approve + random.uniform(-0.2, 0.2)))  # real-world noise
    return 1 if random.random() < p_approve else 0


def main():
    rows = []
    for _ in range(N_PROFILES):
        profile = random_profile()
        results = service.score_schemes(profile, top_n=len(SCHEME_REGISTRY), min_score_pct=0.0)
        for r in results:
            matched, missed = len(r.matched_criteria), len(r.missed_criteria)
            outcome = synthetic_outcome(r.score_pct, matched, missed, r.is_disqualified, profile.is_bpl)
            rows.append({
                "age": profile.age,
                "annual_income": profile.annual_income,
                "occupation": profile.occupation,
                "gender": profile.gender,
                "category": profile.category,
                "education": profile.education,
                "land_owned_acres": profile.land_owned_acres,
                "is_bpl": int(profile.is_bpl),
                "is_disabled": int(profile.is_disabled),
                "scheme_id": r.scheme_id,
                "rule_score_pct": r.score_pct,
                "matched_count": matched,
                "missed_count": missed,
                "is_disqualified": int(r.is_disqualified),
                "synthetic_outcome_approved": outcome,
            })

    out_path = Path(__file__).resolve().parent / "outcome_bootstrap_SYNTHETIC.csv"
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    approved = sum(r["synthetic_outcome_approved"] for r in rows)
    print(f"Wrote {len(rows)} SYNTHETIC (profile, scheme, simulated-outcome) rows to {out_path}")
    print(f"Simulated approval rate: {approved}/{len(rows)} = {approved/len(rows):.1%}")
    print("Reminder: this data is entirely synthetic — see module docstring.")


if __name__ == "__main__":
    main()
