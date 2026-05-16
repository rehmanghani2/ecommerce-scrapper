import asyncio
import logging

import redis.asyncio as redis

from app.config import settings
from app.core.scraper_engine import ScraperEngine
from app.services.job_service import JobService

# from app.db.session import async_session_maker
# from app.models.database import async_session_maker
from app.models.database import get_db_context

from app.services.job_service import JobService


logger = logging.getLogger(__name__)


class DistributedWorker:

    def __init__(self):
        self._redis = None
        self._running = True
        # self._job_service = JobService()

    async def connect(self):
        # self._redis = redis.Redis(
        #     host=settings.REDIS_HOST,
        #     port=settings.REDIS_PORT,
        #     db=settings.REDIS_DB,
        #     decode_responses=True
        # )
        # logger.info("DistributedWorker connected to Redis")
        self._redis = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True
        )

        await self._redis.ping()

    print("Connected to Redis successfully")

    async def start(self):
        logger.info("DistributedWorker started")
        await self.connect()

        while self._running:
            try:
                result = await self._redis.blpop(
                    "crawl:job_queue",
                    timeout=5
                )

                if not result:
                    continue

                _, job_id = result
                logger.info(f"Worker picked job {job_id}")

                await self._process_job(job_id)

            except Exception as e:
                logger.exception(f"Worker loop error: {e}")
                await asyncio.sleep(2)

    async def _process_job(self, job_id: str):

        async with get_db_context() as db:
            job_service = JobService(db)
            job = await job_service.get_job(job_id)

            if not job:
                logger.warning(f"Job {job_id} not found")
                return

            engine = ScraperEngine(
                job_id=job.job_id,
                start_url=job.url,
                max_depth=job.config.get("max_depth", 3),
                max_pages=job.config.get("max_pages", 500),
            )

            await engine.start()
        
        # try:
        #     job = await self._job_service.get_job(job_id)

        #     if not job:
        #         logger.warning(f"Job {job_id} not found")
        #         return

        #     engine = ScraperEngine(
        #         job_id=job.id,
        #         start_url=job.start_url,
        #         max_depth=job.max_depth,
        #         max_pages=job.max_pages
        #     )

        #     await engine.start()

        # except Exception as e:
        #     logger.exception(f"Job {job_id} failed: {e}")

    

    async def shutdown(self):
        logger.info("DistributedWorker shutting down")
        self._running = False
        if self._redis:
            await self._redis.close()


async def main():
    worker = DistributedWorker()

    # loop = asyncio.get_event_loop()

    # for sig in (signal.SIGINT, signal.SIGTERM):
    #     loop.add_signal_handler(
    #         sig,
    #         lambda: asyncio.create_task(worker.shutdown())
    #     )

    try:
        await worker.start()
    except KeyboardInterrupt:
        print("Worker shutting down...")
        await worker.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
