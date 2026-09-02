import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from ..scrapers.manager import scraper_manager

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

async def scheduled_scrape_job():
    logger.info("[Scheduler] Disparando rotina periódica de varredura de vagas...")
    try:
        result = await scraper_manager.run_all()
        logger.info(f"[Scheduler] Varredura periódica finalizada: {result.get('new_jobs_inserted', 0)} novas vagas salvas.")
    except Exception as e:
        logger.error(f"[Scheduler] Falha na execução periódica: {e}")

def start_scheduler(interval_hours: int = 3):
    if not scheduler.running:
        # Agendar para rodar a cada X horas
        scheduler.add_job(
            scheduled_scrape_job,
            trigger=IntervalTrigger(hours=interval_hours),
            id="job_scraper_routine",
            replace_existing=True
        )
        scheduler.start()
        logger.info(f"[Scheduler] Agendador iniciado! Varreduras automáticas a cada {interval_hours} horas.")

def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()
        logger.info("[Scheduler] Agendador desativado.")
