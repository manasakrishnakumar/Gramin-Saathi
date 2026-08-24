from fastapi import APIRouter, Depends
from typing import Dict, List, Any
from app.services.monitoring_service import monitoring_service

router = APIRouter()

@router.get("/stats")
async def get_stats() -> Dict[str, Any]:
    """Get dashboard stats for today."""
    return monitoring_service.get_todays_stats()

@router.get("/logs")
async def get_logs(limit: int = 20) -> List[Dict]:
    """Get recent query logs."""
    return monitoring_service.get_recent_queries(limit)
