# backend/app/scrapers/amazon_scraper.py
from playwright.async_api import Page, ElementHandle
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin
import re

from app.scrapers.base_scraper import BaseScraper

class AmazonScraper(BaseScraper):
    """Specialized scraper for Amazon"""
    
    PLATFORM_NAME = "amazon"
    
    # Amazon-specific selectors
    SELECTORS = {
        "product_container": "[data-component-type='s-search-result']",
        "name": "h2 a span",
        "price_whole": ".a-price-whole",
        "price_fraction": ".a-price-fraction",
        "price_symbol": ".a-price-symbol",
        "original_price": ".a-text-price .a-offscreen",
        "image": ".s-image",
        "rating": ".a-icon-star-small .a-icon-alt",
        "reviews": ".a-size-base.s-underline-text",
        "link": "h2 a",
        "prime": ".s-prime",
        "sponsored": ".s-label-popover-default",
        "brand": ".a-size-base-plus.a-color-base",
        "delivery": ".a-color-base.a-text-bold",
    }
    
    async def detect_products(self, page: Page) -> List[ElementHandle]:
        """Detect Amazon product elements"""
        await page.wait_for_selector(
            self.SELECTORS["product_container"],
            timeout=self.config.timeout
        )
        
        products = await page.query_selector_all(self.SELECTORS["product_container"])
        
        # Filter out sponsored ads if needed
        filtered_products = []
        for product in products:
            # Check if it's a valid product (has ASIN)
            asin = await product.get_attribute("data-asin")
            if asin:
                filtered_products.append(product)
        
        return filtered_products
    
    async def extract_product_data(
        self, 
        element: ElementHandle, 
        page: Page
    ) -> Dict[str, Any]:
        """Extract Amazon product data"""
        data = {}
        base_url = "https://www.amazon.com"
        
        # ASIN (Amazon Standard Identification Number)
        data["asin"] = await element.get_attribute("data-asin")
        data["sku"] = data["asin"]
        
        # Product name
        data["name"] = await self._get_text(element, self.SELECTORS["name"])
        
        # Price
        price_whole = await self._get_text(element, self.SELECTORS["price_whole"])
        price_fraction = await self._get_text(element, self.SELECTORS["price_fraction"])
        
        if price_whole:
            price_str = price_whole.replace(",", "")
            if price_fraction:
                price_str += "." + price_fraction
            try:
                data["price"] = float(price_str)
            except:
                data["price"] = None
        
        # Original price
        original_price_text = await self._get_text(
            element, 
            self.SELECTORS["original_price"]
        )
        if original_price_text:
            match = re.search(r'[\d,]+\.?\d*', original_price_text)
            if match:
                try:
                    data["original_price"] = float(match.group().replace(",", ""))
                except:
                    pass
        
        # Calculate discount
        if data.get("price") and data.get("original_price"):
            discount = (1 - data["price"] / data["original_price"]) * 100
            data["discount_percentage"] = round(discount, 1)
        
        # Image
        img = await element.query_selector(self.SELECTORS["image"])
        if img:
            data["image_url"] = await img.get_attribute("src")
            # Get high-res image URL
            srcset = await img.get_attribute("srcset")
            if srcset:
                # Get the largest image from srcset
                images = srcset.split(",")
                if images:
                    data["image_url_hd"] = images[-1].strip().split(" ")[0]
        
        # Rating
        rating_text = await self._get_text(element, self.SELECTORS["rating"])
        if rating_text:
            match = re.search(r'([\d.]+)\s*out of', rating_text)
            if match:
                try:
                    data["rating"] = float(match.group(1))
                except:
                    pass
        
        # Reviews count
        reviews_text = await self._get_text(element, self.SELECTORS["reviews"])
        if reviews_text:
            reviews_clean = reviews_text.replace(",", "").replace("(", "").replace(")", "")
            match = re.search(r'(\d+)', reviews_clean)
            if match:
                try:
                    data["reviews_count"] = int(match.group(1))
                except:
                    pass
        
        # Product URL
        link = await element.query_selector(self.SELECTORS["link"])
        if link:
            href = await link.get_attribute("href")
            if href:
                data["product_url"] = urljoin(base_url, href)
        
        # Prime eligibility
        prime = await element.query_selector(self.SELECTORS["prime"])
        data["prime"] = prime is not None
        
        # Sponsored
        sponsored = await element.query_selector(self.SELECTORS["sponsored"])
        data["sponsored"] = sponsored is not None
        
        # Brand (if available)
        brand_text = await self._get_text(element, self.SELECTORS["brand"])
        if brand_text:
            data["brand"] = brand_text
        
        # Delivery info
        delivery = await self._get_text(element, self.SELECTORS["delivery"])
        if delivery:
            data["delivery_info"] = delivery
        
        # Availability (check for "In Stock" or similar)
        data["availability"] = "In Stock"  # Default for search results
        
        data["currency"] = "USD"
        data["platform"] = "amazon"
        
        return data
    
    async def get_next_page(self, page: Page) -> Optional[str]:
        """Navigate to next Amazon page"""
        next_selectors = [
            ".s-pagination-next",
            "a.s-pagination-next",
            "[aria-label='Go to next page']",
        ]
        
        for selector in next_selectors:
            try:
                next_button = await page.query_selector(selector)
                if next_button:
                    # Check if disabled
                    is_disabled = await next_button.get_attribute("aria-disabled")
                    class_attr = await next_button.get_attribute("class") or ""
                    
                    if is_disabled == "true" or "disabled" in class_attr:
                        return None
                    
                    href = await next_button.get_attribute("href")
                    if href:
                        return urljoin(page.url, href)
            except:
                continue
        
        return None

    @staticmethod
    def is_amazon_url(url: str) -> bool:
        """Check if URL is from Amazon"""
        amazon_domains = [
            "amazon.com", "amazon.co.uk", "amazon.de",
            "amazon.fr", "amazon.it", "amazon.es",
            "amazon.ca", "amazon.com.au", "amazon.in",
            "amazon.co.jp", "amazon.com.br", "amazon.com.mx",
        ]
        return any(domain in url.lower() for domain in amazon_domains)