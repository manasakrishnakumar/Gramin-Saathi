from pydantic import BaseModel, Field
from typing import Any, Optional


class ProfileRequest(BaseModel):
    age: int = Field(..., ge=0, le=120, description="Age in years")
    annual_income: float = Field(..., ge=0, description="Annual household income in INR")
    occupation: str = Field(
        ...,
        description="One of: farmer, student, self_employed, salaried, daily_wage, unemployed, other"
    )
    gender: str = Field(..., description="male | female | transgender | other")
    category: str = Field(..., description="general | obc | sc | st")
    state: str = Field("", description="State name (optional, empty = all India)")
    land_owned_acres: float = Field(0.0, ge=0, description="Land owned in acres")
    is_bpl: bool = Field(False, description="Has BPL card / SECC listed")
    is_disabled: bool = Field(False, description="Person with disability")
    education: str = Field("none", description="none | primary | secondary | graduate | postgraduate")
    marital_status: str = Field("single", description="single | married | widowed | divorced")
    top_n: int = Field(10, ge=1, le=20, description="Number of top schemes to return")
    min_score_pct: float = Field(0.0, ge=0, le=100, description="Minimum match % to include")


class CriterionDetail(BaseModel):
    label: str
    field: str
    matched: bool
    weight: int
    is_hard: bool
    actual_value: Any
    required_value: Any


class SchemeRecommendation(BaseModel):
    scheme_id: str
    name: str
    ministry: str
    description: str
    apply_url: str
    score_pct: float
    is_disqualified: bool
    matched_criteria: list[CriterionDetail]
    missed_criteria: list[CriterionDetail]
    match_label: str          # "Excellent", "Good", "Partial", "Low", "Not Eligible"
    ml_engagement_score: Optional[float] = None  # trained ranker's predicted engagement (0-1); None if ranker unavailable


class ProfileSummary(BaseModel):
    age: int
    income_band: str
    occupation: str
    gender: str
    category: str
    state: str
    land_owned_acres: float
    is_bpl: bool
    is_disabled: bool


class RecommendationResponse(BaseModel):
    profile_summary: ProfileSummary
    total_eligible: int           # schemes with score_pct > 0
    recommendations: list[SchemeRecommendation]
    ranking_method: str = "rule_engine"  # "rule_engine" | "ml_reranked" — see backend/ml/README.md


class SchemeListItem(BaseModel):
    scheme_id: str
    name: str
    ministry: str
    description: str


class ProfileFieldsResponse(BaseModel):
    occupations: list[str]
    genders: list[str]
    categories: list[str]
    education_levels: list[str]
    marital_statuses: list[str]
