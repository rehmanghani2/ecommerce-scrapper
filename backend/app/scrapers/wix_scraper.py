"""
Wix eCommerce Scraper Module
Specialized scraper for Wix Stores.
Supports standard Wix data-hook selectors and JSON-LD schema.
"""

from playwright.async_api import Page, ElementHandle
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin
import re
import json
import logging

from app.scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class WixScraper(BaseScraper):
    """Specialized scraper for Wix eCommerce stores."""

    PLATFORM_NAME = "wix"
    PLATFORM_DOMAINS = ["wixsite.com", "wix.com"]

    SELECTORS = {
        "product_container": [
            "[data-hook='product-item-root']",
            "li[data-hook='product-list-item']",
            "div[data-hook='product-item']",
            "[data-hook='product-widget-item']",
            ".product-item",
            "li.product-list-item",
        ],
        "name": [
            "[data-hook='product-item-name']",
            "h3[data-hook='product-item-name']",
            "[data-hook='product-title']",
            "h2.product-title",
            "h3.product-title",
            ".product-title",
        ],
        "price": [
            "[data-hook='product-item-price-to-pay']",
            "span[data-hook='product-item-price']",
            "[data-hook='formatted-primary-price']",
            ".product-price",
            ".price",
        ],
        "original_price": [
            "[data-hook='product-item-price-before-discount']",
            "[data-hook='formatted-strike-through-price']",
            "del[data-hook='product-item-price']",
            "del",
        ],
        "image": [
            "[data-hook='product-item-images'] img",
            "img[data-hook='product-item-image']",
            "[data-hook='product-image'] img",
            "img",
        ],
        "link": [
            "a[data-hook='product-item-container']",
            "a[data-hook='item-link']",
            "a[data-hook='product-item-name']",
            "a",
        ],
        "next_page": [
            "[data-hook='pagination-next']",
            "a[data-hook='next-page']",
            "button[data-hook='load-more-button']",
            "a[rel='next']",
            ".pagination .next",
        ],
    }

    async def detect_products(self, page: Page) -> List[ElementHandle]:
        """Detect Wix product cards on the page."""
        for selector in self.SELECTORS["product_container"]:
            try:
                await page.wait_for_selector(selector, timeout=5000)
                products = await page.query_selector_all(selector)
                if len(products) >= 1:
                    return products
            except Exception:
                continue

        # Fallback to general container patterns
        for pattern in self.PRODUCT_PATTERNS["container"]:
            try:
                elements = await page.query_selector_all(pattern)
                if len(elements) >= 2:
                    return elements
            except Exception:
                continue

        return []

    async def extract_product_data(
        self,
        element: ElementHandle,
        page: Page
    ) -> Dict[str, Any]:
        """Extract product data from a Wix card element."""
        data = {
            "platform": "wix",
        }
        base_url = page.url

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
                    try:
                        data["price"] = float(match.group())
                        data["price_text"] = price_text
                        break
                    except ValueError:
                        pass

        # Original Price
        for selector in self.SELECTORS["original_price"]:
            orig_text = await self._get_text(element, selector)
            if orig_text:
                match = re.search(r'[\d,]+\.?\d*', orig_text.replace(",", ""))
                if match:
                    try:
                        val = float(match.group())
                        if "price" in data and val > data["price"]:
                            data["original_price"] = val
                            data["on_sale"] = True
                            break
                    except ValueError:
                        pass

        # Image
        for selector in self.SELECTORS["image"]:
            img = await element.query_selector(selector)
            if img:
                src = (
                    await img.get_attribute("src")
                    or await img.get_attribute("data-src")
                )
                if src:
                    # Clean Wix media CDN URL
                    if src.startswith("//"):
                        src = "https:" + src
                    data["image_url"] = src.split("?")[0]
                    break

        # Product URL
        for selector in self.SELECTORS["link"]:
            link = await element.query_selector(selector)
            if link:
                href = await link.get_attribute("href")
                if href and href != "#":
                    data["product_url"] = urljoin(base_url, href)
                    break

        data["availability"] = "In Stock"
        return data

    async def get_next_page(self, page: Page) -> Optional[str]:
        """Get next page URL or handle Wix pagination."""
        for selector in self.SELECTORS["next_page"]:
            try:
                next_btn = await page.query_selector(selector)
                if next_btn:
                    href = await next_btn.get_attribute("href")
                    if href:
                        return urljoin(page.url, href)
            except Exception:
                continue

        # Check URL parameter pagination: ?page=2
        current_url = page.url
        if "page=" in current_url:
            match = re.search(r'page=(\d+)', current_url)
            if match:
                current_page = int(match.group(1))
                return re.sub(r'page=\d+', f'page={current_page + 1}', current_url)
        else:
            sep = "&" if "?" in current_url else "?"
            return f"{current_url}{sep}page=2"

        return None
