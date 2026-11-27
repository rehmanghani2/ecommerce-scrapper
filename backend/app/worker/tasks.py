"""Background tasks executed only by the dedicated browser worker."""
import asyncio
import socket

from celery.utils.log import get_task_logger
from fastapi import HTTPException

from app.models.database import get_db_context
from app.models.job import Job, JobStatus
from app.core.scraper_engine import ScraperEngine
from app.worker.celery_app import celery_app

logger = get_task_logger(__name__)


@celery_app.task(
    bind=True,
    name="scraper.execute_job",
    acks_late=True,
    reject_on_worker_lost=True,
)
def execute_scrape_job(self, job_pk: int):
    """Run one persisted crawl job using Playwright in this worker process."""
    return asyncio.run(_execute_scrape_job(job_pk, self.request.id))


async def _execute_scrape_job(job_pk: int, task_id: str):
    async with get_db_context() as db:
        job = await db.get(Job, job_pk)
        if not job:
            logger.warning("Skipping missing job database id=%s", job_pk)
            return {"status": "missing", "job_id": job_pk}
        if job.status == JobStatus.CANCELLED:
            return {"status": "cancelled", "job_id": job.job_id}

        job.celery_task_id = task_id
        job.worker_id = socket.gethostname()
        await db.commit()

        config = job.config or {}
        engine = ScraperEngine(
            db,
            job.id,
            job.url,
            max_depth=int(config.get("max_depth", 3)),
            max_pages=int(config.get("max_pages", 500)),
        )
        await engine.start()
        await db.refresh(job)
        return {"status": job.status.value, "job_id": job.job_id}


@celery_app.task(
    name="scraper.discover_website",
    acks_late=True,
    reject_on_worker_lost=True,
)
def discover_website_task(payload: dict):
    """Execute the bounded discovery browser workflow away from FastAPI Cloud."""
    from app.api.routes.scraper import _discover_website_local

    try:
        return asyncio.run(_discover_website_local(payload))
    except HTTPException as exc:
        return {
            "_worker_error": str(exc.detail),
            "_status_code": exc.status_code,
        }
    except Exception as exc:
        logger.exception("Remote discovery task failed")
        return {
            "_worker_error": str(exc)[:300],
            "_status_code": 502,
        }
