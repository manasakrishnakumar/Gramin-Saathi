"""
Profile anomaly detection endpoints. Mounted live at /api/v1/ml/anomaly/*.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from app.services.ml_anomaly_service import ml_anomaly_service

router = APIRouter()


class AnomalyCheckRequest(BaseModel):
    age: int
    annual_income: float
    occupation: str
    gender: str
    category: str
    education: str = "none"
    land_owned_acres: float = 0.0
    is_bpl: bool = False
    is_disabled: bool = False


@router.post("/check-profile", summary="Flag whether a submitted profile looks statistically unusual")
async def check_profile(request: AnomalyCheckRequest):
    return ml_anomaly_service.check(request.model_dump())


@router.get("/status", summary="Is the anomaly detector loaded, and its training info")
async def status():
    return {
        "ready": ml_anomaly_service.is_ready,
        "manifest": ml_anomaly_service.manifest(),
    }
