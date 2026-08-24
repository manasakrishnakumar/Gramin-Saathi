from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import logging
from app.services.scraper_service import scraper_service
from app.core.config import settings

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

def start_scheduler():
    # Parse cron expression "0 2 * * *" -> minute=0, hour=2
    # settings.SCRAPE_SCHEDULE defaults to "0 2 * * *"
    parts = settings.SCRAPE_SCHEDULE.split()
    minute, hour = parts[0], parts[1]
    
    scheduler.add_job(
        scraper_service.run_daily,
        CronTrigger(hour=hour, minute=minute),
        id="daily_scrape",
        replace_existing=True
    )
    
    scheduler.start()
    logger.info(f"Scheduler started. Next run at {hour}:{minute}")

def stop_scheduler():
    scheduler.shutdown()
