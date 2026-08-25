import asyncio
import logging
from typing import List, Dict, Any, Optional, Callable, Awaitable
from urllib.parse import urlparse

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

from .httpx_scraper import _get_selectors, _extract_products, _extract_links

logger = logging.getLogger(__name__)

class PlaywrightScraper:
    """
    Reliable async scraper using Playwright for JS-rendered sites.
    Provides the exact same API as HttpxScraper.
    """

    def __init__(
        self,
        job_id: int,
        start_url: str,
        *,
        max_pages: int = 100,
        max_products: int = 10000,
        max_depth: int = 3,
        request_delay: float = 1.0,
        proxy: Optional[Dict[str, str]] = None,
        on_log: Optional[Callable[[str, str], Awaitable[None]]] = None,
        on_product_batch: Optional[Callable[[List[Dict]], Awaitable[None]]] = None,
        on_page_done: Optional[Callable[[str, bool, int], Awaitable[None]]] = None,
    ):
        self.job_id = job_id
        self.start_url = start_url.rstrip("/")
        self.max_pages = max_pages
        self.max_products = max_products
        self.max_depth = max_depth
        self.request_delay = request_delay
        self.proxy = proxy

        parsed = urlparse(start_url)
        self.allowed_domain = parsed.netloc

        self.selectors = _get_selectors(start_url)
        self.platform = self.selectors.get("platform", "Generic")

        self.on_log = on_log
        self.on_product_batch = on_product_batch
        self.on_page_done = on_page_done

        self._visited: set = set()
        self._queue: List[tuple] = [(self.start_url, 0)]  # (url, depth)
        self._total_products = 0

    async def _log(self, message: str, level: str = "info"):
        logger.info(f"[Job {self.job_id}] {message}")
        if self.on_log:
            await self.on_log(message, level)

    async def run(self):
        import asyncio
        from playwright.sync_api import sync_playwright, TimeoutError as SyncTimeoutError
        import time

        await self._log(f"Starting Playwright scrape of {self.start_url}")
        await self._log(f"Detected platform: {self.platform} (JS Rendered)")
        await self._log(f"Max pages: {self.max_pages} | Max products: {self.max_products}")

        loop = asyncio.get_running_loop()
        
        def _sync_log(msg, lvl="info"):
            asyncio.run_coroutine_threadsafe(self._log(msg, lvl), loop)

        def _scrape_sync():
            try:
                import sys
                if sys.platform == 'win32':
                    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
                    
                pages_scraped = 0
                with sync_playwright() as p:
                    launch_args = [
                        "--disable-blink-features=AutomationControlled",
                        "--use-fake-device-for-media-stream",
                        "--use-fake-ui-for-media-stream"
                    ]
                    context_kwargs = {
                        "viewport": {'width': 1920, 'height': 1080},
                        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                        "locale": "en-US",
                        "timezone_id": "America/New_York",
                        "extra_http_headers": {
                            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                            "Accept-Language": "en-US,en;q=0.9",
                            "Accept-Encoding": "gzip, deflate, br, zstd",
                            "Connection": "keep-alive",
                            "Upgrade-Insecure-Requests": "1",
                            "sec-ch-ua": '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
                            "sec-ch-ua-mobile": "?0",
                            "sec-ch-ua-platform": '"Windows"',
                            "Sec-Fetch-Dest": "document",
                            "Sec-Fetch-Mode": "navigate",
                            "Sec-Fetch-Site": "none",
                            "Sec-Fetch-User": "?1",
                        }
                    }

                    def _launch_browser(use_proxy=False):
                        kw = {"headless": True, "args": launch_args}
                        if use_proxy and self.proxy:
                            kw["proxy"] = self.proxy
                            _sync_log(f"  ↳ Using proxy server: {self.proxy.get('server', self.proxy)}")
                        else:
                            _sync_log("  ↳ Direct connection (no proxy)")
                        browser = p.chromium.launch(**kw)
                        context = browser.new_context(**context_kwargs)
                        pg = context.new_page()
                        try:
                            from playwright_stealth import stealth_sync
                            stealth_sync(pg)
                        except Exception:
                            pass
                        pg.add_init_script("""
                            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                            window.navigator.chrome = { runtime: {},  };
                            Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
                            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
                        """)
                        return browser, pg

                    # Strategy: try direct first, fallback to proxy on 403/503/tunnel error
                    using_proxy = False
                    browser, page = _launch_browser(use_proxy=False)

                    while self._queue and pages_scraped < self.max_pages and self._total_products < self.max_products:
                        url, depth = self._queue.pop(0)

                        if url in self._visited:
                            continue
                        self._visited.add(url)

                        _sync_log(f"[{pages_scraped + 1}/{self.max_pages}] Fetching: {url}")
                        
                        try:
                            response = page.goto(url, wait_until="commit", timeout=25000)
                        except SyncTimeoutError:
                            _sync_log(f"  ↳ Timeout navigating to {url} — skipping", "warning")
                            if self.on_page_done:
                                asyncio.run_coroutine_threadsafe(self.on_page_done(url, False, pages_scraped), loop)
                            continue
                        except Exception as nav_err:
                            err_str = str(nav_err)
                            # If tunnel/connection failed on direct, retry with proxy
                            if not using_proxy and self.proxy and ("TUNNEL" in err_str.upper() or "CONNECTION" in err_str.upper()):
                                _sync_log(f"  ↳ Direct connection failed, switching to proxy...", "warning")
                                browser.close()
                                using_proxy = True
                                browser, page = _launch_browser(use_proxy=True)
                                self._visited.discard(url)
                                self._queue.insert(0, (url, depth))
                                continue
                            _sync_log(f"  ↳ Navigation error: {nav_err}", "warning")
                            if self.on_page_done:
                                asyncio.run_coroutine_threadsafe(self.on_page_done(url, False, pages_scraped), loop)
                            continue

                        status = response.status if response else 0

                        # If first page is 403/503 and we have a proxy, retry with proxy
                        if status in (403, 503) and not using_proxy and self.proxy and pages_scraped == 0:
                            _sync_log(f"  ↳ HTTP {status} on direct — retrying with proxy...", "warning")
                            browser.close()
                            using_proxy = True
                            browser, page = _launch_browser(use_proxy=True)
                            self._visited.discard(url)
                            self._queue.insert(0, (url, depth))
                            continue

                        if status >= 400:
                            _sync_log(f"  ↳ HTTP {status} — skipping", "warning")
                            if self.on_page_done:
                                asyncio.run_coroutine_threadsafe(self.on_page_done(url, False, pages_scraped), loop)
                            continue

                        # Wait for DOM body to be ready after commit-level navigation
                        try:
                            page.wait_for_selector("body", timeout=10000)
                        except Exception:
                            pass

                        page.evaluate("""
                            if (document.body) {
                                window.scrollTo(0, document.body.scrollHeight / 2);
                                setTimeout(() => window.scrollTo(0, document.body.scrollHeight), 500);
                            }
                        """)
                        
                        # Wait up to 3 seconds specifically for product cards to load dynamically
                        try:
                            page.wait_for_selector("div.grid div.bg-white.flex-col, div[data-product-card], .product, .products, [class*='product']", timeout=3000)
                        except Exception:
                            # Not a product page, or loaded slow, proceed anyway
                            page.wait_for_timeout(1500)
                            
                        html = page.content()
                        pages_scraped += 1

                        products = _extract_products(html, url, self.selectors)
                        if products:
                            _sync_log(f"  ↳ Found {len(products)} products on page")
                            if self.on_product_batch:
                                fut = asyncio.run_coroutine_threadsafe(self.on_product_batch(products), loop)
                                try:
                                    fut.result(timeout=15)
                                except Exception as e:
                                    _sync_log(f"  ↳ Error saving products batch: {e}", "error")
                            self._total_products += len(products)
                        else:
                            _sync_log("  ↳ No products found on this page")

                        if self.on_page_done:
                            fut = asyncio.run_coroutine_threadsafe(self.on_page_done(url, True, pages_scraped), loop)
                            try:
                                fut.result(timeout=5)
                            except Exception:
                                pass

                        if depth < self.max_depth:
                            links = _extract_links(html, url, self.allowed_domain)
                            new_links = [l for l in links if l not in self._visited]
                            for link in new_links:
                                self._queue.append((link, depth + 1))
                                
                        time.sleep(self.request_delay)

                    browser.close()
                return pages_scraped
            except Exception as e:
                import traceback
                err = traceback.format_exc()
                logger.error(f"[Job {self.job_id}] Playwright Initialization Error: {err}")
                return {"error": err}

        # Run the entire crawl inside the thread pool using thread-safe loggers
        result = await asyncio.to_thread(_scrape_sync)
        
        pages_count = 0
        if isinstance(result, dict) and "error" in result:
            await self._log(f"Playwright crashed: {result['error']}", "error")
        else:
            pages_count = result or 0

        await self._log(
            f"Scrape complete. Pages: {pages_count}, Products: {self._total_products}"
        )
