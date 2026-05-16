import asyncio
import json
import logging
from typing import Callable, Awaitable

import redis.asyncio as redis

from app.config import settings

logger = logging.getLogger(__name__)


class RedisSubscriber:
    """
    Subscribes to Redis channels and forwards messages
    to a provided async callback (e.g., WebSocket sender).
    """

    def __init__(self):
        self._redis = None
        self._pubsub = None
        self._running = False

    async def connect(self):
        try:
            # self._redis = redis.Redis(
            #     host=settings.REDIS_HOST,
            #     port=settings.REDIS_PORT,
            #     db=settings.REDIS_DB,
            #     decode_responses=True
            # )
            self._redis = redis.from_url(
                settings.REDIS_URL,
                decode_responses=True
            )

            await self._redis.ping()

            print("Connected to Redis successfully")
            self._pubsub = self._redis.pubsub()
            logger.info("RedisSubscriber connected")

        except Exception as e:
            logger.error(f"RedisSubscriber connection failed: {e}")
            raise

    async def subscribe(
        self,
        channel: str,
        message_handler: Callable[[dict], Awaitable[None]]
    ):
        """
        channel: Redis channel name
        message_handler: async function that handles decoded message
        """
        if not self._pubsub:
            raise RuntimeError("RedisSubscriber not connected")

        await self._pubsub.subscribe(channel)
        self._running = True

        logger.info(f"Subscribed to {channel}")

        try:
            while self._running:
                message = await self._pubsub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=1.0
                )

                if message:
                    try:
                        data = json.loads(message["data"])
                        await message_handler(data)
                    except Exception as e:
                        logger.error(f"Message handling failed: {e}")

                await asyncio.sleep(0.01)

        except asyncio.CancelledError:
            logger.info("RedisSubscriber cancelled")

        finally:
            await self.unsubscribe(channel)

    async def unsubscribe(self, channel: str):
        if self._pubsub:
            await self._pubsub.unsubscribe(channel)
        self._running = False

    async def close(self):
        self._running = False

        if self._pubsub:
            await self._pubsub.close()

        if self._redis:
            await self._redis.close()

        logger.info("RedisSubscriber closed")
