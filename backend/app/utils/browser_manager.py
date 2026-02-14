"""
Browser Manager Module
Manages Playwright browser instances and contexts for web scraping.
"""

import asyncio
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from contextlib import asynccontextmanager
from playwright.async_api import async_playwright, Browser, BrowserContext, Playwright
import logging

from app.config import settings
from app.utils.user_agents import UserAgentRotator, UserAgentInfo
from app.utils.proxy_rotator import ProxyRotator

logger = logging.getLogger(__name__)


@dataclass
class BrowserConfig:
    """Configuration for browser instances."""
    headless: bool = True
    browser_type: str = "chromium"  # chromium, firefox, webkit
    viewport_width: int = 1920
    viewport_height: int = 1080
    locale: str = "en-GB"
    timezone: str = "Europe/London"
    geolocation: Optional[Dict[str, float]] = None
    permissions: List[str] = field(default_factory=list)
    extra_http_headers: Optional[Dict[str, str]] = None
    ignore_https_errors: bool = True
    java_script_enabled: bool = True
    accept_downloads: bool = False
    
    # Anti-detection
    disable_webrtc: bool = True
    disable_blink_features: str = "AutomationControlled"


class BrowserManager:
    """
    Manages Playwright browser instances for web scraping.
    
    Features:
    - Browser pool management
    - Context isolation
    - Anti-detection measures
    - Automatic resource cleanup
    - Proxy integration
    - User agent rotation
    """
    
    def __init__(
        self,
        max_browsers: int = None,
        config: Optional[BrowserConfig] = None
    ):
        """
        Initialize the browser manager.
        
        Args:
            max_browsers: Maximum number of concurrent browsers
            config: Browser configuration
        """
        self.max_browsers = max_browsers or settings.MAX_CONCURRENT_BROWSERS
        self.config = config or BrowserConfig(
            headless=settings.HEADLESS,
            browser_type=settings.BROWSER_TYPE
        )
        
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._contexts: Dict[str, BrowserContext] = {}
        self._lock = asyncio.Lock()
        self._initialized = False
        
        # Utilities
        self._user_agent_rotator = UserAgentRotator()
        self._proxy_rotator: Optional[ProxyRotator] = None
        
        if settings.USE_PROXY:
            self._proxy_rotator = ProxyRotator()
    
    async def initialize(self) -> None:
        """Initialize Playwright and launch browser."""
        if self._initialized:
            return
        
        async with self._lock:
            if self._initialized:
                return
            
            logger.info(f"Initializing browser manager with {self.config.browser_type}...")
            
            try:
                self._playwright = await async_playwright().start()
                
                # Get browser launcher
                if self.config.browser_type == "firefox":
                    launcher = self._playwright.firefox
                elif self.config.browser_type == "webkit":
                    launcher = self._playwright.webkit
                else:
                    launcher = self._playwright.chromium
                
                # Launch options
                launch_options = {
                    "headless": self.config.headless,
                }
                
                # Add anti-detection args for Chromium
                if self.config.browser_type == "chromium":
                    launch_options["args"] = [
                        "--disable-blink-features=AutomationControlled",
                        "--disable-dev-shm-usage",
                        "--disable-infobars",
                        "--disable-background-networking",
                        "--disable-default-apps",
                        "--disable-extensions",
                        "--disable-gpu",
                        "--disable-sync",
                        "--no-first-run",
                        "--no-sandbox",
                        "--metrics-recording-only",
                        "--mute-audio",
                    ]
                
                self._browser = await launcher.launch(**launch_options)
                self._initialized = True
                
                logger.info(f"Browser manager initialized successfully")
                
            except Exception as e:
                logger.error(f"Failed to initialize browser manager: {e}")
                raise
    
    async def shutdown(self) -> None:
        """Shutdown browser and cleanup resources."""
        async with self._lock:
            logger.info("Shutting down browser manager...")
            
            # Close all contexts
            for context_id, context in list(self._contexts.items()):
                try:
                    await context.close()
                except Exception as e:
                    logger.warning(f"Error closing context {context_id}: {e}")
            self._contexts.clear()
            
            # Close browser
            if self._browser:
                try:
                    await self._browser.close()
                except Exception as e:
                    logger.warning(f"Error closing browser: {e}")
                self._browser = None
            
            # Stop Playwright
            if self._playwright:
                try:
                    await self._playwright.stop()
                except Exception as e:
                    logger.warning(f"Error stopping Playwright: {e}")
                self._playwright = None
            
            self._initialized = False
            logger.info("Browser manager shutdown complete")
    
    async def _create_context(
        self,
        context_id: str,
        user_agent: Optional[UserAgentInfo] = None,
        proxy: Optional[Dict] = None,
        cookies: Optional[List[Dict]] = None
    ) -> BrowserContext:
        """
        Create a new browser context with anti-detection measures.
        
        Args:
            context_id: Unique identifier for the context
            user_agent: User agent configuration
            proxy: Proxy configuration
            cookies: Initial cookies to set
        
        Returns:
            New BrowserContext
        """
        if not self._browser:
            await self.initialize()
        
        # Get user agent
        if user_agent is None:
            user_agent = self._user_agent_rotator.get_random()
        
        # Context options
        context_options = {
            "viewport": {
                "width": user_agent.viewport["width"],
                "height": user_agent.viewport["height"]
            },
            "user_agent": user_agent.user_agent,
            "locale": self.config.locale,
            "timezone_id": self.config.timezone,
            "ignore_https_errors": self.config.ignore_https_errors,
            "java_script_enabled": self.config.java_script_enabled,
            "accept_downloads": self.config.accept_downloads,
        }
        
        # Add proxy if provided
        if proxy:
            context_options["proxy"] = proxy
        
        # Add geolocation if configured
        if self.config.geolocation:
            context_options["geolocation"] = self.config.geolocation
            context_options["permissions"] = ["geolocation"]
        
        # Add extra headers
        if self.config.extra_http_headers:
            context_options["extra_http_headers"] = self.config.extra_http_headers
        
        # Create context
        context = await self._browser.new_context(**context_options)
        
        # Add anti-detection scripts
        await self._apply_stealth(context)
        
        # Set initial cookies
        if cookies:
            await context.add_cookies(cookies)
        
        self._contexts[context_id] = context
        logger.debug(f"Created browser context: {context_id}")
        
        return context
    
    async def _apply_stealth(self, context: BrowserContext) -> None:
        """Apply stealth scripts to evade bot detection."""
        
        # Stealth JavaScript to evade detection
        stealth_js = """
        () => {
            // Override navigator.webdriver
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
            
            // Override navigator.plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
            
            // Override navigator.languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-GB', 'en-US', 'en'],
            });
            
            // Override permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
            
            // Remove automation indicators
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
            
            // Override chrome
            window.chrome = {
                runtime: {},
            };
            
            // Mock WebGL vendor
            const getParameterOriginal = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(parameter) {
                if (parameter === 37445) {
                    return 'Intel Inc.';
                }
                if (parameter === 37446) {
                    return 'Intel Iris OpenGL Engine';
                }
                return getParameterOriginal.apply(this, arguments);
            };
        }
        """
        
        await context.add_init_script(stealth_js)
    
    async def get_context(
        self,
        context_id: str = "default",
        fresh: bool = False,
        domain: Optional[str] = None
    ) -> BrowserContext:
        """
        Get or create a browser context.
        
        Args:
            context_id: Unique identifier for the context
            fresh: Force create a new context
            domain: Target domain for proxy selection
        
        Returns:
            BrowserContext
        """
        async with self._lock:
            # Return existing context if available
            if not fresh and context_id in self._contexts:
                return self._contexts[context_id]
            
            # Close existing context if creating fresh
            if context_id in self._contexts:
                await self._contexts[context_id].close()
                del self._contexts[context_id]
            
            # Get proxy if enabled
            proxy = None
            if self._proxy_rotator:
                proxy = await self._proxy_rotator.get_proxy_for_playwright(domain)
            
            return await self._create_context(context_id, proxy=proxy)
    
    @asynccontextmanager
    async def get_page(
        self,
        context_id: str = "default",
        fresh_context: bool = False,
        domain: Optional[str] = None
    ):
        """
        Context manager for getting a page.
        
        Usage:
            async with browser_manager.get_page("my-context") as page:
                await page.goto("https://example.com")
        
        Args:
            context_id: Context identifier
            fresh_context: Create a new context
            domain: Target domain
        
        Yields:
            Page instance
        """
        if not self._initialized:
            await self.initialize()
        
        context = await self.get_context(context_id, fresh_context, domain)
        page = await context.new_page()
        
        try:
            # Set default timeouts
            page.set_default_timeout(settings.REQUEST_TIMEOUT)
            page.set_default_navigation_timeout(settings.PAGE_LOAD_TIMEOUT)
            
            yield page
            
        finally:
            try:
                await page.close()
            except Exception as e:
                logger.warning(f"Error closing page: {e}")
    
    async def close_context(self, context_id: str) -> None:
        """Close a specific browser context."""
        async with self._lock:
            if context_id in self._contexts:
                try:
                    await self._contexts[context_id].close()
                    del self._contexts[context_id]
                    logger.debug(f"Closed context: {context_id}")
                except Exception as e:
                    logger.warning(f"Error closing context {context_id}: {e}")
    
    async def clear_cookies(self, context_id: str) -> None:
        """Clear cookies for a context."""
        if context_id in self._contexts:
            await self._contexts[context_id].clear_cookies()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get browser manager statistics."""
        return {
            "initialized": self._initialized,
            "browser_type": self.config.browser_type,
            "headless": self.config.headless,
            "active_contexts": len(self._contexts),
            "max_browsers": self.max_browsers,
            "context_ids": list(self._contexts.keys())
        }


# Global browser manager instance
_browser_manager: Optional[BrowserManager] = None


async def get_browser_manager() -> BrowserManager:
    """Get the global browser manager instance."""
    global _browser_manager
    if _browser_manager is None:
        _browser_manager = BrowserManager()
        await _browser_manager.initialize()
    return _browser_manager


async def shutdown_browser_manager() -> None:
    """Shutdown the global browser manager."""
    global _browser_manager
    if _browser_manager:
        await _browser_manager.shutdown()
        _browser_manager = None