"""
ml_router.py — single aggregator for every ML endpoint (Phases 0-8).

Mounted live in app/api/v1/api.py:
    from app.api.v1.ml_router import ml_router
    api_router.include_router(ml_router)

(That two-line mount, plus a few narrowly-scoped wiring edits to
rag_service.py and the recommendation endpoint to actually use the
trained models on live traffic, are the only touches this whole ML
effort ever made to pre-existing files — see backend/ml/README.md for
the full list and reasoning.)
"""

from fastapi import APIRouter
from app.api.v1.endpoints import (
    ml_feedback, ml_intent, ml_rank, ml_outcomes, ml_forecast, ml_anomaly,
    ml_groundedness, ml_ner, ml_clusters, ml_bandit, ml_voice_quality,
)

ml_router = APIRouter(prefix="/ml", tags=["ml"])
ml_router.include_router(ml_feedback.router, prefix="/feedback")
ml_router.include_router(ml_intent.router, prefix="/intent")
ml_router.include_router(ml_rank.router, prefix="/rank")
ml_router.include_router(ml_outcomes.router, prefix="/outcomes")
ml_router.include_router(ml_forecast.router, prefix="/forecast")
ml_router.include_router(ml_anomaly.router, prefix="/anomaly")
ml_router.include_router(ml_groundedness.router, prefix="/groundedness")
ml_router.include_router(ml_ner.router, prefix="/ner")
ml_router.include_router(ml_clusters.router, prefix="/clusters")
ml_router.include_router(ml_bandit.router, prefix="/bandit")
ml_router.include_router(ml_voice_quality.router, prefix="/voice-quality")
