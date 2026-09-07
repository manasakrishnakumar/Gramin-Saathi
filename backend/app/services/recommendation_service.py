"""
recommendation_service.py
Rule-based Personalized Scheme Recommendation Engine.

No ML/training required. Eligibility rules are public domain knowledge.
Scoring is purely deterministic: weight × matched_criteria.
Explainability = surfacing which criteria matched/failed.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Optional
import math


# ---------------------------------------------------------------------------
# Domain types
# ---------------------------------------------------------------------------

@dataclass
class UserProfile:
    age: int
    annual_income: float          # in INR
    occupation: str               # farmer, student, self_employed, salaried, daily_wage, unemployed, other
    gender: str                   # male, female, transgender, other
    category: str                 # general, obc, sc, st
    state: str                    # e.g. "Karnataka", "Maharashtra", "" means all
    land_owned_acres: float = 0.0
    is_bpl: bool = False          # Below Poverty Line card
    is_disabled: bool = False
    education: str = "none"       # none, primary, secondary, graduate, postgraduate
    marital_status: str = "single"  # single, married, widowed, divorced


@dataclass
class CriterionResult:
    label: str           # Human-readable: "Annual income ≤ ₹1.5 lakh"
    field: str           # Profile field name
    matched: bool
    weight: int          # 1=minor, 2=moderate, 3=critical
    is_hard: bool        # If True and not matched → scheme score = 0
    actual_value: Any    # What the user has
    required_value: Any  # What's required


@dataclass
class SchemeResult:
    scheme_id: str
    name: str
    ministry: str
    description: str
    apply_url: str
    score_pct: float                          # 0–100
    criteria_results: list[CriterionResult]
    matched_criteria: list[CriterionResult]   # only matched
    missed_criteria: list[CriterionResult]    # only missed
    is_disqualified: bool = False             # A hard criterion failed


# ---------------------------------------------------------------------------
# Scheme Registry — 18 real Indian government schemes
# ---------------------------------------------------------------------------
#
# Each criterion dict:
#   field    : UserProfile attribute name (or special computed like "is_bpl")
#   op       : eq | lte | gte | in | not_in | range | any (always True)
#   value    : threshold / set / [min, max]
#   weight   : 1 | 2 | 3
#   label    : human readable
#   hard     : bool — disqualifier if not matched
#

SCHEME_REGISTRY: list[dict] = [

    # ─────────────────────────────────────────────────
    # AGRICULTURE
    # ─────────────────────────────────────────────────
    {
        "id": "pm_kisan",
        "name": "PM-KISAN",
        "ministry": "Ministry of Agriculture & Farmers' Welfare",
        "description": "Income support of ₹6,000/year in 3 installments to small & marginal farmers.",
        "apply_url": "https://pmkisan.gov.in/",
        "criteria": [
            {"field": "occupation", "op": "in", "value": ["farmer"], "weight": 3,
             "label": "Must be a farmer", "hard": True},
            {"field": "land_owned_acres", "op": "lte", "value": 5.0, "weight": 2,
             "label": "Land owned ≤ 5 acres (small/marginal)", "hard": False},
            {"field": "annual_income", "op": "lte", "value": 200000, "weight": 2,
             "label": "Annual income ≤ ₹2 lakh", "hard": False},
            {"field": "age", "op": "gte", "value": 18, "weight": 1,
             "label": "Age ≥ 18 years", "hard": True},
        ],
    },

    {
        "id": "pm_fasal_bima",
        "name": "PM Fasal Bima Yojana",
        "ministry": "Ministry of Agriculture & Farmers' Welfare",
        "description": "Crop insurance scheme providing financial support to farmers in case of crop failure.",
        "apply_url": "https://pmfby.gov.in/",
        "criteria": [
            {"field": "occupation", "op": "in", "value": ["farmer"], "weight": 3,
             "label": "Must be a farmer", "hard": True},
            {"field": "land_owned_acres", "op": "gte", "value": 0.1, "weight": 2,
             "label": "Must own/lease land", "hard": False},
            {"field": "age", "op": "gte", "value": 18, "weight": 1,
             "label": "Age ≥ 18 years", "hard": True},
        ],
    },

    {
        "id": "kisan_credit_card",
        "name": "Kisan Credit Card (KCC)",
        "ministry": "Ministry of Agriculture & Farmers' Welfare",
        "description": "Affordable credit for farmers for agricultural needs up to ₹3 lakh at 4% interest.",
        "apply_url": "https://www.nabard.org/content1.aspx?id=572",
        "criteria": [
            {"field": "occupation", "op": "in", "value": ["farmer"], "weight": 3,
             "label": "Must be a farmer/cultivator", "hard": True},
            {"field": "age", "op": "range", "value": [18, 75], "weight": 1,
             "label": "Age between 18–75 years", "hard": True},
            {"field": "land_owned_acres", "op": "gte", "value": 0.5, "weight": 2,
             "label": "Cultivable land ≥ 0.5 acres", "hard": False},
        ],
    },

    # ─────────────────────────────────────────────────
    # WOMEN / MATERNAL
    # ─────────────────────────────────────────────────
    {
        "id": "pm_matru_vandana",
        "name": "Pradhan Mantri Matru Vandana Yojana",
        "ministry": "Ministry of Women & Child Development",
        "description": "₹5,000 cash incentive for first live birth to support pregnant/lactating women.",
        "apply_url": "https://pmmvy.wcd.gov.in/",
        "criteria": [
            {"field": "gender", "op": "in", "value": ["female"], "weight": 3,
             "label": "Must be female", "hard": True},
            {"field": "age", "op": "gte", "value": 19, "weight": 2,
             "label": "Age ≥ 19 years", "hard": True},
            {"field": "annual_income", "op": "lte", "value": 800000, "weight": 1,
             "label": "Annual income ≤ ₹8 lakh", "hard": False},
        ],
    },

    {
        "id": "mahila_shakti_kendra",
        "name": "Mahila Shakti Kendra Scheme",
        "ministry": "Ministry of Women & Child Development",
        "description": "Empowering rural women through community participation and convergence of schemes.",
        "apply_url": "https://wcd.nic.in/schemes/mahila-shakti-kendra",
        "criteria": [
            {"field": "gender", "op": "in", "value": ["female"], "weight": 3,
             "label": "Must be female", "hard": True},
            {"field": "annual_income", "op": "lte", "value": 300000, "weight": 2,
             "label": "Annual income ≤ ₹3 lakh (rural/semi-urban)", "hard": False},
        ],
    },

    # ─────────────────────────────────────────────────
    # STUDENTS / EDUCATION
    # ─────────────────────────────────────────────────
    {
        "id": "national_scholarship_portal",
        "name": "National Scholarship Portal (NSP) Schemes",
        "ministry": "Ministry of Education",
        "description": "Pre & post matric scholarships for SC/ST/OBC/minority students.",
        "apply_url": "https://scholarships.gov.in/",
        "criteria": [
            {"field": "occupation", "op": "in", "value": ["student"], "weight": 3,
             "label": "Must be a student", "hard": True},
            {"field": "age", "op": "range", "value": [14, 30], "weight": 1,
             "label": "Age 14–30 years", "hard": False},
            {"field": "category", "op": "in", "value": ["sc", "st", "obc"], "weight": 2,
             "label": "SC/ST/OBC category", "hard": False},
            {"field": "annual_income", "op": "lte", "value": 250000, "weight": 2,
             "label": "Family income ≤ ₹2.5 lakh/year", "hard": False},
        ],
    },

    {
        "id": "pm_scholarship_scheme",
        "name": "PM Scholarship Scheme (PMSS)",
        "ministry": "Ministry of Home Affairs",
        "description": "Scholarships for wards of ex-servicemen/police officers; technical/professional courses.",
        "apply_url": "https://ksb.gov.in/pmss.htm",
        "criteria": [
            {"field": "occupation", "op": "in", "value": ["student"], "weight": 3,
             "label": "Must be a student", "hard": True},
            {"field": "age", "op": "range", "value": [18, 25], "weight": 1,
             "label": "Age 18–25 years", "hard": False},
            {"field": "annual_income", "op": "lte", "value": 600000, "weight": 2,
             "label": "Family income ≤ ₹6 lakh/year", "hard": False},
        ],
    },

    # ─────────────────────────────────────────────────
    # HEALTH
    # ─────────────────────────────────────────────────
    {
        "id": "ayushman_bharat",
        "name": "Ayushman Bharat – PM-JAY",
        "ministry": "Ministry of Health & Family Welfare",
        "description": "₹5 lakh/year health cover for secondary & tertiary hospitalisation for BPL families.",
        "apply_url": "https://pmjay.gov.in/",
        "criteria": [
            {"field": "is_bpl", "op": "eq", "value": True, "weight": 3,
             "label": "Must be BPL / SECC-listed household", "hard": True},
            {"field": "annual_income", "op": "lte", "value": 100000, "weight": 2,
             "label": "Annual income ≤ ₹1 lakh", "hard": False},
        ],
    },

    {
        "id": "pm_suraksha_bima",
        "name": "PM Suraksha Bima Yojana",
        "ministry": "Ministry of Finance",
        "description": "₹2 lakh accident insurance for ₹20/year premium. Bank account mandatory.",
        "apply_url": "https://financialservices.gov.in/insurance-divisions/Government-Sponsored-Socially-Oriented-Insurance-Schemes/Pradhan-Mantri-Suraksha-Bima-Yojana(PMSBY)",
        "criteria": [
            {"field": "age", "op": "range", "value": [18, 70], "weight": 2,
             "label": "Age 18–70 years", "hard": True},
            {"field": "annual_income", "op": "lte", "value": 500000, "weight": 1,
             "label": "Annual income ≤ ₹5 lakh (target low-income)", "hard": False},
        ],
    },

    {
        "id": "pm_jeevan_jyoti",
        "name": "PM Jeevan Jyoti Bima Yojana",
        "ministry": "Ministry of Finance",
        "description": "₹2 lakh life insurance for ₹436/year premium for bank account holders.",
        "apply_url": "https://financialservices.gov.in/insurance-divisions/Government-Sponsored-Socially-Oriented-Insurance-Schemes/Pradhan-Mantri-Jeevan-Jyoti-Bima-Yojana(PMJJBY)",
        "criteria": [
            {"field": "age", "op": "range", "value": [18, 50], "weight": 2,
             "label": "Age 18–50 years", "hard": True},
            {"field": "annual_income", "op": "lte", "value": 500000, "weight": 1,
             "label": "Annual income ≤ ₹5 lakh", "hard": False},
        ],
    },

    # ─────────────────────────────────────────────────
    # HOUSING
    # ─────────────────────────────────────────────────
    {
        "id": "pm_awas_yojana_gramin",
        "name": "PM Awas Yojana – Gramin (PMAY-G)",
        "ministry": "Ministry of Rural Development",
        "description": "Financial assistance to construct pucca houses for rural BPL households.",
        "apply_url": "https://pmayg.nic.in/",
        "criteria": [
            {"field": "is_bpl", "op": "eq", "value": True, "weight": 3,
             "label": "Must be BPL household", "hard": True},
            {"field": "land_owned_acres", "op": "lte", "value": 2.5, "weight": 1,
             "label": "Land ≤ 2.5 acres (rural small holding)", "hard": False},
            {"field": "annual_income", "op": "lte", "value": 300000, "weight": 2,
             "label": "Annual income ≤ ₹3 lakh", "hard": False},
            {"field": "age", "op": "gte", "value": 18, "weight": 1,
             "label": "Age ≥ 18 years", "hard": True},
        ],
    },

    # ─────────────────────────────────────────────────
    # EMPLOYMENT / LIVELIHOOD
    # ─────────────────────────────────────────────────
    {
        "id": "mgnregs",
        "name": "MGNREGS (Mahatma Gandhi NREGS)",
        "ministry": "Ministry of Rural Development",
        "description": "100 days/year guaranteed wage employment to rural households; adults seeking unskilled work.",
        "apply_url": "https://nrega.nic.in/",
        "criteria": [
            {"field": "age", "op": "gte", "value": 18, "weight": 2,
             "label": "Age ≥ 18 years (adult)", "hard": True},
            {"field": "occupation", "op": "in",
             "value": ["daily_wage", "farmer", "unemployed", "self_employed", "other"],
             "weight": 2,
             "label": "Unskilled/manual work seeker", "hard": False},
            {"field": "annual_income", "op": "lte", "value": 200000, "weight": 2,
             "label": "Annual income ≤ ₹2 lakh (rural poor)", "hard": False},
        ],
    },

    {
        "id": "pm_mudra_yojana",
        "name": "PM MUDRA Yojana",
        "ministry": "Ministry of Finance",
        "description": "Loans ₹50K–₹10 lakh for non-farm micro/small enterprises (Shishu/Kishor/Tarun).",
        "apply_url": "https://mudra.org.in/",
        "criteria": [
            {"field": "occupation", "op": "in", "value": ["self_employed"], "weight": 3,
             "label": "Must be self-employed / small business owner", "hard": True},
            {"field": "age", "op": "range", "value": [18, 65], "weight": 1,
             "label": "Age 18–65 years", "hard": True},
            {"field": "annual_income", "op": "lte", "value": 1000000, "weight": 1,
             "label": "Annual income ≤ ₹10 lakh", "hard": False},
        ],
    },

    {
        "id": "startup_india_seed_fund",
        "name": "Startup India Seed Fund Scheme",
        "ministry": "Ministry of Commerce & Industry",
        "description": "Seed funding up to ₹50 lakh for early-stage DPIIT-recognised startups.",
        "apply_url": "https://seedfund.startupindia.gov.in/",
        "criteria": [
            {"field": "occupation", "op": "in", "value": ["self_employed"], "weight": 3,
             "label": "Must be self-employed / startup founder", "hard": True},
            {"field": "age", "op": "range", "value": [18, 50], "weight": 1,
             "label": "Age 18–50 years", "hard": False},
        ],
    },

    # ─────────────────────────────────────────────────
    # DISABILITY / SOCIAL
    # ─────────────────────────────────────────────────
    {
        "id": "deen_dayal_disability",
        "name": "Deen Dayal Disabled Rehabilitation Scheme",
        "ministry": "Ministry of Social Justice & Empowerment",
        "description": "Grants to NGOs for rehabilitation of persons with disabilities.",
        "apply_url": "https://disabilityaffairs.gov.in/content/page/ddrs.php",
        "criteria": [
            {"field": "is_disabled", "op": "eq", "value": True, "weight": 3,
             "label": "Must have a disability", "hard": True},
            {"field": "annual_income", "op": "lte", "value": 250000, "weight": 2,
             "label": "Annual income ≤ ₹2.5 lakh", "hard": False},
        ],
    },

    # ─────────────────────────────────────────────────
    # SC / ST
    # ─────────────────────────────────────────────────
    {
        "id": "post_matric_sc",
        "name": "Post-Matric Scholarship for SC Students",
        "ministry": "Ministry of Social Justice & Empowerment",
        "description": "Financial assistance to SC students pursuing post-matriculation courses.",
        "apply_url": "https://scholarships.gov.in/",
        "criteria": [
            {"field": "category", "op": "in", "value": ["sc"], "weight": 3,
             "label": "Must be SC category", "hard": True},
            {"field": "occupation", "op": "in", "value": ["student"], "weight": 2,
             "label": "Must be a student", "hard": True},
            {"field": "annual_income", "op": "lte", "value": 250000, "weight": 2,
             "label": "Annual family income ≤ ₹2.5 lakh", "hard": False},
        ],
    },

    {
        "id": "eklavya_model_school",
        "name": "Eklavya Model Residential Schools",
        "ministry": "Ministry of Tribal Affairs",
        "description": "Quality education for ST students in tribal areas; free residential schooling.",
        "apply_url": "https://emrs.tribal.gov.in/",
        "criteria": [
            {"field": "category", "op": "in", "value": ["st"], "weight": 3,
             "label": "Must be ST category", "hard": True},
            {"field": "occupation", "op": "in", "value": ["student"], "weight": 2,
             "label": "Must be a school student", "hard": True},
            {"field": "age", "op": "range", "value": [6, 18], "weight": 1,
             "label": "Age 6–18 years (school age)", "hard": False},
        ],
    },

    # ─────────────────────────────────────────────────
    # SENIOR CITIZENS
    # ─────────────────────────────────────────────────
    {
        "id": "indira_gandhi_old_age",
        "name": "Indira Gandhi National Old Age Pension Scheme",
        "ministry": "Ministry of Rural Development",
        "description": "Monthly pension of ₹200–₹500 for BPL senior citizens aged 60+.",
        "apply_url": "https://nsap.nic.in/",
        "criteria": [
            {"field": "age", "op": "gte", "value": 60, "weight": 3,
             "label": "Age ≥ 60 years", "hard": True},
            {"field": "is_bpl", "op": "eq", "value": True, "weight": 3,
             "label": "Must be BPL household", "hard": True},
            {"field": "annual_income", "op": "lte", "value": 100000, "weight": 2,
             "label": "Annual income ≤ ₹1 lakh", "hard": False},
        ],
    },
]


# ---------------------------------------------------------------------------
# Criterion Evaluator
# ---------------------------------------------------------------------------

def _evaluate_criterion(profile: UserProfile, crit: dict) -> CriterionResult:
    field_name = crit["field"]
    op = crit["op"]
    required = crit["value"]
    weight = crit["weight"]
    label = crit["label"]
    is_hard = crit.get("hard", False)

    actual = getattr(profile, field_name, None)

    if op == "eq":
        matched = (actual == required)
    elif op == "lte":
        matched = (actual is not None and actual <= required)
    elif op == "gte":
        matched = (actual is not None and actual >= required)
    elif op == "in":
        matched = (actual in required)
    elif op == "not_in":
        matched = (actual not in required)
    elif op == "range":
        lo, hi = required
        matched = (actual is not None and lo <= actual <= hi)
    elif op == "any":
        matched = True
    else:
        matched = False

    return CriterionResult(
        label=label,
        field=field_name,
        matched=matched,
        weight=weight,
        is_hard=is_hard,
        actual_value=actual,
        required_value=required,
    )


# ---------------------------------------------------------------------------
# Core Recommendation Engine
# ---------------------------------------------------------------------------

class RecommendationService:

    def score_schemes(
        self,
        profile: UserProfile,
        top_n: int = 10,
        min_score_pct: float = 0.0,
    ) -> list[SchemeResult]:
        """
        Score all schemes against the profile and return top_n sorted by score_pct DESC.
        Hard-criteria failures set score_pct = 0 and mark is_disqualified = True.
        """
        results: list[SchemeResult] = []

        for scheme in SCHEME_REGISTRY:
            criteria_results: list[CriterionResult] = [
                _evaluate_criterion(profile, c) for c in scheme["criteria"]
            ]

            # Check hard disqualifiers first
            disqualified = any(r.is_hard and not r.matched for r in criteria_results)

            if disqualified:
                score_pct = 0.0
            else:
                total_weight = sum(r.weight for r in criteria_results)
                earned_weight = sum(r.weight for r in criteria_results if r.matched)
                score_pct = (earned_weight / total_weight * 100) if total_weight > 0 else 0.0

            matched = [r for r in criteria_results if r.matched]
            missed  = [r for r in criteria_results if not r.matched]

            results.append(SchemeResult(
                scheme_id=scheme["id"],
                name=scheme["name"],
                ministry=scheme["ministry"],
                description=scheme["description"],
                apply_url=scheme["apply_url"],
                score_pct=round(score_pct, 1),
                criteria_results=criteria_results,
                matched_criteria=matched,
                missed_criteria=missed,
                is_disqualified=disqualified,
            ))

        # Sort: non-disqualified first, then by score DESC
        results.sort(key=lambda r: (not r.is_disqualified, r.score_pct), reverse=True)

        # Filter minimum score and take top_n
        filtered = [r for r in results if r.score_pct >= min_score_pct]
        return filtered[:top_n]

    def profile_from_dict(self, data: dict) -> UserProfile:
        """Parse and validate incoming profile dict into a UserProfile."""
        return UserProfile(
            age=int(data.get("age", 0)),
            annual_income=float(data.get("annual_income", 0)),
            occupation=str(data.get("occupation", "other")).lower().strip(),
            gender=str(data.get("gender", "other")).lower().strip(),
            category=str(data.get("category", "general")).lower().strip(),
            state=str(data.get("state", "")).strip(),
            land_owned_acres=float(data.get("land_owned_acres", 0.0)),
            is_bpl=bool(data.get("is_bpl", False)),
            is_disabled=bool(data.get("is_disabled", False)),
            education=str(data.get("education", "none")).lower().strip(),
            marital_status=str(data.get("marital_status", "single")).lower().strip(),
        )

    def profile_summary(self, profile: UserProfile) -> dict:
        """Returns a human-readable summary of the profile for the frontend."""
        income_band = (
            "Below ₹1L" if profile.annual_income < 100000 else
            "₹1L–₹2.5L" if profile.annual_income < 250000 else
            "₹2.5L–₹5L" if profile.annual_income < 500000 else
            "₹5L–₹10L" if profile.annual_income < 1000000 else
            "Above ₹10L"
        )
        return {
            "age": profile.age,
            "income_band": income_band,
            "occupation": profile.occupation.replace("_", " ").title(),
            "gender": profile.gender.title(),
            "category": profile.category.upper(),
            "state": profile.state or "All India",
            "land_owned_acres": profile.land_owned_acres,
            "is_bpl": profile.is_bpl,
            "is_disabled": profile.is_disabled,
        }


# Singleton
recommendation_service = RecommendationService()
