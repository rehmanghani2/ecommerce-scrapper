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

        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--use-fake-device-for-media-stream",
            "--use-fake-ui-for-media-stream"
        ]
        self._browser = await self._playwright.chromium.launch(
            headless=self._headless,
            args=launch_args
        )

        self._context = await self._browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            locale="en-US",
            timezone_id="America/New_York",
            extra_http_headers={
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
        )

        # Inject stealth scripts to the context
        stealth_js = """
        () => {
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.navigator.chrome = { runtime: {},  };
            Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
        }
        """
        await self._context.add_init_script(stealth_js)

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
