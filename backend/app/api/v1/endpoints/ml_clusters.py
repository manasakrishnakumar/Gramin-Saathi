"""
User segmentation endpoints. Mounted live at /api/v1/ml/clusters/*.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from app.services.ml_cluster_service import ml_cluster_service

router = APIRouter()


class AssignRequest(BaseModel):
    age: int
    annual_income: float
    occupation: str
    gender: str
    category: str
    education: str = "none"
    land_owned_acres: float = 0.0
    is_bpl: bool = False
    is_disabled: bool = False


@router.get("/segments", summary="List all discovered user segments")
async def segments():
    return ml_cluster_service.segments()


@router.post("/assign", summary="Which segment does this profile belong to")
async def assign(request: AssignRequest):
    return ml_cluster_service.assign(request.model_dump())
