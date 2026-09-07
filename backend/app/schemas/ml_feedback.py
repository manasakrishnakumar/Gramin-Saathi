from pydantic import BaseModel, Field
from typing import Optional


class ChatFeedbackRequest(BaseModel):
    query: str
    answer_snippet: str = Field("", description="First ~500 chars of the answer being rated")
    helpful: bool
    source: str = ""
    language: str = "English"


class RecommendationActionRequest(BaseModel):
    scheme_id: str
    action: str = Field(..., description="viewed | clicked_apply | checked_eligibility | dismissed")
    profile: dict
    rule_score_pct: float
    matched_count: int
    missed_count: int
    is_disqualified: bool = False


class FeedbackStatsResponse(BaseModel):
    chat_feedback_total: int
    chat_feedback_helpful: int
    chat_helpful_rate: Optional[float]
    recommendation_actions: dict[str, int]
    total_recommendation_events: int
