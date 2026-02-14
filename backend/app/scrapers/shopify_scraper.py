# backend/app/scrapers/shopify_scraper.py
from playwright.async_api import Page, ElementHandle
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, urlparse
import re

from app.scrapers.base_scraper import BaseScraper

class ShopifyScraper(BaseScraper):
    """Specialized scraper for Shopify stores"""
    
    PLATFORM_NAME = "shopify"
    
    # Common Shopify theme selectors
    SELECTORS = {
        "product_container": [
            ".product-card",
            ".grid-product",
            ".product-item",
            ".collection-product",
            ".product",
            "[data-product-card]",
            ".product-block",
        ],
        "name": [
            ".product-card__title",
            ".product-item__title", 
            ".product__title",
            ".grid-product__title",
            "h2 a", "h3 a",
            ".title",
        ],
        "price": [
            ".product-card__price",
            ".product-item__price",
            ".product__price",
            ".price",
            "[data-product-price]",
            ".money",
        ],
        "original_price": [
            ".product-card__price--compare",
            ".compare-price",
            ".was-price",
            "del", "s",
        ],
        "image": [
            ".product-card__image img",
            ".product-item__image img",
            ".product__image img",
            "img.lazyload",
            "img",
        ],
        "link": [
            ".product-card__link",
            ".product-item__link",
            "a.product-link",
            "a",
        ],
        "vendor": [
            ".product-card__vendor",
            ".vendor",
            ".product__vendor",
        ],
        "badge": [
            ".product-card__badge",
            ".badge",
            ".product-badge",
        ],
    }
    
    async def detect_products(self, page: Page) -> List[ElementHandle]:
        """Detect Shopify product elements"""
        # Try to get products from Shopify's JSON API first
        products_from_json = await self._try_json_api(page)
        if products_from_json:
            return products_from_json
        
        # Fallback to DOM scraping
        for selector in self.SELECTORS["product_container"]:
            try:
                await page.wait_for_selector(selector, timeout=5000)
                products = await page.query_selector_all(selector)
                print("products ", products)
                if len(products) >= 2:
                    return products
            except:
                continue
        
        return []
    
    async def _try_json_api(self, page: Page) -> Optional[List]:
        """Try to get products from Shopify's JSON endpoint"""
        try:
            # Check if products.json is accessible
            current_url = page.url
            parsed = urlparse(current_url)
            
            # Try collection JSON endpoint
            if "/collections/" in current_url:
                json_url = current_url.split("?")[0]
                if not json_url.endswith(".json"):
                    json_url += "/products.json"
                
                response = await page.request.get(json_url)
                if response.ok:
                    data = await response.json()
                    if "products" in data:
                        # Store JSON data for extraction
                        self._json_products = data["products"]
                        return self._json_products
        except:
            pass
        
        return None
    
    async def extract_product_data(
        self, 
        element, 
        page: Page
    ) -> Dict[str, Any]:
        """Extract Shopify product data"""
        # Check if we have JSON data
        if hasattr(self, '_json_products') and isinstance(element, dict):
            return self._extract_from_json(element)
        
        # Extract from DOM
        return await self._extract_from_dom(element, page)
    
    def _extract_from_json(self, product: Dict) -> Dict[str, Any]:
        """Extract product data from Shopify JSON"""
        data = {
            "name": product.get("title"),
            "description": product.get("body_html", "").strip(),
            "brand": product.get("vendor"),
            "product_type": product.get("product_type"),
            "tags": product.get("tags", []),
            "created_at": product.get("created_at"),
            "updated_at": product.get("updated_at"),
            "platform": "shopify",
        }
        
        # Get handle for URL
        handle = product.get("handle")
        if handle:
            data["handle"] = handle
        
        # Get first variant for price
        variants = product.get("variants", [])
        if variants:
            first_variant = variants[0]
            
            price = first_variant.get("price")
            if price:
                data["price"] = float(price)
            
            compare_price = first_variant.get("compare_at_price")
            if compare_price:
                data["original_price"] = float(compare_price)
            
            data["sku"] = first_variant.get("sku")
            data["inventory_quantity"] = first_variant.get("inventory_quantity")
            
            if first_variant.get("available"):
                data["availability"] = "In Stock"
            else:
                data["availability"] = "Out of Stock"
        
        # Get all variants
        data["variants"] = [
            {
                "id": v.get("id"),
                "title": v.get("title"),
                "price": float(v.get("price", 0)),
                "sku": v.get("sku"),
                "available": v.get("available", False),
            }
            for v in variants
        ]
        
        # Get images
        images = product.get("images", [])
        if images:
            data["image_url"] = images[0].get("src")
            data["images"] = [img.get("src") for img in images]
        
        return data
    
    async def _extract_from_dom(
        self, 
        element: ElementHandle, 
        page: Page
    ) -> Dict[str, Any]:
        """Extract product data from DOM"""
        data = {}
        base_url = page.url.split("/collections")[0] if "/collections" in page.url else page.url
        
        # Name
        for selector in self.SELECTORS["name"]:
            name = await self._get_text(element, selector)
            if name:
                data["name"] = name
                break
        
        # Price
        for selector in self.SELECTORS["price"]:
            price_text = await self._get_text(element, selector)
            if price_text:
                match = re.search(r'[\d,]+\.?\d*', price_text.replace(",", ""))
                if match:
                    data["price"] = float(match.group())
                    break
        
        # Original price
        for selector in self.SELECTORS["original_price"]:
            original_text = await self._get_text(element, selector)
            if original_text:
                match = re.search(r'[\d,]+\.?\d*', original_text.replace(",", ""))
                if match:
                    data["original_price"] = float(match.group())
                    break
        
        # Image
        for selector in self.SELECTORS["image"]:
            img = await element.query_selector(selector)
            if img:
                src = await img.get_attribute("src") or \
                      await img.get_attribute("data-src") or \
                      await img.get_attribute("data-srcset")
                if src:
                    # Clean Shopify image URL
                    if src.startswith("//"):
                        src = "https:" + src
                    data["image_url"] = src.split("?")[0]
                    break
        
        # Link
        for selector in self.SELECTORS["link"]:
            link = await element.query_selector(selector)
            if link:
                href = await link.get_attribute("href")
                if href and "/products/" in href:
                    data["product_url"] = urljoin(base_url, href)
                    break
        
        # Vendor/Brand
        for selector in self.SELECTORS["vendor"]:
            vendor = await self._get_text(element, selector)
            if vendor:
                data["brand"] = vendor
                break
        
        # Badge (sale, new, etc.)
        for selector in self.SELECTORS["badge"]:
            badge = await self._get_text(element, selector)
            if badge:
                data["badge"] = badge
                if "sale" in badge.lower():
                    data["on_sale"] = True
                break
        
        data["platform"] = "shopify"
        
        return data
    
    async def get_next_page(self, page: Page) -> Optional[str]:
        """Navigate to next Shopify page"""
        next_selectors = [
            "a.pagination__next",
            ".pagination-next a",
            "a[rel='next']",
            ".next a",
            "a:has-text('Next')",
            "a:has-text('→')",
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
        
        # Try URL-based pagination
        current_url = page.url
        if "page=" in current_url:
            match = re.search(r'page=(\d+)', current_url)
            if match:
                current_page = int(match.group(1))
                return re.sub(r'page=\d+', f'page={current_page + 1}', current_url)
        else:
            separator = "&" if "?" in current_url else "?"
            return f"{current_url}{separator}page=2"
        
        return None

    @staticmethod
    def is_shopify_url(url: str) -> bool:
        """Check if URL is from a Shopify store"""
        # This would need more sophisticated detection
        # Could check for Shopify-specific headers or meta tags
        shopify_indicators = [
            "myshopify.com",
            "/collections/",
            "/products/",
        ]
        return any(indicator in url.lower() for indicator in shopify_indicators)