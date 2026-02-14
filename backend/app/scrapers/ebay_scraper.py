# backend/app/scrapers/ebay_scraper.py
from playwright.async_api import Page, ElementHandle
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin
import re

from app.scrapers.base_scraper import BaseScraper

class EbayScraper(BaseScraper):
    """Specialized scraper for eBay"""
    
    PLATFORM_NAME = "ebay"
    
    SELECTORS = {
        "product_container": ".s-item",
        "name": ".s-item__title",
        "price": ".s-item__price",
        "original_price": ".s-item__original-price",
        "image": ".s-item__image-img",
        "link": ".s-item__link",
        "shipping": ".s-item__shipping",
        "location": ".s-item__location",
        "seller": ".s-item__seller-info-text",
        "condition": ".SECONDARY_INFO",
        "bids": ".s-item__bids",
        "time_left": ".s-item__time-left",
        "hot": ".s-item__hot-text",
    }
    
    async def detect_products(self, page: Page) -> List[ElementHandle]:
        """Detect eBay product elements"""
        await page.wait_for_selector(
            self.SELECTORS["product_container"],
            timeout=self.config.timeout
        )
        
        products = await page.query_selector_all(self.SELECTORS["product_container"])
        
        # Filter out the "Shop on eBay" header item
        filtered = []
        for product in products:
            title = await self._get_text(product, self.SELECTORS["name"])
            if title and "Shop on eBay" not in title:
                filtered.append(product)
        
        return filtered
    
    async def extract_product_data(
        self, 
        element: ElementHandle, 
        page: Page
    ) -> Dict[str, Any]:
        """Extract eBay product data"""
        data = {}
        base_url = "https://www.ebay.com"
        
        # Product name
        name = await self._get_text(element, self.SELECTORS["name"])
        # Remove "New Listing" prefix
        if name:
            data["name"] = re.sub(r'^New Listing\s*', '', name).strip()
        
        # Price
        price_text = await self._get_text(element, self.SELECTORS["price"])
        if price_text:
            data["price_raw"] = price_text
            
            # Handle price ranges (e.g., "$10.00 to $20.00")
            if " to " in price_text.lower():
                prices = re.findall(r'[\d,]+\.?\d*', price_text)
                if len(prices) >= 2:
                    data["price_min"] = float(prices[0].replace(",", ""))
                    data["price_max"] = float(prices[1].replace(",", ""))
                    data["price"] = data["price_min"]
            else:
                match = re.search(r'[\d,]+\.?\d*', price_text)
                if match:
                    data["price"] = float(match.group().replace(",", ""))
        
        # Original price
        original_text = await self._get_text(element, self.SELECTORS["original_price"])
        if original_text:
            match = re.search(r'[\d,]+\.?\d*', original_text)
            if match:
                data["original_price"] = float(match.group().replace(",", ""))
        
        # Image
        img = await element.query_selector(self.SELECTORS["image"])
        if img:
            data["image_url"] = await img.get_attribute("src")
        
        # Product URL
        link = await element.query_selector(self.SELECTORS["link"])
        if link:
            href = await link.get_attribute("href")
            if href:
                # Clean up URL (remove tracking params)
                data["product_url"] = href.split("?")[0] if "?" in href else href
        
        # Shipping
        shipping = await self._get_text(element, self.SELECTORS["shipping"])
        if shipping:
            data["shipping"] = shipping
            if "free" in shipping.lower():
                data["free_shipping"] = True
            else:
                # Extract shipping cost
                match = re.search(r'\+\s*\$?([\d.]+)', shipping)
                if match:
                    data["shipping_cost"] = float(match.group(1))
        
        # Location
        location = await self._get_text(element, self.SELECTORS["location"])
        if location:
            data["location"] = location.replace("from ", "")
        
        # Condition
        condition = await self._get_text(element, self.SELECTORS["condition"])
        if condition:
            data["condition"] = condition
        
        # Auction specific
        bids = await self._get_text(element, self.SELECTORS["bids"])
        if bids:
            match = re.search(r'(\d+)\s*bid', bids)
            if match:
                data["bids"] = int(match.group(1))
                data["is_auction"] = True
        
        time_left = await self._get_text(element, self.SELECTORS["time_left"])
        if time_left:
            data["time_left"] = time_left
        
        # Hot item
        hot = await element.query_selector(self.SELECTORS["hot"])
        if hot:
            hot_text = await hot.inner_text()
            data["popularity"] = hot_text
        
        data["currency"] = "USD"
        data["platform"] = "ebay"
        
        return data
    
    async def get_next_page(self, page: Page) -> Optional[str]:
        """Navigate to next eBay page"""
        next_selectors = [
            "a.pagination__next",
            "[aria-label='Go to next search page']",
            "a[type='next']",
        ]
        
        for selector in next_selectors:
            try:
                next_button = await page.query_selector(selector)
                if next_button:
                    href = await next_button.get_attribute("href")
                    if href:
                        return urljoin(page.url, href)
            except:
                continue
        
        return None

    @staticmethod
    def is_ebay_url(url: str) -> bool:
        """Check if URL is from eBay"""
        ebay_domains = [
            "ebay.com", "ebay.co.uk", "ebay.de",
            "ebay.fr", "ebay.it", "ebay.es",
            "ebay.ca", "ebay.com.au",
        ]
        return any(domain in url.lower() for domain in ebay_domains)