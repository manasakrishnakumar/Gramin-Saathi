"""
Answer groundedness scoring endpoints. Mounted live at /api/v1/ml/groundedness/*.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from app.services.ml_groundedness_service import ml_groundedness_service

router = APIRouter()


class ScoreRequest(BaseModel):
    context: str
    answer: str


@router.post("/score", summary="Score whether an answer is supported by its context")
async def score(request: ScoreRequest):
    return ml_groundedness_service.score(request.context, request.answer)


@router.get("/status", summary="Is the groundedness classifier loaded, and its training info")
async def status():
    return {
        "ready": ml_groundedness_service.is_ready,
        "manifest": ml_groundedness_service.manifest(),
    }
