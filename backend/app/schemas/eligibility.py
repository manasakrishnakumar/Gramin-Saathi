from pydantic import BaseModel, Field
from typing import Any, Optional


class CriterionEligibilityDetail(BaseModel):
    label: str
    field: str
    matched: bool
    weight: int
    is_hard: bool
    actual_value: Any
    required_value: Any
    fix_suggestion: str
    documents_for_criterion: list[str]


class EligibilityRequest(BaseModel):
    # Profile fields
    age: int = Field(..., ge=0, le=120)
    annual_income: float = Field(..., ge=0)
    occupation: str
    gender: str
    category: str
    state: str = ""
    land_owned_acres: float = 0.0
    is_bpl: bool = False
    is_disabled: bool = False
    education: str = "none"
    marital_status: str = "single"
    # Target scheme
    scheme_id: str = Field(..., description="Scheme ID to check eligibility for")


class BulkEligibilityRequest(BaseModel):
    """Check eligibility for all schemes at once."""
    age: int = Field(..., ge=0, le=120)
    annual_income: float = Field(..., ge=0)
    occupation: str
    gender: str
    category: str
    state: str = ""
    land_owned_acres: float = 0.0
    is_bpl: bool = False
    is_disabled: bool = False
    education: str = "none"
    marital_status: str = "single"


class EligibilityResponse(BaseModel):
    scheme_id: str
    scheme_name: str
    ministry: str
    description: str
    apply_url: str
    verdict: str                    # Fully Eligible | Conditionally Eligible | Partially Eligible | Not Eligible
    eligibility_pct: float          # 0–100
    confidence: str                 # High | Medium | Low
    is_eligible: bool
    blocking_criteria: list[CriterionEligibilityDetail]   # hard fails → disqualifiers
    soft_gaps: list[CriterionEligibilityDetail]           # non-hard fails
    passed_criteria: list[CriterionEligibilityDetail]     # all passed
    documents_required: list[str]
    next_steps: list[str]
    what_if_suggestions: list[str]


class BulkEligibilityItem(BaseModel):
    """Compact summary for bulk check results."""
    scheme_id: str
    scheme_name: str
    verdict: str
    eligibility_pct: float
    is_eligible: bool
    blocking_count: int
    soft_gap_count: int


class BulkEligibilityResponse(BaseModel):
    total_eligible: int
    total_not_eligible: int
    results: list[BulkEligibilityItem]
