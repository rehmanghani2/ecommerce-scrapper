import redis.asyncio as redis
from app.config import settings


class JobQueueService:

    def __init__(self):
        self._redis = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            decode_responses=True
        )

    async def enqueue(self, job_id: str):
        await self._redis.rpush("crawl:job_queue", job_id)

    async def close(self):
        await self._redis.close()
