"""
Playwright page fetching with conservative CAPTCHA / anti-bot challenge detection.

This module detects access challenges only. It never solves or bypasses them.
"""
from typing import Any, Dict, Optional

from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError

from app.core.challenge_detector import detect_challenge
from app.utils.logger import get_logger

logger = get_logger(__name__)


class PageFetchResult:
    """Standardized result returned by PageFetcher."""

    def __init__(
        self,
        success: bool,
        url: str,
        status: Optional[int] = None,
        html: Optional[str] = None,
        error: Optional[str] = None,
        challenge: Optional[Dict[str, Any]] = None,
    ):
        self.success = success
        self.url = url
        self.status = status
        self.html = html
        self.error = error
        self.challenge = challenge


class PageFetcher:
    """Centralizes Playwright navigation, response handling, and challenge checks."""

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
        self.extra_headers = extra_headers or {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    async def _challenge_result(
        self, url: str, status: Optional[int], html: Optional[str]
    ) -> Optional[PageFetchResult]:
        challenge = detect_challenge(url, status, html)
        if not challenge:
            return None

        logger.warning(
            "Access challenge detected: provider=%s url=%s",
            challenge["provider"],
            url,
        )
        return PageFetchResult(
            success=False,
            url=url,
            status=status,
            error="Access challenge detected; page was not processed",
            challenge=challenge,
        )

    async def fetch(self, url: str) -> PageFetchResult:
        """
        Navigate to a URL and return page content.

        Failures are returned as PageFetchResult objects. A detected challenge is
        surfaced separately so the scheduler can log it and stop issuing requests.
        """
        try:
            logger.info("Fetching URL: %s", url)

            if self.extra_headers:
                await self.page.set_extra_http_headers(self.extra_headers)

            response = await self.page.goto(
                url,
                timeout=self.timeout_ms,
                wait_until=self.wait_until,
            )

            status = response.status if response is not None else None
            html = await self.page.content()

            challenge_result = await self._challenge_result(url, status, html)
            if challenge_result:
                return challenge_result

            if response is None:
                return PageFetchResult(
                    success=False,
                    url=url,
                    error="No response returned from page.goto",
                )

            if status is not None and status >= 400:
                return PageFetchResult(
                    success=False,
                    url=url,
                    status=status,
                    error=f"HTTP error {status}",
                )

            return PageFetchResult(
                success=True,
                url=url,
                status=status,
                html=html,
            )

        except PlaywrightTimeoutError:
            logger.warning("Timeout while fetching: %s", url)
            # Some challenge pages render before the navigation wait times out.
            try:
                html = await self.page.content()
                challenge_result = await self._challenge_result(url, None, html)
                if challenge_result:
                    return challenge_result
            except Exception:
                pass

            return PageFetchResult(
                success=False,
                url=url,
                error="Navigation timeout",
            )

        except Exception as exc:
            logger.exception("Unexpected error while fetching %s", url)
            return PageFetchResult(
                success=False,
                url=url,
                error=str(exc),
            )

    async def close(self):
        """Close page explicitly if scheduler owns lifecycle."""
        try:
            await self.page.close()
        except Exception:
            pass
