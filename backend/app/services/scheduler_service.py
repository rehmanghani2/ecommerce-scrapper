"""
Background scheduler service for executing recurring scraping jobs using cron expressions.
"""

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from urllib.parse import urlparse
from croniter import croniter

from sqlalchemy import select
from app.models.database import get_db_context
from app.models.schedule import ScheduledJob
from app.models.job import Job, JobStatus, JobType

logger = logging.getLogger(__name__)


def calculate_next_run(cron_expression: str, base_time: Optional[datetime] = None) -> datetime:
    """
    Calculate the next execution datetime from a cron expression.
    Defaults to UTC timezone.
    """
    if base_time is None:
        base_time = datetime.now(timezone.utc)
    elif base_time.tzinfo is None:
        base_time = base_time.replace(tzinfo=timezone.utc)
    
    # croniter calculates the next recurrence
    iter = croniter(cron_expression, base_time)
    next_ts = iter.get_next(datetime)
    if next_ts.tzinfo is None:
        next_ts = next_ts.replace(tzinfo=timezone.utc)
    return next_ts


class SchedulerService:
    """
    Async background worker that periodically polls active scheduled jobs
    and triggers scraper executions when next_run_at is reached.
    """

    def __init__(self, check_interval_seconds: int = 30):
        self.check_interval = check_interval_seconds
        self._task: Optional[asyncio.Task] = None
        self._is_running = False

    def start(self):
        """Start the background scheduler loop."""
        if self._is_running:
            logger.info("Scheduler service is already running.")
            return

        self._is_running = True
        self._task = asyncio.create_task(self._scheduler_loop())
        logger.info(f"Scheduled Scraper Service started (polling every {self.check_interval}s).")

    def stop(self):
        """Stop the background scheduler loop."""
        self._is_running = False
        if self._task and not self._task.done():
            self._task.cancel()
            logger.info("Scheduled Scraper Service stopped.")

    async def _scheduler_loop(self):
        """Main periodic loop."""
        # Initial wait to let app startup and DB initialization settle
        await asyncio.sleep(5)

        while self._is_running:
            try:
                await self._check_and_run_due_jobs()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in scheduler tick: {e}", exc_info=True)

            try:
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break

    async def _check_and_run_due_jobs(self):
        """Query DB for scheduled jobs that are active and due."""
        now = datetime.now(timezone.utc)

        async with get_db_context() as db:
            stmt = select(ScheduledJob).where(
                ScheduledJob.is_active == True,
                ScheduledJob.next_run_at <= now
            )
            result = await db.execute(stmt)
            due_schedules = result.scalars().all()

            for sched in due_schedules:
                logger.info(f"Triggering scheduled crawl: '{sched.name}' (ID: {sched.id}, URL: {sched.url})")
                asyncio.create_task(self.trigger_schedule(sched.id))

    async def trigger_schedule(self, schedule_id: int) -> Optional[int]:
        """
        Execute a scheduled job, create a corresponding Job in DB,
        update last_run_at & next_run_at, and dispatch the browser worker task.
        Returns the created Job's integer ID.
        """
        async with get_db_context() as db:
            sched = await db.get(ScheduledJob, schedule_id)
            if not sched:
                logger.warning(f"Scheduled job {schedule_id} not found.")
                return None

            now = datetime.now(timezone.utc)
            timestamp_str = int(time.time())
            unique_job_id = f"sched_{sched.id}_{timestamp_str}"
            domain = sched.domain or urlparse(sched.url).netloc

            # 1. Create a Job record
            cfg_dict = sched.config or {}
            job = Job(
                job_id=unique_job_id,
                name=f"[Scheduled] {sched.name}",
                description=f"Automated run triggered via schedule '{sched.name}' ({sched.cron_expression})",
                url=sched.url,
                domain=domain,
                job_type=JobType.FULL_SITE,
                status=JobStatus.QUEUED,
                config=cfg_dict,
                user_id=sched.user_id,
            )
            db.add(job)
            await db.commit()
            await db.refresh(job)

            # 2. Update schedule tracking
            sched.last_run_at = now
            sched.last_job_id = job.id
            sched.total_runs = (sched.total_runs or 0) + 1
            try:
                sched.next_run_at = calculate_next_run(sched.cron_expression, now)
            except Exception as cron_err:
                logger.error(f"Failed to calculate next_run for schedule {sched.id}: {cron_err}")

            await db.commit()
            created_job_id = job.id

        # 3. Dispatch through the same independent Playwright worker queue.
        try:
            from app.worker.tasks import execute_scrape_job
            queued_task = execute_scrape_job.delay(created_job_id)
            async with get_db_context() as update_db:
                queued_job = await update_db.get(Job, created_job_id)
                if queued_job:
                    queued_job.celery_task_id = queued_task.id
                    await update_db.commit()
            logger.info(
                "Queued scheduled crawl '%s' on browser worker; Job ID: %s",
                sched.name,
                created_job_id,
            )
        except Exception as dispatch_error:
            async with get_db_context() as update_db:
                queued_job = await update_db.get(Job, created_job_id)
                if queued_job:
                    queued_job.status = JobStatus.FAILED
                    queued_job.error_message = f"Could not enqueue scheduled crawl: {dispatch_error}"
                    await update_db.commit()
            logger.exception("Failed to enqueue scheduled crawl %s", created_job_id)
        return created_job_id


# Global scheduler singleton
scheduler_service = SchedulerService()
