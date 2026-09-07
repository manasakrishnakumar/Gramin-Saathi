"""
Voice transcription quality endpoints. Mounted live at /api/v1/ml/voice-quality/*.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from app.services.ml_voice_quality_service import ml_voice_quality_service

router = APIRouter()


class CheckRequest(BaseModel):
    transcript: str


@router.post("/check", summary="Flag whether a transcript looks like it may contain ASR errors")
async def check(request: CheckRequest):
    return ml_voice_quality_service.check(request.transcript)


@router.get("/status", summary="Is the voice quality classifier loaded, and its training info")
async def status():
    return {
        "ready": ml_voice_quality_service.is_ready,
        "manifest": ml_voice_quality_service.manifest(),
    }
