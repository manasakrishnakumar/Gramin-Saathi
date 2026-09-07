"""
Query volume forecast endpoints. Mounted live at /api/v1/ml/forecast/*.
"""

from fastapi import APIRouter
from app.services.ml_forecast_service import ml_forecast_service

router = APIRouter()


@router.get("/next-24h", summary="Predicted query volume for the next 24 hours")
async def next_24h():
    return ml_forecast_service.forecast_next_24h()


@router.get("/status", summary="Is the forecast model loaded, real or synthetic data, training metrics")
async def status():
    return {
        "ready": ml_forecast_service.is_ready,
        "manifest": ml_forecast_service.manifest(),
    }
