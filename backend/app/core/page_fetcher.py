"""
page_fetcher.py
----------------
Responsible for fetching pages using Playwright in a controlled, reusable,
and fault-tolerant way.

This module does NOT extract data. It only:
- Opens pages
- Applies navigation rules
- Returns HTML / Playwright page object

This design allows us to safely test 200+ ecommerce websites.
"""

from typing import Optional, Dict

from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError

from app.utils.logger import get_logger

logger = get_logger(__name__)


class PageFetchResult:
    """
    Standardized result object returned by PageFetcher
    """

    def __init__(
        self,
        success: bool,
        url: str,
        status: Optional[int] = None,
        html: Optional[str] = None,
        error: Optional[str] = None,
    ):
        self.success = success
        self.url = url
        self.status = status
        self.html = html
        self.error = error


class PageFetcher:
    """
    PageFetcher encapsulates all browser interaction logic.

    WHY THIS EXISTS:
    - Centralizes Playwright usage
    - Avoids duplicated browser code
    - Makes retries, timeouts, and headers consistent
    """

    def __init__(
        self,
        page: Page,
        *,
        timeout_ms: int = 30000,
        wait_until: str = "domcontentloaded",
        extra_headers: Optional[Dict[str, str]] = None,
    ):
        self.page = page
        self.timeout_ms = timeout_ms
        self.wait_until = wait_until
        self.extra_headers = extra_headers or {}

    async def fetch(self, url: str) -> PageFetchResult:
        """
        Navigate to a URL and return page content.

        This method NEVER raises exceptions upward.
        All failures are captured and returned safely.
        """

        try:
            logger.info(f"Fetching URL: {url}")

            if self.extra_headers:
                await self.page.set_extra_http_headers(self.extra_headers)

            response = await self.page.goto(
                url,
                timeout=self.timeout_ms,
                wait_until=self.wait_until,
            )

            if response is None:
                return PageFetchResult(
                    success=False,
                    url=url,
                    error="No response returned from page.goto",
                )

            status = response.status

            if status >= 400:
                return PageFetchResult(
                    success=False,
                    url=url,
                    status=status,
                    error=f"HTTP error {status}",
                )

            html = await self.page.content()

            return PageFetchResult(
                success=True,
                url=url,
                status=status,
                html=html,
            )

        except PlaywrightTimeoutError:
            logger.warning(f"Timeout while fetching: {url}")
            return PageFetchResult(
                success=False,
                url=url,
                error="Navigation timeout",
            )

        except Exception as exc:
            logger.exception(f"Unexpected error while fetching {url}")
            return PageFetchResult(
                success=False,
                url=url,
                error=str(exc),
            )

    async def close(self):
        """
        Close page explicitly if scheduler owns lifecycle.
        """
        try:
            await self.page.close()
        except Exception:
            pass
