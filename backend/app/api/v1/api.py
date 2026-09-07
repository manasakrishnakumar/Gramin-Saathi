from fastapi import APIRouter
from app.api.v1.endpoints import rag, voice, monitor, scraper, recommendation, eligibility, intent
from app.api.v1.ml_router import ml_router

api_router = APIRouter()
api_router.include_router(rag.router, prefix="/rag", tags=["rag"])
api_router.include_router(voice.router, prefix="/voice", tags=["voice"])
api_router.include_router(monitor.router, prefix="/monitor", tags=["monitor"])
api_router.include_router(scraper.router, prefix="/scraper", tags=["scraper"])
api_router.include_router(recommendation.router, prefix="/recommend", tags=["recommendation"])
api_router.include_router(eligibility.router, prefix="/eligibility", tags=["eligibility"])
api_router.include_router(intent.router, prefix="/intent", tags=["intent"])
api_router.include_router(ml_router)  # /ml/feedback, /ml/intent, /ml/rank, /ml/outcomes — see backend/ml/README.md

