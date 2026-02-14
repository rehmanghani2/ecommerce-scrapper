"""
Crawl Scheduler Module
----------------------
Responsible for orchestrating crawl execution using the URL Frontier.
This module controls:
- Concurrency limits
- Crawl lifecycle per job
- Safe async execution

Designed for a generic, large-scale ecommerce crawler (200+ sites).
Fully aligned with existing FastAPI + async architecture.
"""

import asyncio
import logging
from typing import Callable, Awaitable

from app.core.url_frontier import URLFrontier

logger = logging.getLogger(__name__)


class CrawlScheduler:
    """
    CrawlScheduler coordinates crawling by pulling URLs from URLFrontier
    and dispatching them to a fetch coroutine with controlled concurrency.
    """

    def __init__(
        self,
        frontier: URLFrontier,
        fetch_callback: Callable[[str, int], Awaitable[None]],
        max_concurrency: int = 5,
        poll_interval: float = 0.1,
    ):
        """
        :param frontier: URLFrontier instance
        :param fetch_callback: async function(url, depth)
        :param max_concurrency: maximum concurrent fetches
        :param poll_interval: wait time when frontier is empty
        """
        self.frontier = frontier
        self.fetch_callback = fetch_callback
        self.max_concurrency = max_concurrency
        self.poll_interval = poll_interval

        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._running = False
        self._tasks: set[asyncio.Task] = set()

    async def start(self) -> None:
        """Start the crawl scheduler loop."""
        logger.info("CrawlScheduler started")
        self._running = True

        while self._running:
            if self.frontier.is_empty():
                await asyncio.sleep(self.poll_interval)
                continue

            url_item = await self.frontier.get_next_url()
            if not url_item:
                await asyncio.sleep(self.poll_interval)
                continue

            url, depth = url_item

            await self._semaphore.acquire()
            task = asyncio.create_task(self._run_fetch(url, depth))
            self._tasks.add(task)
            task.add_done_callback(self._on_task_done)

    async def stop(self) -> None:
        """Gracefully stop the scheduler and wait for running tasks."""
        logger.info("Stopping CrawlScheduler...")
        self._running = False

        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

        logger.info("CrawlScheduler stopped")

    async def _run_fetch(self, url: str, depth: int) -> None:
        """Wrapper to execute fetch callback safely."""
        try:
            await self.fetch_callback(url, depth)
        except Exception as exc:
            logger.exception(f"Fetch failed for {url}: {exc}")
        finally:
            self._semaphore.release()

    def _on_task_done(self, task: asyncio.Task) -> None:
        """Cleanup completed tasks."""
        self._tasks.discard(task)

    @property
    def active_tasks(self) -> int:
        return len(self._tasks)
