"""
Phase 0 endpoints — event/feedback collection.

Not registered against the live app's api_router yet (see
backend/ml/README.md for the one-line diff that would do so). Standalone
and fully functional on its own: mount ml_router (app/api/v1/ml_router.py)
whenever you're ready to activate it.
"""

from fastapi import APIRouter, HTTPException
from app.schemas.ml_feedback import (
    ChatFeedbackRequest,
    RecommendationActionRequest,
    FeedbackStatsResponse,
)
from app.services.ml_feedback_service import ml_feedback_service

router = APIRouter()


@router.post("/chat", summary="Log thumbs up/down on a chat answer")
async def log_chat_feedback(request: ChatFeedbackRequest):
    try:
        ml_feedback_service.log_chat_feedback(
            query=request.query,
            answer_snippet=request.answer_snippet,
            helpful=request.helpful,
            source=request.source,
            language=request.language,
        )
        return {"status": "logged"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recommendation", summary="Log a user action on a recommended scheme")
async def log_recommendation_action(request: RecommendationActionRequest):
    valid_actions = {"viewed", "clicked_apply", "checked_eligibility", "dismissed"}
    if request.action not in valid_actions:
        raise HTTPException(status_code=400, detail=f"action must be one of {sorted(valid_actions)}")
    try:
        ml_feedback_service.log_recommendation_action(
            scheme_id=request.scheme_id,
            action=request.action,
            profile=request.profile,
            rule_score_pct=request.rule_score_pct,
            matched_count=request.matched_count,
            missed_count=request.missed_count,
            is_disqualified=request.is_disqualified,
        )
        return {"status": "logged"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=FeedbackStatsResponse, summary="Feedback volume so far")
async def feedback_stats():
    return ml_feedback_service.get_stats()
