"""
Phase 3 endpoints.

/report and /count deal with REAL outcome data collection only (no
prediction). /predict-demo is a SEPARATE, SYNTHETIC-DATA-ONLY demo model —
see ml_outcome_predictor_service.py and ml/PHASE3_NOTES.md for why the two
are kept strictly apart. Every /predict-demo response carries a disclaimer
field that must not be stripped before display.

Mounted live at /api/v1/ml/outcomes/* via ml_router — see backend/ml/README.md.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.schemas.ml_outcome import OutcomeReport
from app.services.ml_outcome_service import ml_outcome_service
from app.services.ml_outcome_predictor_service import ml_outcome_predictor_service

router = APIRouter()


class PredictDemoRequest(BaseModel):
    profile: dict
    scheme_id: str
    rule_score_pct: float
    matched_count: int
    missed_count: int


@router.post("/report", summary="Report a real scheme-application outcome (approved/rejected/pending)")
async def report_outcome(request: OutcomeReport):
    try:
        ml_outcome_service.report_outcome(
            scheme_id=request.scheme_id,
            profile_snapshot=request.profile_snapshot,
            outcome=request.outcome,
            source=request.source,
            applied_at=request.applied_at,
            outcome_reported_at=request.outcome_reported_at,
            notes=request.notes,
        )
        return {"status": "logged"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/count", summary="How much real outcome data has been collected so far")
async def count():
    return ml_outcome_service.count()


@router.post(
    "/predict-demo",
    summary="SYNTHETIC DEMO: predicted approval likelihood (NOT real outcome data)",
)
async def predict_demo(request: PredictDemoRequest):
    """
    Returns a score from a model trained entirely on fabricated data — see
    ml_outcome_predictor_service.DISCLAIMER, always included in the
    response. This is a demonstration of the modeling technique, not a
    real prediction. Do not remove the disclaimer before showing this to
    a user.
    """
    result = ml_outcome_predictor_service.predict(
        profile=request.profile,
        scheme_result={
            "rule_score_pct": request.rule_score_pct,
            "matched_count": request.matched_count,
            "missed_count": request.missed_count,
        },
    )
    return {"scheme_id": request.scheme_id, **result}


@router.get("/predict-demo/status", summary="Is the SYNTHETIC demo model loaded, and its training info")
async def predict_demo_status():
    return {
        "ready": ml_outcome_predictor_service.is_ready,
        "manifest": ml_outcome_predictor_service.manifest(),
    }
