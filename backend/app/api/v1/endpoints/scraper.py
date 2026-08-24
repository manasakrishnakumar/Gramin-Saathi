from fastapi import APIRouter, BackgroundTasks
from app.services.scraper_service import scraper_service

router = APIRouter()

@router.post("/trigger")
async def trigger_scrape(background_tasks: BackgroundTasks):
    """Manually trigger the scraper."""
    background_tasks.add_task(scraper_service.run_daily)
    return {"message": "Scraper job started in background"}
