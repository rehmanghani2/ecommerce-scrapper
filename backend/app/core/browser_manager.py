import logging
from typing import Optional

from playwright.async_api import async_playwright, Browser, BrowserContext, Page


logger = logging.getLogger(__name__)


class BrowserManager:

    def __init__(self, headless: bool = True):
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._headless = headless

    async def start(self):
        self._playwright = await async_playwright().start()

        self._browser = await self._playwright.chromium.launch(
            headless=self._headless
        )

        self._context = await self._browser.new_context()

        logger.info("BrowserManager started")

    async def new_page(self) -> Page:
        if not self._context:
            raise RuntimeError("Browser not started")

        return await self._context.new_page()

    async def close(self):
        try:
            if self._context:
                await self._context.close()

            if self._browser:
                await self._browser.close()

            if self._playwright:
                await self._playwright.stop()

            logger.info("BrowserManager closed")

        except Exception as e:
            logger.error(f"BrowserManager shutdown error: {e}")
