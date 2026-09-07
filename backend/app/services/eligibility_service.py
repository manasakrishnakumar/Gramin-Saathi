"""
eligibility_service.py
Deterministic Eligibility Prediction Engine.

Distinct from recommendation_service (which RANKS schemes across a profile).
This service does a DEEP analysis of ONE scheme for ONE user:
  - Hard pass/fail verdict per criterion
  - Blocking reasons (hard failures that disqualify)
  - Soft gaps (non-hard failures that reduce score)
  - Actionable fix suggestions per failed criterion
  - Documents required to apply
  - Next steps ordered by priority
  - What-if gap analysis ("change X to qualify")

No ML/XGBoost. Government rules are deterministic — this is pure rule evaluation.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from app.services.recommendation_service import (
    SCHEME_REGISTRY,
    UserProfile,
    CriterionResult,
    _evaluate_criterion,
)


# ---------------------------------------------------------------------------
# Extended scheme metadata: documents + fix suggestions per criterion
# ---------------------------------------------------------------------------
#
# CRITERION_EXTRAS maps  scheme_id → list of per-criterion extras.
# Each entry aligns by index with the scheme's criteria list.
# Provides:
#   documents : documents needed specifically for this criterion
#   fix       : actionable fix suggestion if criterion fails
#

CRITERION_EXTRAS: dict[str, list[dict]] = {

    "pm_kisan": [
        {
            "documents": ["Aadhaar card", "Land records (Khatauni/7-12 extract)"],
            "fix": "Register as a farmer with your local agricultural department.",
        },
        {
            "documents": ["Land record showing acreage"],
            "fix": "This scheme targets small/marginal farmers (≤5 acres). If you own more, consider if land is split across family members.",
        },
        {
            "documents": ["Income certificate from tehsildar"],
            "fix": "Reduce assessable income or apply for an income certificate reflecting actual farm income.",
        },
        {
            "documents": ["Aadhaar card (age proof)"],
            "fix": "Applicant must be 18 or older.",
        },
    ],

    "pm_fasal_bima": [
        {
            "documents": ["Farmer registration / Kisan ID", "Aadhaar"],
            "fix": "Register as a farmer with your state agriculture department.",
        },
        {
            "documents": ["Land record or lease agreement"],
            "fix": "Get a lease agreement from the landowner to show cultivable land access.",
        },
        {
            "documents": ["Aadhaar card"],
            "fix": "Must be 18+.",
        },
    ],

    "kisan_credit_card": [
        {
            "documents": ["Kisan ID / Farmer registration", "Aadhaar"],
            "fix": "Register as a farmer to apply for KCC.",
        },
        {
            "documents": ["Aadhaar (age proof)"],
            "fix": "Applicant must be aged 18–75.",
        },
        {
            "documents": ["Land records showing ≥0.5 acres"],
            "fix": "You need at least 0.5 acres of cultivable land. A lease agreement can substitute.",
        },
    ],

    "pm_matru_vandana": [
        {
            "documents": ["Aadhaar card", "MCP card (Mother & Child Protection card)"],
            "fix": "Scheme is only for women. Male applicants are not eligible.",
        },
        {
            "documents": ["Birth certificate / Aadhaar showing age ≥ 19"],
            "fix": "Must be at least 19 years old.",
        },
        {
            "documents": ["Income certificate"],
            "fix": "Annual household income should be ≤ ₹8 lakh.",
        },
    ],

    "mahila_shakti_kendra": [
        {
            "documents": ["Aadhaar card"],
            "fix": "Scheme is exclusively for women.",
        },
        {
            "documents": ["Income certificate"],
            "fix": "Reduce annual income or apply through local Anganwadi/ICDS centre for verification.",
        },
    ],

    "national_scholarship_portal": [
        {
            "documents": ["School/college enrollment certificate", "Aadhaar"],
            "fix": "Must be an enrolled student. Obtain enrollment certificate from institution.",
        },
        {
            "documents": ["Date of birth certificate / Aadhaar"],
            "fix": "Age must be between 14 and 30 years.",
        },
        {
            "documents": ["Caste/community certificate from competent authority"],
            "fix": "Obtain SC/ST/OBC certificate from your district's Tehsildar or SDM office.",
        },
        {
            "documents": ["Income certificate (family income ≤ ₹2.5 lakh)"],
            "fix": "Apply for income certificate from tehsildar; ensure it reflects actual family income.",
        },
    ],

    "pm_scholarship_scheme": [
        {
            "documents": ["Enrollment certificate from institution", "Aadhaar"],
            "fix": "Must be an enrolled student in a technical/professional course.",
        },
        {
            "documents": ["Date of birth proof"],
            "fix": "Applicant must be aged 18–25.",
        },
        {
            "documents": ["Family income certificate"],
            "fix": "Family income must be ≤ ₹6 lakh. Get income certificate from tehsildar.",
        },
    ],

    "ayushman_bharat": [
        {
            "documents": ["BPL card", "SECC-2011 list verification", "Aadhaar"],
            "fix": "Apply for a BPL card at your gram panchayat or municipal office. Also check SECC-2011 list at pmjay.gov.in.",
        },
        {
            "documents": ["Income certificate"],
            "fix": "Annual household income should be ≤ ₹1 lakh.",
        },
    ],

    "pm_suraksha_bima": [
        {
            "documents": ["Aadhaar", "Bank account (savings)"],
            "fix": "Must be aged 18–70. This is determined by Aadhaar records.",
        },
        {
            "documents": ["Bank statement"],
            "fix": "Scheme targets people with income ≤ ₹5 lakh/year.",
        },
    ],

    "pm_jeevan_jyoti": [
        {
            "documents": ["Aadhaar", "Savings bank account"],
            "fix": "Must be aged 18–50. Policy must be renewed each year before age 50.",
        },
        {
            "documents": ["Bank statement"],
            "fix": "Scheme targets lower-income individuals (≤ ₹5 lakh/year).",
        },
    ],

    "pm_awas_yojana_gramin": [
        {
            "documents": ["BPL card", "SECC-2011 enrollment", "Aadhaar"],
            "fix": "Get BPL card from gram panchayat. Check SECC-2011 inclusion list at pmayg.nic.in.",
        },
        {
            "documents": ["Land records"],
            "fix": "Landholding should be ≤ 2.5 acres for rural classification.",
        },
        {
            "documents": ["Income certificate from tehsildar"],
            "fix": "Annual family income must be ≤ ₹3 lakh.",
        },
        {
            "documents": ["Aadhaar (age proof)"],
            "fix": "Head of household must be 18+.",
        },
    ],

    "mgnregs": [
        {
            "documents": ["Aadhaar", "Residence proof (voter ID / ration card)"],
            "fix": "Applicant must be 18 or older.",
        },
        {
            "documents": ["Job Card application form"],
            "fix": "Apply for a MGNREGS Job Card at your gram panchayat.",
        },
        {
            "documents": ["Income certificate"],
            "fix": "Scheme targets rural households with income ≤ ₹2 lakh.",
        },
    ],

    "pm_mudra_yojana": [
        {
            "documents": ["Business registration / GST certificate / shop license", "Aadhaar", "Bank statement"],
            "fix": "Must be self-employed or running a micro/small business. Register your business with municipal authority.",
        },
        {
            "documents": ["Aadhaar (age proof)"],
            "fix": "Applicant must be aged 18–65.",
        },
        {
            "documents": ["Business financial statement / income proof"],
            "fix": "Business income ≤ ₹10 lakh qualifies for MUDRA loans.",
        },
    ],

    "startup_india_seed_fund": [
        {
            "documents": ["DPIIT recognition certificate", "Pitch deck", "Business plan"],
            "fix": "Register your startup with DPIIT at startupindia.gov.in to get DPIIT recognition first.",
        },
        {
            "documents": ["Aadhaar / passport"],
            "fix": "Founder must be aged 18–50.",
        },
    ],

    "deen_dayal_disability": [
        {
            "documents": ["Disability certificate from medical board (UDID card)", "Aadhaar"],
            "fix": "Obtain UDID (Unique Disability ID) card from swavlambancard.gov.in or district medical board.",
        },
        {
            "documents": ["Income certificate"],
            "fix": "Annual income must be ≤ ₹2.5 lakh. Apply for income certificate from tehsildar.",
        },
    ],

    "post_matric_sc": [
        {
            "documents": ["SC caste certificate from competent authority", "Aadhaar"],
            "fix": "Obtain SC caste certificate from district Tehsildar / SDM office.",
        },
        {
            "documents": ["College/school enrollment certificate"],
            "fix": "Must be enrolled as a student. Get enrollment proof from institution.",
        },
        {
            "documents": ["Family income certificate (≤ ₹2.5 lakh)"],
            "fix": "Get income certificate from tehsildar. Ensure it reflects household income.",
        },
    ],

    "eklavya_model_school": [
        {
            "documents": ["ST caste certificate from competent authority", "Aadhaar"],
            "fix": "Obtain ST caste certificate from district authority.",
        },
        {
            "documents": ["School enrollment certificate"],
            "fix": "Must be an enrolled school student.",
        },
        {
            "documents": ["Birth certificate / Aadhaar"],
            "fix": "Residential school admission is for ages 6–18.",
        },
    ],

    "indira_gandhi_old_age": [
        {
            "documents": ["Age proof (Aadhaar showing age ≥ 60)"],
            "fix": "Applicant must be 60 years or older.",
        },
        {
            "documents": ["BPL card", "SECC-2011 enrollment"],
            "fix": "Must be in BPL household. Apply for BPL card at gram panchayat.",
        },
        {
            "documents": ["Income certificate"],
            "fix": "Annual income should be ≤ ₹1 lakh.",
        },
    ],
}


# Common documents every applicant needs regardless of scheme
UNIVERSAL_DOCUMENTS = [
    "Aadhaar card (mandatory for all government schemes)",
    "Bank account linked with Aadhaar (for DBT transfers)",
    "Passport-size photograph",
]


# ---------------------------------------------------------------------------
# Eligibility Result types
# ---------------------------------------------------------------------------

@dataclass
class CriterionEligibility:
    label: str
    field: str
    matched: bool
    weight: int
    is_hard: bool
    actual_value: Any
    required_value: Any
    fix_suggestion: str         # "what to do if this fails"
    documents_for_criterion: list[str]  # docs specifically for this criterion


@dataclass
class EligibilityVerdict:
    verdict: str            # "Fully Eligible" | "Conditionally Eligible" | "Not Eligible"
    eligibility_pct: float  # 0–100 (only meaningful if not hard-blocked)
    confidence: str         # "High" (all hard pass) | "Medium" | "Low"
    is_eligible: bool       # True if no hard blocker
    blocking_criteria: list[CriterionEligibility]   # hard criteria that FAILED
    soft_gaps: list[CriterionEligibility]            # non-hard criteria that failed
    passed_criteria: list[CriterionEligibility]      # all criteria that passed
    all_criteria: list[CriterionEligibility]         # full list
    documents_required: list[str]       # full consolidated doc list
    next_steps: list[str]               # ordered action steps
    what_if_suggestions: list[str]      # "If you do X, you could qualify"
    scheme_id: str
    scheme_name: str
    ministry: str
    description: str
    apply_url: str


# ---------------------------------------------------------------------------
# Core Eligibility Service
# ---------------------------------------------------------------------------

class EligibilityService:

    def _get_scheme(self, scheme_id: str) -> dict | None:
        for s in SCHEME_REGISTRY:
            if s["id"] == scheme_id:
                return s
        return None

    def _build_criterion_eligibility(
        self,
        result: CriterionResult,
        extras: dict,
    ) -> CriterionEligibility:
        return CriterionEligibility(
            label=result.label,
            field=result.field,
            matched=result.matched,
            weight=result.weight,
            is_hard=result.is_hard,
            actual_value=result.actual_value,
            required_value=result.required_value,
            fix_suggestion=extras.get("fix", "Contact your local government office for guidance."),
            documents_for_criterion=extras.get("documents", []),
        )

    def predict(self, profile: UserProfile, scheme_id: str) -> EligibilityVerdict | None:
        """
        Deep eligibility analysis for ONE scheme + ONE profile.
        Returns None if scheme_id not found.
        """
        scheme = self._get_scheme(scheme_id)
        if not scheme:
            return None

        criteria = scheme["criteria"]
        extras_list = CRITERION_EXTRAS.get(scheme_id, [{}] * len(criteria))

        # Evaluate each criterion
        raw_results = [_evaluate_criterion(profile, c) for c in criteria]

        # Build enriched eligibility objects
        enriched: list[CriterionEligibility] = []
        for i, result in enumerate(raw_results):
            extras = extras_list[i] if i < len(extras_list) else {}
            enriched.append(self._build_criterion_eligibility(result, extras))

        # Categorise
        blocking  = [e for e in enriched if e.is_hard and not e.matched]
        soft_gaps = [e for e in enriched if not e.is_hard and not e.matched]
        passed    = [e for e in enriched if e.matched]

        # Verdict
        is_eligible = len(blocking) == 0
        total_weight = sum(e.weight for e in enriched)
        earned = sum(e.weight for e in enriched if e.matched)
        eligibility_pct = round(earned / total_weight * 100, 1) if total_weight > 0 else 0.0

        if not is_eligible:
            verdict = "Not Eligible"
            confidence = "High"   # deterministic — hard rule failed
        elif len(soft_gaps) == 0:
            verdict = "Fully Eligible"
            confidence = "High"
        elif eligibility_pct >= 70:
            verdict = "Conditionally Eligible"
            confidence = "High"
        else:
            verdict = "Partially Eligible"
            confidence = "Medium"

        # Documents — consolidate from all failed criterion + universal
        docs: list[str] = list(UNIVERSAL_DOCUMENTS)
        for e in enriched:
            for d in e.documents_for_criterion:
                if d not in docs:
                    docs.append(d)

        # Next steps
        next_steps = self._build_next_steps(
            scheme, blocking, soft_gaps, is_eligible, scheme_id
        )

        # What-if
        what_if = self._build_what_if(blocking, soft_gaps)

        return EligibilityVerdict(
            verdict=verdict,
            eligibility_pct=eligibility_pct,
            confidence=confidence,
            is_eligible=is_eligible,
            blocking_criteria=blocking,
            soft_gaps=soft_gaps,
            passed_criteria=passed,
            all_criteria=enriched,
            documents_required=docs,
            next_steps=next_steps,
            what_if_suggestions=what_if,
            scheme_id=scheme_id,
            scheme_name=scheme["name"],
            ministry=scheme["ministry"],
            description=scheme["description"],
            apply_url=scheme["apply_url"],
        )

    def _build_next_steps(
        self,
        scheme: dict,
        blocking: list[CriterionEligibility],
        soft_gaps: list[CriterionEligibility],
        is_eligible: bool,
        scheme_id: str,
    ) -> list[str]:
        steps: list[str] = []

        if not is_eligible:
            steps.append("⚠️  You are currently NOT eligible due to hard requirement failures.")
            for b in blocking:
                steps.append(f"Fix: {b.fix_suggestion}")
            steps.append("After resolving blocking issues, re-check eligibility.")
            return steps

        # Eligible path
        steps.append(f"✅ You qualify for {scheme['name']}! Follow these steps to apply:")
        steps.append("1. Gather all required documents listed below.")
        steps.append("2. Link your Aadhaar to your bank account (mandatory for DBT).")

        if scheme_id in ("pm_kisan", "pm_fasal_bima", "kisan_credit_card"):
            steps.append("3. Visit your nearest Common Service Centre (CSC) or bank branch.")
            steps.append("4. Submit online at the official portal with documents.")
        elif scheme_id in ("ayushman_bharat", "pm_awas_yojana_gramin", "mgnregs"):
            steps.append("3. Visit your Gram Panchayat office to initiate the application.")
            steps.append("4. Verify your name on the beneficiary list (SECC-2011 / PMAY list).")
        elif scheme_id in ("national_scholarship_portal", "post_matric_sc", "eklavya_model_school"):
            steps.append("3. Register at scholarships.gov.in / NSP portal.")
            steps.append("4. Fill the application before the academic year deadline (usually Oct–Nov).")
        elif scheme_id in ("pm_suraksha_bima", "pm_jeevan_jyoti"):
            steps.append("3. Visit your savings bank branch and fill the enrollment form.")
            steps.append("4. Auto-debit of premium will be set up from your account.")
        else:
            steps.append("3. Visit the official scheme portal and register.")
            steps.append("4. Fill the application form with all supporting documents.")

        if soft_gaps:
            steps.append("5. Note: Some soft criteria are not fully met — your application may be de-prioritised.")
            for g in soft_gaps:
                steps.append(f"   → Improve: {g.fix_suggestion}")

        steps.append(f"Apply at: {scheme['apply_url']}")
        return steps

    def _build_what_if(
        self,
        blocking: list[CriterionEligibility],
        soft_gaps: list[CriterionEligibility],
    ) -> list[str]:
        suggestions: list[str] = []

        for b in blocking:
            suggestions.append(
                f"If you satisfy '{b.label}': this blocking criterion will be resolved, "
                f"potentially making you eligible. → {b.fix_suggestion}"
            )

        for g in soft_gaps:
            suggestions.append(
                f"If you satisfy '{g.label}': your eligibility score will increase by {g.weight} weight point(s). "
                f"→ {g.fix_suggestion}"
            )

        if not suggestions:
            suggestions.append("All criteria are met. No changes needed.")

        return suggestions

    def check_all(
        self, profile: UserProfile
    ) -> list[EligibilityVerdict]:
        """Run eligibility check for all schemes. Used for bulk comparison."""
        verdicts = []
        for scheme in SCHEME_REGISTRY:
            v = self.predict(profile, scheme["id"])
            if v:
                verdicts.append(v)
        verdicts.sort(
            key=lambda v: (v.is_eligible, v.eligibility_pct),
            reverse=True,
        )
        return verdicts


# Singleton
eligibility_service = EligibilityService()
