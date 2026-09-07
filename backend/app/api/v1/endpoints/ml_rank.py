"""
Phase 2 endpoints — preview the learned reranking without applying it.

Not registered against the live app's api_router yet — see
backend/ml/README.md. Deliberately named "preview": calling this never
changes what /recommend/schemes returns; it's read-only introspection so
the ranker's behavior can be inspected before ever wiring it in.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.ml_ranker_service import ml_ranker_service
from app.services.recommendation_service import recommendation_service

router = APIRouter()


class RankPreviewRequest(BaseModel):
    # Same shape as ProfileRequest in app/schemas/recommendation.py
    age: int
    annual_income: float
    occupation: str
    gender: str
    category: str
    state: str = ""
    land_owned_acres: float = 0.0
    is_bpl: bool = False
    is_disabled: bool = False
    education: str = "none"
    marital_status: str = "single"


@router.post("/preview", summary="Show rule-engine order vs. ML-reranked order, side by side")
async def preview(request: RankPreviewRequest):
    """
    Runs the existing, unmodified rule engine to get eligible schemes
    (identical to what /recommend/schemes returns), then shows what order
    the trained ranker WOULD produce if it were wired in — for comparison
    only, does not affect the live recommendation endpoint.
    """
    if not ml_ranker_service.is_ready:
        raise HTTPException(status_code=503, detail="Ranker model not trained yet — see backend/ml/README.md")

    profile = recommendation_service.profile_from_dict(request.model_dump())
    results = recommendation_service.score_schemes(profile, top_n=50, min_score_pct=0.0)
    eligible = [r for r in results if not r.is_disqualified and r.score_pct > 0]

    scored = []
    for r in eligible:
        ml_score = ml_ranker_service.score(
            profile=request.model_dump(),
            scheme_result={
                "rule_score_pct": r.score_pct,
                "matched_count": len(r.matched_criteria),
                "missed_count": len(r.missed_criteria),
            },
        )
        scored.append({
            "scheme_id": r.scheme_id,
            "name": r.name,
            "rule_score_pct": r.score_pct,
            "ml_engagement_score": ml_score,
        })

    rule_order = [s["scheme_id"] for s in scored]  # already sorted by rule engine
    ml_order = [s["scheme_id"] for s in sorted(scored, key=lambda s: s["ml_engagement_score"] or 0, reverse=True)]

    return {
        "schemes": scored,
        "rule_engine_order": rule_order,
        "ml_reranked_order": ml_order,
        "order_changed": rule_order != ml_order,
        "model_manifest": ml_ranker_service.manifest(),
    }
