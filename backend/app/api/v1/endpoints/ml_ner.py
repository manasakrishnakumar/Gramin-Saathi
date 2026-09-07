"""
Scheme-data NER endpoints. Mounted live at /api/v1/ml/ner/*.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from app.services.ml_ner_service import ml_ner_service

router = APIRouter()


class ExtractRequest(BaseModel):
    text: str


@router.post("/extract", summary="Extract SCHEME/MINISTRY/AMOUNT/AGE/PCT entities from free text")
async def extract(request: ExtractRequest):
    """
    Meant for newly scraped scheme documents (scraper_service.py) — pulls
    structured facts back out of free text to reduce how much of
    SCHEME_REGISTRY needs hand-transcription. Known limitation: multi-word
    ministry names containing "and" can truncate (e.g. "Ministry of
    Commerce and Industry" -> "Ministry of Commerce") — see ml/README.md.
    """
    return ml_ner_service.extract(request.text)


@router.get("/status", summary="Is the NER model loaded, and its training info")
async def status():
    return {
        "ready": ml_ner_service.is_ready,
        "manifest": ml_ner_service.manifest(),
    }
