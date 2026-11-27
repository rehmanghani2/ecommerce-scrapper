"""Background tasks executed only by the dedicated browser worker."""
import asyncio
import socket

from celery.utils.log import get_task_logger
from fastapi import HTTPException

from app.models.database import get_db_context
from app.models.job import Job, JobStatus
from sqlalchemy import select
from app.core.scraper_engine import ScraperEngine
from app.worker.celery_app import celery_app

logger = get_task_logger(__name__)


@celery_app.task(
    bind=True,
    name="scraper.execute_job",
    acks_late=True,
    reject_on_worker_lost=True,
)
def execute_scrape_job(self, job_pk: int | str):
    """Run one persisted crawl job using Playwright in this worker process."""
    return asyncio.run(_execute_scrape_job(job_pk, self.request.id))


async def _execute_scrape_job(job_identifier: int | str, task_id: str):
    async with get_db_context() as db:
        if isinstance(job_identifier, int):
            job = await db.get(Job, job_identifier)
        else:
            result = await db.execute(select(Job).where(Job.job_id == str(job_identifier)))
            job = result.scalar_one_or_none()
        if not job:
            logger.warning("Skipping missing job identifier=%s", job_identifier)
            return {"status": "missing", "job_id": str(job_identifier)}
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



@celery_app.task(
    name="scraper.execute_bulk_job",
    acks_late=True,
    reject_on_worker_lost=True,
)
def execute_bulk_scrape_job(
    self,
    job_pk: int,
    urls: list,
    concurrency: int = 10,
    request_delay: float = 0.5,
    custom_selectors: dict | None = None,
):
    """Run bulk product extraction in the isolated browser worker."""
    from app.api.routes.scraper import run_bulk_scraper_job

    return asyncio.run(
        run_bulk_scraper_job(
            job_pk,
            urls,
            concurrency,
            request_delay,
            custom_selectors,
        )
    )
