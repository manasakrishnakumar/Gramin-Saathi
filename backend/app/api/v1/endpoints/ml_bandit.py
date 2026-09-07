"""
Contextual bandit endpoints. Mounted live at /api/v1/ml/bandit/*.

Unlike the other endpoints in this pass, /update here is meant to be
called repeatedly over time with real reward signals as they arrive
(e.g. from the recommendation feedback flow) — the bandit updates
in-process and persists its state after every call, no retrain step.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from app.services.ml_bandit_service import ml_bandit_service

router = APIRouter()


class PreviewRequest(BaseModel):
    profile: dict
    candidate_scheme_ids: list[str]


class UpdateRequest(BaseModel):
    profile: dict
    scheme_id: str
    reward: float  # 1.0 = positive engagement, 0.0 = not


@router.post("/preview", summary="What would the bandit currently choose among these eligible schemes")
async def preview(request: PreviewRequest):
    return ml_bandit_service.preview(request.profile, request.candidate_scheme_ids)


@router.post("/update", summary="Feed a real reward signal — the bandit learns from this immediately")
async def update(request: UpdateRequest):
    return ml_bandit_service.update(request.profile, request.scheme_id, request.reward)


@router.get("/status", summary="Is the bandit loaded, and its simulation-convergence info")
async def status():
    return {
        "ready": ml_bandit_service.is_ready,
        "manifest": ml_bandit_service.manifest(),
    }
