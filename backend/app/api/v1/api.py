from fastapi import APIRouter
from app.api.v1.endpoints import rag, voice, monitor, scraper

api_router = APIRouter()
api_router.include_router(rag.router, prefix="/rag", tags=["rag"])
api_router.include_router(voice.router, prefix="/voice", tags=["voice"])
api_router.include_router(monitor.router, prefix="/monitor", tags=["monitor"])
api_router.include_router(scraper.router, prefix="/scraper", tags=["scraper"])
