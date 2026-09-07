from pydantic import BaseModel, Field
from typing import Optional


class OutcomeReport(BaseModel):
    """
    Schema for a REAL scheme-application outcome — e.g. reported by a
    partner NGO, a scheme administrator, or a long-running in-app
    "did you get approved?" follow-up. See PHASE3_NOTES.md for why no
    model is trained on this yet: this endpoint only collects and stores
    the data; nothing consumes it for prediction until there's enough
    real, verified outcome data to justify it.
    """
    scheme_id: str
    profile_snapshot: dict = Field(..., description="The applicant's profile at time of application")
    applied_at: Optional[str] = None
    outcome: str = Field(..., description="approved | rejected | pending | withdrawn")
    outcome_reported_at: Optional[str] = None
    source: str = Field(..., description="Who is reporting this — e.g. 'partner_ngo:xyz', 'user_self_report'")
    notes: str = ""
