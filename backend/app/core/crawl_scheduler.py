"""
Crawl Scheduler
---------------
Coordinates URL fetching and extraction. When an access challenge is detected,
it records the event and stops dispatching additional requests to that site.
"""
import asyncio
import logging
from typing import Callable, Awaitable, Optional, List, Dict, Any

from app.core.url_frontier import URLFrontier
from app.core.page_fetcher import PageFetcher
from app.core.link_extractor import LinkExtractor
from app.core.product_extractor import ProductExtractor

logger = logging.getLogger(__name__)


class CrawlScheduler:
    """Coordinates crawling through the URL frontier."""

    def __init__(
        self,
        frontier: URLFrontier,
        fetcher: PageFetcher,
        extractor: LinkExtractor,
        product_extractor: ProductExtractor,
        on_page_crawled: Optional[Callable[[str, bool], Awaitable[None]]] = None,
        on_products_found: Optional[Callable[[List[Dict[str, Any]]], Awaitable[None]]] = None,
        on_challenge: Optional[Callable[[str, Dict[str, Any]], Awaitable[None]]] = None,
        max_concurrency: int = 3,
        poll_interval: float = 0.5,
    ):
        self.frontier = frontier
        self.fetcher = fetcher
        self.extractor = extractor
        self.product_extractor = product_extractor
        self.on_page_crawled = on_page_crawled
        self.on_products_found = on_products_found
        self.on_challenge = on_challenge
        self.max_concurrency = max_concurrency
        self.poll_interval = poll_interval

        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._running = False
        self._challenge_detected = False
        self._tasks: set[asyncio.Task] = set()

    def is_empty(self) -> bool:
        return self.frontier.stats()["queued"] == 0

    async def run(self) -> None:
        logger.info("CrawlScheduler started")
        self._running = True

        try:
            while self._running and not self._challenge_detected:
                if self.is_empty():
                    if not self._tasks:
                        logger.info("Frontier empty and no active tasks. Crawl complete.")
                        break
                    await asyncio.sleep(self.poll_interval)
                    continue

                url_item = await self.frontier.get_next()
                if not url_item:
                    await asyncio.sleep(self.poll_interval)
                    continue

                await self._semaphore.acquire()
                # A challenge may have been detected while waiting for a slot.
                if self._challenge_detected or not self._running:
                    self._semaphore.release()
                    break

                task = asyncio.create_task(self._process_url(url_item.url, url_item.depth))
                self._tasks.add(task)
                task.add_done_callback(self._on_task_done)

        except Exception as exc:
            logger.exception("Scheduler encountered critical error: %s", exc)
        finally:
            await self.stop()

    async def _process_url(self, url: str, depth: int) -> None:
        success = False
        try:
            result = await self.fetcher.fetch(url)
            success = result.success

            if result.challenge:
                # Stop dispatching more URLs to avoid repeatedly requesting a site
                # that has presented an access-control challenge.
                self._challenge_detected = True
                if self.on_challenge:
                    try:
                        await self.on_challenge(url, result.challenge)
                    except Exception:
                        logger.exception("Failed to record challenge event for %s", url)

            elif result.success and result.html:
                links = self.extractor.extract_links(result.html, url)
                for link in links:
                    await self.frontier.add_url(link, depth + 1)

                products = self.product_extractor.extract(result.html, url)
                if products and self.on_products_found:
                    await self.on_products_found(products)

            if self.on_page_crawled:
                await self.on_page_crawled(url, success)

        except Exception as exc:
            logger.error("Error processing %s: %s", url, exc)
        finally:
            self._semaphore.release()

    async def stop(self) -> None:
        logger.info("Stopping CrawlScheduler...")
        self._running = False

        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

        logger.info("CrawlScheduler stopped")

    def _on_task_done(self, task: asyncio.Task) -> None:
        self._tasks.discard(task)

    @property
    def active_tasks(self) -> int:
        return len(self._tasks)

    @property
    def challenge_detected(self) -> bool:
        return self._challenge_detected
