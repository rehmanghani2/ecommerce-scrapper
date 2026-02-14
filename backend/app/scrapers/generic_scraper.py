# backend/app/scrapers/generic_scraper.py
from playwright.async_api import Page, ElementHandle
from typing import List, Dict, Any, Optional
import re
from urllib.parse import urljoin

from app.scrapers.base_scraper import BaseScraper
from app.core.pattern_detector import PatternDetector
from app.schemas.scraper_schema import ScraperConfig, SelectorConfig

class GenericScraper(BaseScraper):
    """Generic scraper that auto-detects product patterns"""
    
    PLATFORM_NAME = "generic"
    
    def __init__(
        self,
        config: ScraperConfig,
        selectors: Optional[SelectorConfig] = None,
        progress_callback = None
    ):
        super().__init__(config, selectors, progress_callback)
        self.pattern_detector = PatternDetector()
        self.detected_pattern = None
        self.base_url = ""
    
    async def detect_products(self, page: Page) -> List[ElementHandle]:
        """Detect product elements using pattern detection or provided selectors"""
        self.base_url = page.url
        
        # If custom selectors provided, use them
        if self.selectors and self.selectors.product_container:
            return await page.query_selector_all(self.selectors.product_container)
        
        # Auto-detect pattern if not already detected
        if not self.detected_pattern:
            await self.report_progress("Auto-detecting product patterns...")
            self.detected_pattern = await self.pattern_detector.detect(page)
            await self.report_progress(
                f"Detected pattern with {self.detected_pattern.confidence:.0%} confidence",
                detected_selector=self.detected_pattern.product_selector
            )
        
        return await page.query_selector_all(self.detected_pattern.product_selector)
    
    async def extract_product_data(
        self, 
        element: ElementHandle, 
        page: Page
    ) -> Dict[str, Any]:
        """Extract product data from element"""
        data = {}
        
        # Use custom selectors if provided
        if self.selectors:
            data = await self._extract_with_selectors(element, page)
        elif self.detected_pattern:
            data = await self._extract_with_pattern(element, page)
        
        return data
    
    async def _extract_with_selectors(
        self, 
        element: ElementHandle, 
        page: Page
    ) -> Dict[str, Any]:
        """Extract using custom selectors"""
        s = self.selectors
        data = {}
        
        if s.name:
            data["name"] = await self._get_text(element, s.name)
        
        if s.price:
            price_text = await self._get_text(element, s.price)
            data["price"] = self._parse_price(price_text)
            data["price_raw"] = price_text
        
        if s.original_price:
            original_text = await self._get_text(element, s.original_price)
            data["original_price"] = self._parse_price(original_text)
        
        if s.image:
            data["image_url"] = await self._get_image_url(element, s.image)
        
        if s.description:
            data["description"] = await self._get_text(element, s.description)
        
        if s.rating:
            rating_text = await self._get_text(element, s.rating)
            data["rating"] = self._parse_rating(rating_text)
        
        if s.reviews:
            reviews_text = await self._get_text(element, s.reviews)
            data["reviews_count"] = self._parse_number(reviews_text)
        
        if s.availability:
            data["availability"] = await self._get_text(element, s.availability)
        
        if s.brand:
            data["brand"] = await self._get_text(element, s.brand)
        
        if s.link:
            data["product_url"] = await self._get_product_url(element, s.link)
        
        return data
    
    async def _extract_with_pattern(
        self, 
        element: ElementHandle, 
        page: Page
    ) -> Dict[str, Any]:
        """Extract using auto-detected pattern"""
        selectors = self.detected_pattern.field_selectors
        data = {}
        
        # Name
        if "name" in selectors:
            data["name"] = await self._get_text(element, selectors["name"])
        else:
            # Fallback: try common patterns
            for sel in ["h2", "h3", "h4", ".title", ".name"]:
                text = await self._get_text(element, sel)
                if text:
                    data["name"] = text
                    break
        
        # Price
        if "price" in selectors:
            price_text = await self._get_text(element, selectors["price"])
            data["price"] = self._parse_price(price_text)
            data["price_raw"] = price_text
        
        # Original price
        if "original_price" in selectors:
            original_text = await self._get_text(element, selectors["original_price"])
            data["original_price"] = self._parse_price(original_text)
        
        # Image
        if "image" in selectors:
            data["image_url"] = await self._get_image_url(element, selectors["image"])
        else:
            data["image_url"] = await self._get_image_url(element, "img")
        
        # Link
        if "link" in selectors:
            data["product_url"] = await self._get_product_url(element, selectors["link"])
        else:
            data["product_url"] = await self._get_product_url(element, "a")
        
        # Rating
        if "rating" in selectors:
            rating_elem = await element.query_selector(selectors["rating"])
            if rating_elem:
                rating_text = await rating_elem.get_attribute("aria-label") or \
                              await rating_elem.get_attribute("title") or \
                              await rating_elem.inner_text()
                data["rating"] = self._parse_rating(rating_text)
        
        # Reviews count
        if "reviews" in selectors:
            reviews_text = await self._get_text(element, selectors["reviews"])
            data["reviews_count"] = self._parse_number(reviews_text)
        
        # Description
        if "description" in selectors:
            data["description"] = await self._get_text(element, selectors["description"])
        
        # Brand
        if "brand" in selectors:
            data["brand"] = await self._get_text(element, selectors["brand"])
        
        # Availability
        if "availability" in selectors:
            data["availability"] = await self._get_text(element, selectors["availability"])
        
        # Get all images
        data["images"] = await self._get_all_images(element)
        
        return data
    
    async def _get_image_url(self, element: ElementHandle, selector: str) -> Optional[str]:
        """Get image URL from element"""
        try:
            img = await element.query_selector(selector)
            if img:
                # Try different attributes
                for attr in ["src", "data-src", "data-lazy-src", "data-original"]:
                    url = await img.get_attribute(attr)
                    if url and not url.startswith("data:"):
                        return urljoin(self.base_url, url)
                
                # Try srcset
                srcset = await img.get_attribute("srcset")
                if srcset:
                    first_src = srcset.split(",")[0].split()[0]
                    return urljoin(self.base_url, first_src)
        except:
            pass
        return None
    
    async def _get_all_images(self, element: ElementHandle) -> List[str]:
        """Get all image URLs from element"""
        images = []
        try:
            img_elements = await element.query_selector_all("img")
            for img in img_elements:
                src = await img.get_attribute("src") or await img.get_attribute("data-src")
                if src and not src.startswith("data:"):
                    full_url = urljoin(self.base_url, src)
                    if full_url not in images:
                        images.append(full_url)
        except:
            pass
        return images
    
    async def _get_product_url(self, element: ElementHandle, selector: str) -> Optional[str]:
        """Get product URL from element"""
        try:
            link = await element.query_selector(selector)
            if link:
                href = await link.get_attribute("href")
                if href:
                    return urljoin(self.base_url, href)
        except:
            pass
        return None
    
    async def get_next_page(self, page: Page) -> Optional[str]:
        """Get next page URL"""
        # Common next page selectors
        next_selectors = [
            "a.next",
            ".pagination-next a",
            "a[rel='next']",
            "[aria-label='Next']",
            "[aria-label='Next page']",
            ".pager-next a",
            "a.pagination__next",
            ".next-page a",
            "button.next",
            "[data-testid='pagination-next']",
            "a:has-text('Next')",
            "a:has-text('›')",
            "a:has-text('»')",
        ]
        
        for selector in next_selectors:
            try:
                next_button = await page.query_selector(selector)
                if next_button:
                    # Check if disabled
                    is_disabled = await next_button.get_attribute("disabled")
                    aria_disabled = await next_button.get_attribute("aria-disabled")
                    class_name = await next_button.get_attribute("class") or ""
                    
                    if is_disabled or aria_disabled == "true" or "disabled" in class_name:
                        continue
                    
                    # Try to get href
                    href = await next_button.get_attribute("href")
                    if href and href != "#":
                        return urljoin(page.url, href)
                    
                    # Click the button for pagination
                    if self.config.pagination_type == "click":
                        await next_button.click()
                        await page.wait_for_load_state("networkidle", timeout=10000)
                        return page.url
                        
            except Exception:
                continue
        
        # Try infinite scroll
        if self.config.pagination_type == "scroll":
            return await self._handle_infinite_scroll(page)
        
        return None
    
    async def _handle_infinite_scroll(self, page: Page) -> Optional[str]:
        """Handle infinite scroll pagination"""
        # Get initial product count
        initial_count = len(await self.detect_products(page))
        
        # Scroll to bottom
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(2000)
        
        # Check if new products loaded
        new_count = len(await self.detect_products(page))
        
        if new_count > initial_count:
            return page.url  # Same URL but new content
        
        return None
    
    def _parse_price(self, text: str) -> Optional[float]:
        """Parse price from text"""
        if not text:
            return None
        
        # Remove currency symbols and whitespace
        clean = re.sub(r'[^\d.,]', '', text)
        
        # Handle different formats
        if ',' in clean and '.' in clean:
            # Determine format (1,234.56 vs 1.234,56)
            if clean.rfind(',') > clean.rfind('.'):
                clean = clean.replace('.', '').replace(',', '.')
            else:
                clean = clean.replace(',', '')
        elif ',' in clean:
            # Could be 1,234 or 1,50
            if len(clean.split(',')[-1]) == 2:
                clean = clean.replace(',', '.')
            else:
                clean = clean.replace(',', '')
        
        try:
            return float(clean)
        except:
            return None
    
    def _parse_rating(self, text: str) -> Optional[float]:
        """Parse rating from text"""
        if not text:
            return None
        
        # Try common patterns
        patterns = [
            r'(\d+\.?\d*)\s*(?:out of|\/)\s*5',
            r'(\d+\.?\d*)\s*stars?',
            r'rating[:\s]*(\d+\.?\d*)',
            r'(\d+\.?\d*)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    rating = float(match.group(1))
                    if 0 <= rating <= 5:
                        return rating
                except:
                    continue
        
        return None
    
    def _parse_number(self, text: str) -> Optional[int]:
        """Parse number from text"""
        if not text:
            return None
        
        # Extract numbers
        numbers = re.findall(r'[\d,]+', text)
        if numbers:
            try:
                return int(numbers[0].replace(',', ''))
            except:
                pass
        
        return None