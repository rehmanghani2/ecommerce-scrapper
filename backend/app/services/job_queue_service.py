"""Queue scraping jobs through Celery so API and browser runtimes stay separate."""


class JobQueueService:
    async def enqueue(self, job_id: str) -> str:
        from app.worker.tasks import execute_scrape_job

        result = execute_scrape_job.delay(job_id)
        return result.id

    async def close(self):
        # Celery owns its broker connection pool; there is no per-request
        # Redis client to close here.
        return None
