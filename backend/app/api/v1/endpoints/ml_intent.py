"""
Phase 1 endpoints — inspect/compare the trained intent classifier.

Not registered against the live app's api_router yet — see
backend/ml/README.md.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from app.services.ml_intent_classifier_service import ml_intent_classifier_service

router = APIRouter()


class ClassifyRequest(BaseModel):
    text: str


@router.post("/classify", summary="Classify with the trained model only")
async def classify_trained(request: ClassifyRequest):
    return ml_intent_classifier_service.classify(request.text)


@router.post("/compare", summary="Compare the trained classifier against the existing rule/LLM hybrid")
async def compare(request: ClassifyRequest):
    trained = ml_intent_classifier_service.classify(request.text)
    try:
        from app.services.intent_service import intent_service
        existing = intent_service.result_to_dict(intent_service.classify_fast(request.text))
    except Exception as e:
        existing = {"error": str(e)}
    return {"trained_model": trained, "existing_rule_based": existing}


@router.get("/status", summary="Is the trained model loaded, and what are its training metrics")
async def status():
    return {
        "ready": ml_intent_classifier_service.is_ready,
        "manifest": ml_intent_classifier_service.manifest(),
    }
