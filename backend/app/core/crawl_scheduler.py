"""
Crawl Scheduler Module
----------------------
Responsible for orchestrating crawl execution using the URL Frontier.
"""

import asyncio
import logging
from typing import Callable, Awaitable, Optional

from app.core.url_frontier import URLFrontier
from app.core.page_fetcher import PageFetcher
from app.core.link_extractor import LinkExtractor

logger = logging.getLogger(__name__)


class CrawlScheduler:
    """
    CrawlScheduler coordinates crawling by pulling URLs from URLFrontier,
    using PageFetcher to get content, and LinkExtractor to find new URLs.
    """

    def __init__(
        self,
        frontier: URLFrontier,
        fetcher: PageFetcher,
        extractor: LinkExtractor,
        on_page_crawled: Optional[Callable[[str, bool], Awaitable[None]]] = None,
        max_concurrency: int = 3,
        poll_interval: float = 0.5,
    ):
        self.frontier = frontier
        self.fetcher = fetcher
        self.extractor = extractor
        self.on_page_crawled = on_page_crawled
        self.max_concurrency = max_concurrency
        self.poll_interval = poll_interval

        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._running = False
        self._tasks: set[asyncio.Task] = set()

    def is_empty(self) -> bool:
        """Check if the frontier is empty."""
        return self.frontier.stats()["queued"] == 0

    async def run(self) -> None:
        """
        Main execution loop.
        """
        logger.info("CrawlScheduler started")
        self._running = True

        try:
            while self._running:
                # Check if we reached limits or frontier is empty
                if self.is_empty():
                    # If no active tasks, we are done
                    if not self._tasks:
                        logger.info("Frontier empty and no active tasks. Crawl complete.")
                        break
                    await asyncio.sleep(self.poll_interval)
                    continue

                # Get next URL
                url_item = await self.frontier.get_next()
                if not url_item:
                    await asyncio.sleep(self.poll_interval)
                    continue

                url, depth = url_item.url, url_item.depth

                # Wait for slot and spawn task
                await self._semaphore.acquire()
                task = asyncio.create_task(self._process_url(url, depth))
                self._tasks.add(task)
                task.add_done_callback(self._on_task_done)

        except Exception as e:
            logger.exception(f"Scheduler encountered critical error: {e}")
        finally:
            await self.stop()

    async def _process_url(self, url: str, depth: int) -> None:
        """
        Single URL processing unit.
        """
        success = False
        try:
            # 1. Fetch
            result = await self.fetcher.fetch(url)
            success = result.success

            if result.success and result.html:
                # 2. Extract links and add to frontier
                links = self.extractor.extract_links(result.html, url)
                for link in links:
                    await self.frontier.add_url(link, depth + 1)
                
                # 3. TODO: Extract products if it's a product page
                # (This would be handled by ProductExtractor in a real implementation)
            
            # 4. Notify progress
            if self.on_page_crawled:
                await self.on_page_crawled(url, success)

        except Exception as exc:
            logger.error(f"Error processing {url}: {exc}")
        finally:
            self._semaphore.release()

    async def stop(self) -> None:
        """Gracefully stop the scheduler."""
        logger.info("Stopping CrawlScheduler...")
        self._running = False

        if self._tasks:
            # Wait for remaining tasks to finish
            await asyncio.gather(*self._tasks, return_exceptions=True)

        logger.info("CrawlScheduler stopped")

    def _on_task_done(self, task: asyncio.Task) -> None:
        """Cleanup completed tasks."""
        self._tasks.discard(task)

    @property
    def active_tasks(self) -> int:
        return len(self._tasks)
