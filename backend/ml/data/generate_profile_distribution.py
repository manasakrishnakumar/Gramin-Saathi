"""
generate_profile_distribution.py — Profile anomaly detection

Unlike the other bootstrap generators, this one needs NO labels at all —
IsolationForest is unsupervised, it just needs a realistic sample of
*normal* profiles to learn what "normal" looks like, so it can flag
anything that doesn't fit (garbage/bot input, wildly inconsistent
combinations like age 12 with 40 acres of land and postgraduate
education). Reuses the same realistic value ranges as the other
generators, sampled from `app.services.recommendation_service`'s field
options (read-only import).

Output: backend/ml/data/profile_distribution.csv
"""

from __future__ import annotations

import csv
import random
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

random.seed(3)

OCCUPATIONS = ["farmer", "student", "self_employed", "salaried", "daily_wage", "unemployed", "other"]
GENDERS = ["male", "female", "other"]
CATEGORIES = ["general", "obc", "sc", "st"]
EDUCATION = ["none", "primary", "secondary", "graduate", "postgraduate"]

N_PROFILES = 1000

# Plausible (age -> income/education/land) correlations, so the "normal"
# distribution isn't just uniform random noise (which would make almost
# nothing look anomalous by comparison).
def realistic_profile() -> dict:
    age = max(16, min(85, int(random.gauss(40, 16))))

    if age < 22:
        education = random.choice(["none", "primary", "secondary", "secondary", "graduate"])
        occupation = random.choice(["student", "student", "daily_wage", "unemployed"])
    elif age < 60:
        education = random.choice(["none", "primary", "secondary", "graduate", "postgraduate"])
        occupation = random.choice(OCCUPATIONS)
    else:
        education = random.choice(["none", "primary", "secondary"])
        occupation = random.choice(["farmer", "unemployed", "daily_wage", "self_employed"])

    income_band = {
        "student": (0, 50000), "unemployed": (0, 30000), "daily_wage": (20000, 150000),
        "farmer": (20000, 400000), "self_employed": (50000, 800000),
        "salaried": (100000, 1200000), "other": (0, 300000),
    }[occupation]
    annual_income = max(0, int(random.gauss((income_band[0] + income_band[1]) / 2, income_band[1] / 4)))

    land = round(max(0, random.gauss(1.5, 2)), 1) if occupation == "farmer" else round(max(0, random.gauss(0.2, 0.6)), 1)

    return {
        "age": age,
        "annual_income": annual_income,
        "occupation": occupation,
        "gender": random.choice(GENDERS),
        "category": random.choice(CATEGORIES),
        "education": education,
        "land_owned_acres": land,
        "is_bpl": int(random.random() < (0.4 if annual_income < 150000 else 0.05)),
        "is_disabled": int(random.random() < 0.08),
    }


def main():
    rows = [realistic_profile() for _ in range(N_PROFILES)]
    out_path = Path(__file__).resolve().parent / "profile_distribution.csv"
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} realistic synthetic profiles to {out_path}")


if __name__ == "__main__":
    main()
