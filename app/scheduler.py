from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from app.database import SessionLocal
from app.services.recommendation_service import run_recommendations
import logging

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def recommendation_job():
    """Runs daily at 7:00 AM — analyzes history and sends ride recommendations."""
    db = SessionLocal()
    try:
        logger.info("Scheduler: Running ride recommendations...")
        results = run_recommendations(db)
        logger.info(f"Recommendations sent for {len(results)} passenger(s).")
    except Exception as e:
        logger.error(f"Recommendation job failed: {e}")
    finally:
        db.close()


def start_scheduler():
    scheduler.add_job(
        recommendation_job,
        trigger=CronTrigger(hour=7, minute=0),   # every day at 7:00 AM
        id="ride_recommendations",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler started — recommendations will run daily at 7:00 AM")


def stop_scheduler():
    scheduler.shutdown()
