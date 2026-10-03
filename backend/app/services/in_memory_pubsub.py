import asyncio
import logging
from typing import Dict, Set, Callable, Awaitable, Any

logger = logging.getLogger(__name__)

class InMemoryPubSub:
    """
    Resilient in-memory pub-sub provider.
    Used as the primary communication path and fallback when Redis is offline or not installed.
    """
    def __init__(self):
        self._subscribers: Dict[str, Set[Callable[[Dict[str, Any]], Awaitable[None]]]] = {}
        self._lock = asyncio.Lock()

    async def subscribe(self, channel: str, callback: Callable[[Dict[str, Any]], Awaitable[None]]):
        async with self._lock:
            if channel not in self._subscribers:
                self._subscribers[channel] = set()
            self._subscribers[channel].add(callback)
            logger.debug(f"Subscribed callback to channel: {channel}")

    async def unsubscribe(self, channel: str, callback: Callable[[Dict[str, Any]], Awaitable[None]]):
        async with self._lock:
            if channel in self._subscribers:
                self._subscribers[channel].discard(callback)
                if not self._subscribers[channel]:
                    del self._subscribers[channel]
            logger.debug(f"Unsubscribed callback from channel: {channel}")

    async def publish(self, channel: str, message: Dict[str, Any]):
        async with self._lock:
            subscribers = list(self._subscribers.get(channel, []))
        
        if not subscribers:
            return

        logger.debug(f"Publishing to channel {channel} for {len(subscribers)} local subscribers")
        for callback in subscribers:
            try:
                await callback(message)
            except Exception as e:
                logger.warning(f"Error executing callback on channel {channel}: {e}")

# Global singleton
in_memory_pubsub = InMemoryPubSub()
