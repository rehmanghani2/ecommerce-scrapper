# backend/app/scrapers/base_scraper.py
from abc import ABC, abstractmethod
from playwright.async_api import Page, ElementHandle
from typing import List, Dict, Any, Optional, Callable
import asyncio
from datetime import datetime
from dataclasses import dataclass, field

from app.utils.rate_limiter import AdaptiveRateLimiter
from app.utils.browser_manager import BrowserManager
from app.schemas.scraper_schema import ScraperConfig, SelectorConfig
from app.core.data_cleaner import DataCleaner

@dataclass
class ScrapingResult:
    """Result of a scraping operation"""
    success: bool
    products: List[Dict[str, Any]] = field(default_factory=list)
    total_pages: int = 0
    scraped_pages: int = 0
    errors: List[str] = field(default_factory=list)
    screenshots: List[str] = field(default_factory=list)
    duration: float = 0.0

@dataclass
class PageData:
    """Data from a single page"""
    url: str
    page_number: int
    products: List[Dict[str, Any]]
    has_next_page: bool
    next_page_url: Optional[str] = None

class BaseScraper(ABC):
    """Base class for all e-commerce scrapers"""
    
    # Platform identifier
    PLATFORM_NAME: str = "generic"
    
    # Common patterns for product detection
    PRODUCT_PATTERNS = {
        "container": [
            "[data-component-type='s-search-result']",  # Amazon
            ".s-item",  # eBay
            ".product-card",
            ".product-item",
            ".product-tile",
            ".product",
            "[data-product]",
            "[data-product-id]",
            ".grid-item",
            ".collection-product",
            ".product-grid-item",
            "article.product",
            ".product-container",
            ".item-card",
        ],
        "name": [
            "h1", "h2", "h3", "h4",
            ".product-title", ".product-name",
            "[data-product-title]",
            ".item-title", ".title",
            "a.title", ".name",
        ],
        "price": [
            ".price", ".product-price",
            "[data-price]", ".current-price",
            ".sale-price", ".final-price",
            ".amount", ".money",
            "span.price", ".price-current",
        ],
        "image": [
            "img.product-image", "img.primary-image",
            ".product-image img", "img[data-src]",
            ".image img", "picture img",
            "img.lazy", ".product-img img",
        ],
    }
    
    def __init__(
        self,
        config: ScraperConfig,
        selectors: Optional[SelectorConfig] = None,
        progress_callback: Optional[Callable] = None
    ):
        self.config = config
        self.selectors = selectors
        self.progress_callback = progress_callback
        self.rate_limiter = AdaptiveRateLimiter(base_delay=config.delay_range[0])
        self.data_cleaner = DataCleaner()
        self._current_page = 0
        self._total_products = 0
    
    async def report_progress(self, message: str, **kwargs):
        """Report progress to callback if available"""
        if self.progress_callback:
            await self.progress_callback({
                "message": message,
                "current_page": self._current_page,
                "total_products": self._total_products,
                **kwargs
            })
    
    @abstractmethod
    async def detect_products(self, page: Page) -> List[ElementHandle]:
        """Detect product elements on the page"""
        pass
    
    @abstractmethod
    async def extract_product_data(
        self, 
        element: ElementHandle, 
        page: Page
    ) -> Dict[str, Any]:
        """Extract data from a single product element"""
        pass
    
    @abstractmethod
    async def get_next_page(self, page: Page) -> Optional[str]:
        """Get the next page URL or navigate to next page"""
        pass
    
    async def scrape(self, url: str) -> ScrapingResult:
        """Main scraping method"""
        start_time = datetime.now()
        result = ScrapingResult(success=False)
        
        try:
            async with BrowserManager.get_page(
                browser_type=self.config.browser_type.value
            ) as page:
                await self.report_progress(f"Navigating to {url}")
                
                # Navigate to the URL
                response = await page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=self.config.timeout
                )
                
                if not response or response.status >= 400:
                    result.errors.append(f"Failed to load page: {response.status if response else 'No response'}")
                    return result
                
                # Wait for content to load
                await self._wait_for_content(page)
                
                # Scrape pages
                current_url = url
                page_number = 1
                
                while page_number <= self.config.max_pages:
                    self._current_page = page_number
                    await self.report_progress(
                        f"Scraping page {page_number}",
                        current_url=current_url
                    )
                    
                    # Take screenshot if enabled
                    if self.config.take_screenshots:
                        screenshot_path = f"screenshots/page_{page_number}.png"
                        await page.screenshot(path=screenshot_path, full_page=True)
                        result.screenshots.append(screenshot_path)
                    
                    # Extract products from current page
                    page_data = await self._scrape_page(page, page_number)
                    result.products.extend(page_data.products)
                    self._total_products = len(result.products)
                    
                    await self.report_progress(
                        f"Found {len(page_data.products)} products on page {page_number}",
                        products_found=len(page_data.products)
                    )
                    
                    result.scraped_pages = page_number
                    
                    # Check for next page
                    if not self.config.enable_pagination or not page_data.has_next_page:
                        break
                    
                    # Navigate to next page
                    next_url = await self.get_next_page(page)
                    if not next_url:
                        break
                    
                    # Rate limiting
                    await self.rate_limiter.wait()
                    
                    if next_url != current_url:
                        await page.goto(next_url, wait_until="domcontentloaded")
                        current_url = next_url
                    
                    await self._wait_for_content(page)
                    page_number += 1
                    self.rate_limiter.on_success()
                
                result.success = True
                result.total_pages = page_number
                
        except Exception as e:
            result.errors.append(str(e))
            self.rate_limiter.on_error()
        
        result.duration = (datetime.now() - start_time).total_seconds()
        return result
    
    async def _wait_for_content(self, page: Page):
        """Wait for page content to load"""
        try:
            # Wait for network to be idle
            await page.wait_for_load_state("networkidle", timeout=10000)
        except:
            pass
        
        # Additional wait if selector specified
        if self.config.wait_for_selector:
            try:
                await page.wait_for_selector(
                    self.config.wait_for_selector,
                    timeout=self.config.timeout
                )
            except:
                pass
        
        # Random delay to appear human-like
        if self.config.random_delay:
            delay = self.rate_limiter.current_delay
            await asyncio.sleep(delay)
    
    async def _scrape_page(self, page: Page, page_number: int) -> PageData:
        """Scrape a single page"""
        products = []
        
        # Detect product elements
        elements = await self.detect_products(page)
        
        for element in elements:
            try:
                product_data = await self.extract_product_data(element, page)
                if product_data and product_data.get("name"):
                    product_data["page_number"] = page_number
                    product_data["scraped_at"] = datetime.utcnow().isoformat()
                    
                    # Clean the data
                    cleaned_data = self.data_cleaner.clean_product(product_data)
                    products.append(cleaned_data)
            except Exception as e:
                continue
        
        # Check if there's a next page
        has_next = await self._has_next_page(page)
        
        return PageData(
            url=page.url,
            page_number=page_number,
            products=products,
            has_next_page=has_next
        )
    
    async def _has_next_page(self, page: Page) -> bool:
        """Check if there's a next page"""
        next_selectors = [
            "a.next", ".next-page", "[aria-label='Next']",
            ".pagination-next", "a[rel='next']",
            "button.next", ".pager-next",
            "[data-testid='pagination-next']",
        ]
        
        for selector in next_selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    is_disabled = await element.get_attribute("disabled")
                    aria_disabled = await element.get_attribute("aria-disabled")
                    if not is_disabled and aria_disabled != "true":
                        return True
            except:
                continue
        
        return False
    
    # Helper methods for extracting data
    async def _get_text(
        self, 
        element: ElementHandle, 
        selector: str,
        default: str = ""
    ) -> str:
        """Get text content from an element"""
        try:
            target = await element.query_selector(selector)
            if target:
                text = await target.inner_text()
                return text.strip() if text else default
        except:
            pass
        return default
    
    async def _get_attribute(
        self,
        element: ElementHandle,
        selector: str,
        attribute: str,
        default: str = ""
    ) -> str:
        """Get attribute value from an element"""
        try:
            target = await element.query_selector(selector)
            if target:
                value = await target.get_attribute(attribute)
                return value.strip() if value else default
        except:
            pass
        return default
    
    async def _get_all_text(
        self,
        element: ElementHandle,
        selector: str
    ) -> List[str]:
        """Get all text content from matching elements"""
        texts = []
        try:
            targets = await element.query_selector_all(selector)
            for target in targets:
                text = await target.inner_text()
                if text:
                    texts.append(text.strip())
        except:
            pass
        return texts
    
    async def _get_all_attributes(
        self,
        element: ElementHandle,
        selector: str,
        attribute: str
    ) -> List[str]:
        """Get all attribute values from matching elements"""
        values = []
        try:
            targets = await element.query_selector_all(selector)
            for target in targets:
                value = await target.get_attribute(attribute)
                if value:
                    values.append(value.strip())
        except:
            pass
        return values