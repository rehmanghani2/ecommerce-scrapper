"""
Parallel Bulk Batch Scraper Worker.
Crawls large sets of product URLs (up to 10,000+) concurrently using an asyncio worker pool,
smart per-domain rate limiting, proxy rotation, and incremental database batch commits.
"""

import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Callable, Awaitable
from urllib.parse import urlparse, urljoin
import httpx
from bs4 import BeautifulSoup

from app.core.httpx_scraper import HEADERS, _get_selectors, _extract_products
from app.core.proxy_manager import ProxyPoolManager, ProxyNode

logger = logging.getLogger(__name__)


class BulkBatchScraper:
    """
    High-throughput concurrent scraper designed for bulk URL sets and sitemaps.
    Processes URLs in parallel chunks using an asyncio Semaphore worker pool.
    """

    def __init__(
        self,
        job_id: int,
        urls: List[str],
        *,
        concurrency: int = 10,
        request_delay: float = 0.5,
        proxy_pool: Optional[ProxyPoolManager] = None,
        custom_selectors: Optional[Dict[str, Any]] = None,
        on_log: Optional[Callable[[str, str], Awaitable[None]]] = None,
        on_product_batch: Optional[Callable[[List[Dict[str, Any]]], Awaitable[None]]] = None,
        on_progress: Optional[Callable[[int, int, int], Awaitable[None]]] = None,  # (completed, total, successful)
    ):
        self.job_id = job_id
        self.urls = list(dict.fromkeys(urls))  # deduplicate preserving order
        self.total_urls = len(self.urls)
        self.concurrency = max(1, min(concurrency, 50))  # safe clamp between 1 and 50
        self.request_delay = max(0.0, request_delay)
        self.proxy_pool = proxy_pool
        self.custom_selectors = custom_selectors
        self.on_log = on_log
        self.on_product_batch = on_product_batch
        self.on_progress = on_progress

        self._completed_count = 0
        self._successful_count = 0
        self._failed_count = 0
        self._total_products_scraped = 0
        self._batch_lock = asyncio.Lock()
        self._pending_batch: List[Dict[str, Any]] = []

    async def _log(self, message: str, level: str = "info"):
        logger.info(f"[BulkJob {self.job_id}] {message}")
        if self.on_log:
            try:
                await self.on_log(message, level)
            except Exception as e:
                logger.error(f"Error in on_log: {e}")

    async def _flush_batch_if_needed(self, force: bool = False):
        """Flush accumulated scraped products to database callback in batches of 25."""
        async with self._batch_lock:
            if (len(self._pending_batch) >= 25 or (force and self._pending_batch)) and self.on_product_batch:
                to_commit = list(self._pending_batch)
                self._pending_batch.clear()
                try:
                    await self.on_product_batch(to_commit)
                except Exception as e:
                    logger.error(f"Error saving product batch in BulkBatchScraper: {e}")

    def extract_from_product_page(self, html: str, page_url: str, selectors: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract product data from a single product page or catalog page.
        Tries container list extraction first; if empty, extracts single product detail page.
        """
        # 1. Try list extraction first
        products = _extract_products(html, page_url, selectors)
        if products:
            return products

        # 2. Detail Page Fallback: entire page is a single product
        try:
            soup = BeautifulSoup(html, "lxml")
        except Exception:
            soup = BeautifulSoup(html, "html.parser")

        # Name heuristic
        title_el = (
            soup.select_one("h1.product-title, h1[data-product-name], h1.title, h1")
            or soup.select_one("meta[property='og:title']")
        )
        name = None
        if title_el:
            if title_el.name == "meta":
                name = title_el.get("content", "").strip()
            else:
                name = title_el.get_text(strip=True)

        if not name or len(name) < 2:
            # Try HTML page title
            if soup.title:
                raw_t = soup.title.get_text(strip=True)
                # Split brand suffix
                name = raw_t.split(" - ")[0].split(" | ")[0]

        # Price heuristic
        price_text = None
        price_val = None
        price_el = soup.select_one(
            ".price, [data-price], .product-price, .current-price, .amount, span[class*='price']"
        )
        if price_el:
            price_text = price_el.get_text(strip=True)
        else:
            meta_price = soup.select_one("meta[property='product:price:amount']")
            if meta_price:
                price_text = meta_price.get("content")

        if price_text:
            nums = re.findall(r"[\d,]+\.?\d*", price_text.replace(",", ""))
            if nums:
                try:
                    price_val = float(nums[0])
                except ValueError:
                    pass

        # Image heuristic
        image_url = None
        img_el = soup.select_one(
            "img.product-image, img[data-main-image], img[property='og:image'], meta[property='og:image']"
        )
        if img_el:
            if img_el.name == "meta":
                image_url = img_el.get("content")
            else:
                image_url = img_el.get("src") or img_el.get("data-src")
            if image_url:
                image_url = urljoin(page_url, image_url)

        if name and len(name) > 2:
            return [{
                "name": name[:500],
                "price": price_val,
                "price_text": price_text,
                "image_url": image_url,
                "url": page_url,
            }]

        return []

    async def _fetch_and_process_url(
        self,
        url: str,
        semaphore: asyncio.Semaphore,
        client: httpx.AsyncClient,
    ):
        """Worker task processing a single URL."""
        async with semaphore:
            selectors = self.custom_selectors or _get_selectors(url)
            html = ""
            status_code = 0
            success = False

            # Setup proxy if pool is available
            curr_node: Optional[ProxyNode] = None
            if self.proxy_pool and self.proxy_pool.has_proxies:
                curr_node = self.proxy_pool.get_next_proxy()

            headers = dict(HEADERS)
            req_kwargs = {"headers": headers, "follow_redirects": True}

            try:
                # If specific proxy is required per request, create targeted client or use pool
                if curr_node:
                    async with httpx.AsyncClient(
                        proxy=curr_node.to_httpx_proxy(),
                        timeout=25.0,
                        verify=False,
                        follow_redirects=True,
                        headers=headers,
                    ) as p_client:
                        resp = await p_client.get(url)
                else:
                    resp = await client.get(url, timeout=25.0)

                status_code = resp.status_code
                if status_code == 200:
                    html = resp.text
                    success = True
                    if curr_node:
                        self.proxy_pool.report_success(curr_node)
                elif status_code in (403, 429) and curr_node and self.proxy_pool:
                    self.proxy_pool.report_failure(curr_node, status_code)
            except Exception as req_err:
                if curr_node and self.proxy_pool:
                    self.proxy_pool.report_failure(curr_node, error_msg=str(req_err))
                logger.debug(f"Request failed for {url}: {req_err}")

            if success and html:
                products = self.extract_from_product_page(html, url, selectors)
                if products:
                    async with self._batch_lock:
                        self._pending_batch.extend(products)
                        self._total_products_scraped += len(products)
                    await self._flush_batch_if_needed(force=False)
                self._successful_count += 1
            else:
                self._failed_count += 1

            self._completed_count += 1

            # Periodically emit progress callback
            if self.on_progress and (self._completed_count % 5 == 0 or self._completed_count == self.total_urls):
                try:
                    await self.on_progress(self._completed_count, self.total_urls, self._successful_count)
                except Exception as e:
                    logger.error(f"Error in on_progress: {e}")

            # Polite concurrency delay
            if self.request_delay > 0:
                await asyncio.sleep(self.request_delay)

    async def run(self):
        """Execute parallel scraping across all URLs with concurrency limit."""
        await self._log(
            f"🚀 Initiating parallel crawl across {self.total_urls} URLs "
            f"with concurrency={self.concurrency} worker slots."
        )

        semaphore = asyncio.Semaphore(self.concurrency)
        timeout = httpx.Timeout(30.0)

        async with httpx.AsyncClient(
            headers=HEADERS,
            timeout=timeout,
            follow_redirects=True,
            verify=False,
        ) as default_client:
            tasks = [
                self._fetch_and_process_url(url, semaphore, default_client)
                for url in self.urls
            ]
            await asyncio.gather(*tasks, return_exceptions=True)

        # Final flush for any remaining products
        await self._flush_batch_if_needed(force=True)

        await self._log(
            f"✅ Parallel crawl complete: {self._completed_count}/{self.total_urls} URLs processed "
            f"({self._successful_count} OK, {self._failed_count} errors). "
            f"Total products scraped: {self._total_products_scraped}."
        )
