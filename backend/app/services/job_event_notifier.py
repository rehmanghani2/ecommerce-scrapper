"""
job_event_notifier.py
---------------------
Reliable Redis-backed job event publisher for WebSocket updates.

Purpose:
- Eliminate Redis connection instability
- Prevent WebSocket crashes when Redis disconnects
- Provide safe publish with auto-reconnect

This module is infrastructure-level and MUST NOT crash the crawler.
"""

import asyncio
import json
from typing import Any, Dict, Optional

import redis.asyncio as redis

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class JobEventNotifier:
    """
    Redis-based event publisher for job progress updates.
    Safe, reconnectable, and non-blocking.
    """

    def __init__(self):
        self._redis: Optional[redis.Redis] = None
        self._lock = asyncio.Lock()
        self._connected = False

    async def connect(self):
        """
        Establish Redis connection safely.
        """
        async with self._lock:
            if self._connected:
                return

            try:
                self._redis = redis.Redis(
                    host=settings.REDIS_HOST,
                    port=settings.REDIS_PORT,
                    db=settings.REDIS_DB,
                    decode_responses=True,
                )

                await self._redis.ping()
                self._connected = True
                logger.info("Redis connection established")

            except Exception as exc:
                self._connected = False
                logger.warning(f"Redis connection failed: {exc}")

    async def publish(self, channel: str, message: Dict[str, Any]):
        """
        Publish message safely.
        Never raises exception upward.
        """
        if not self._connected:
            await self.connect()

        if not self._connected:
            return

        try:
            payload = json.dumps(message)
            await self._redis.publish(channel, payload)
        except Exception as exc:
            logger.warning(f"Redis publish failed: {exc}")
            self._connected = False

    async def close(self):
        """
        Gracefully close Redis connection.
        """
        if self._redis:
            try:
                await self._redis.close()
            except Exception:
                pass
            finally:
                self._connected = False
