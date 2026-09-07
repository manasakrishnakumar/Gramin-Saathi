"""
simulate_bandit.py — Contextual bandit ranker, simulation-verified

Proves the LinUCB mechanism (bandit.py) actually learns, using a
simulated reward stream (same weak-supervision heuristic as Phase 2's
bootstrap ranker: higher rule_score_pct -> higher simulated click
probability, plus noise). This is explicitly a simulation of the
MECHANISM, not a claim about real user behavior — same honesty
standard as everywhere else in this pass.

What "working" means here, concretely, and what this script measures:
  1. Regret (oracle's expected reward - bandit's expected reward) in a
     rolling window should trend toward 0 as rounds increase.
  2. The bandit's agreement rate with the oracle (did it pick the
     actually-best eligible scheme?) should increase over rounds.

Each round uses the REAL, unmodified recommendation_service rule engine
to get eligible schemes for a random synthetic profile — the bandit only
ever chooses among schemes the rule engine has already deemed eligible,
same "never affects eligibility, only reorders" constraint as Phase 2.

Usage:
    cd backend
    python ml/simulate_bandit.py
"""

from __future__ import annotations

import json
import random
import sys
import time
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.services.recommendation_service import RecommendationService, UserProfile  # noqa: E402
from bandit import LinUCBBandit  # noqa: E402
from bandit_features import profile_to_context, N_FEATURES, OCCUPATIONS, GENDERS, CATEGORIES  # noqa: E402

random.seed(21)

N_ROUNDS = 3000
WINDOW = 200

MODEL_DIR = BACKEND_ROOT / "app" / "models"
STATE_PATH = MODEL_DIR / "bandit_v1_state.json"
MANIFEST_PATH = MODEL_DIR / "bandit_v1.manifest.json"

service = RecommendationService()


def random_profile() -> UserProfile:
    return UserProfile(
        age=random.randint(18, 75),
        annual_income=random.choice([0, 40000, 90000, 150000, 250000, 400000, 800000]),
        occupation=random.choice(OCCUPATIONS),
        gender=random.choice(GENDERS),
        category=random.choice(CATEGORIES),
        state="",
        land_owned_acres=round(random.choice([0, 0.5, 1, 2.5, 5]), 1),
        is_bpl=random.random() < 0.3,
        is_disabled=random.random() < 0.1,
        education=random.choice(["none", "primary", "secondary", "graduate"]),
        marital_status="single",
    )


def true_reward_probability(score_pct: float) -> float:
    """Same weak-supervision heuristic as Phase 2's bootstrap ranker — see its docstring."""
    return min(0.95, max(0.02, score_pct / 100))


def main():
    bandit = LinUCBBandit(n_features=N_FEATURES, alpha=1.0)

    regrets: list[float] = []
    agreements: list[int] = []
    skipped = 0

    t0 = time.time()
    for round_i in range(N_ROUNDS):
        profile = random_profile()
        results = service.score_schemes(profile, top_n=50, min_score_pct=0.0)
        eligible = [r for r in results if not r.is_disqualified and r.score_pct > 0]
        if not eligible:
            skipped += 1
            continue

        context = profile_to_context({
            "age": profile.age, "annual_income": profile.annual_income,
            "land_owned_acres": profile.land_owned_acres, "is_bpl": profile.is_bpl,
            "is_disabled": profile.is_disabled, "occupation": profile.occupation,
            "gender": profile.gender, "category": profile.category,
        })
        candidate_arms = [r.scheme_id for r in eligible]
        scheme_by_id = {r.scheme_id: r for r in eligible}

        chosen_arm, _ = bandit.select(candidate_arms, context)
        oracle_arm = max(eligible, key=lambda r: r.score_pct).scheme_id

        chosen_p = true_reward_probability(scheme_by_id[chosen_arm].score_pct)
        oracle_p = true_reward_probability(scheme_by_id[oracle_arm].score_pct)
        regrets.append(oracle_p - chosen_p)
        agreements.append(1 if chosen_arm == oracle_arm else 0)

        # Sample an actual reward (0/1) for the chosen arm and update online.
        reward = 1.0 if random.random() < chosen_p else 0.0
        bandit.update(chosen_arm, context, reward)

        if (round_i + 1) % 500 == 0:
            recent_regret = sum(regrets[-WINDOW:]) / len(regrets[-WINDOW:])
            recent_agreement = sum(agreements[-WINDOW:]) / len(agreements[-WINDOW:])
            print(f"  round {round_i+1:5d}: rolling regret (last {WINDOW}) = {recent_regret:.4f}, "
                  f"oracle agreement rate = {recent_agreement:.1%}")

    train_seconds = round(time.time() - t0, 2)

    early_regret = sum(regrets[:WINDOW]) / len(regrets[:WINDOW])
    late_regret = sum(regrets[-WINDOW:]) / len(regrets[-WINDOW:])
    early_agreement = sum(agreements[:WINDOW]) / len(agreements[:WINDOW])
    late_agreement = sum(agreements[-WINDOW:]) / len(agreements[-WINDOW:])

    print(f"\nSimulated {len(regrets)} rounds ({skipped} skipped, no eligible schemes) in {train_seconds}s")
    print(f"Regret:          first {WINDOW} rounds = {early_regret:.4f}  ->  last {WINDOW} rounds = {late_regret:.4f}")
    print(f"Oracle agreement: first {WINDOW} rounds = {early_agreement:.1%}  ->  last {WINDOW} rounds = {late_agreement:.1%}")
    if late_regret < early_regret and late_agreement > early_agreement:
        print("CONVERGED: regret dropped and oracle-agreement rose over the simulation — the bandit is learning.")
    else:
        print("WARNING: convergence signal not clearly present — inspect before trusting this.")

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(bandit.state_dict(), f)

    manifest = {
        "model": "LinUCB contextual bandit (online learning)",
        "version": "v1",
        "trained_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "simulated_rounds": len(regrets),
        "train_seconds": train_seconds,
        "early_window_regret": round(early_regret, 4),
        "late_window_regret": round(late_regret, 4),
        "early_window_oracle_agreement": round(early_agreement, 4),
        "late_window_oracle_agreement": round(late_agreement, 4),
        "converged": bool(late_regret < early_regret and late_agreement > early_agreement),
        "note": (
            "SIMULATED reward stream (same weak-supervision heuristic as the Phase 2 "
            "bootstrap ranker), not real user behavior. Demonstrates the online-learning "
            "mechanism converges given a reward signal — swap in real click events from "
            "ml_feedback_service.py via ml_bandit_service.update() to make this real."
        ),
        "artifact": str(STATE_PATH.relative_to(BACKEND_ROOT)),
    }
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"Saved bandit state -> {STATE_PATH}")
    print(f"Saved manifest      -> {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
