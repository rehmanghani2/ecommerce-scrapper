"""
Walmart Marketplace Scraper Module
Specialized scraper for Walmart search and category product pages.
"""

from playwright.async_api import Page, ElementHandle
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin
import re
import logging

from app.scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class WalmartScraper(BaseScraper):
    """Specialized scraper for Walmart product listings."""

    PLATFORM_NAME = "walmart"
    PLATFORM_DOMAINS = ["walmart.com"]

    SELECTORS = {
        "product_container": [
            "div[data-item-id]",
            "div[data-testid='item-stack'] > div",
            "div[data-testid='product-card']",
            "div[data-testid='list-view'] > div",
            "div.mb0.ph0-xl.pt0-xl.pb3-m.bb.b--near-white",
            "div.sans-serif.mid-gray.relative.flex.flex-column.w-100",
        ],
        "name": [
            "span[data-automation-id='product-title']",
            "span.w_iUH7",
            "[data-testid='product-title']",
            "a.w-100 span",
            "a[link-identifier] span",
            "h3",
        ],
        "price": [
            "div[data-automation-id='product-price'] .w_iDh7",
            "div[data-automation-id='product-price']",
            "span.w_iDh7",
            "[data-testid='product-price']",
            "span.f2",
            ".price-main .visuallyhidden",
            "span.b.black",
        ],
        "original_price": [
            "span.strike",
            "div[data-automation-id='product-price'] span.w_iDh7 + span",
            "del",
            ".was-price",
        ],
        "image": [
            "img[data-testid='productTileImage']",
            "img[data-automation-id='product-image']",
            "img.absolute",
            "img[loading='lazy']",
            "img",
        ],
        "link": [
            "a[link-identifier]",
            "a[data-automation-id='product-title-link']",
            "a[data-testid='product-link']",
            "a[data-testid='productTileImage']",
            "a",
        ],
        "rating": [
            "span[data-testid='product-ratings']",
            "span.w_iUH7[aria-hidden='true']",
            ".stars-container",
        ],
        "next_page": [
            "a[data-testid='NextPage']",
            "a[aria-label='Next Page']",
            "a[link-identifier='paginationNext']",
            "a[rel='next']",
            ".pagination-next a",
        ],
    }

    async def detect_products(self, page: Page) -> List[ElementHandle]:
        """Detect Walmart product cards on the page."""
        for selector in self.SELECTORS["product_container"]:
            try:
                await page.wait_for_selector(selector, timeout=5000)
                products = await page.query_selector_all(selector)
                if len(products) >= 1:
                    return products
            except Exception:
                continue

        # Fallback general container patterns
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
        """Extract product data from a Walmart product element."""
        data = {
            "platform": "walmart",
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

        # Original / Was Price
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
                    or await img.get_attribute("srcset")
                )
                if src:
                    if src.startswith("//"):
                        src = "https:" + src
                    data["image_url"] = src.split("?")[0]
                    break

        # Link
        for selector in self.SELECTORS["link"]:
            link = await element.query_selector(selector)
            if link:
                href = await link.get_attribute("href")
                if href and href != "#":
                    data["product_url"] = urljoin(base_url, href).split("?")[0]
                    break

        # SKU or Walmart Item ID
        item_id = await element.get_attribute("data-item-id")
        if item_id:
            data["sku"] = item_id

        # Rating
        for selector in self.SELECTORS["rating"]:
            rating_text = await self._get_text(element, selector)
            if rating_text:
                match = re.search(r'([\d.]+)\s*out of 5', rating_text, re.IGNORECASE)
                if match:
                    try:
                        data["rating"] = float(match.group(1))
                        break
                    except ValueError:
                        pass

        data["availability"] = "In Stock"
        return data

    async def get_next_page(self, page: Page) -> Optional[str]:
        """Get next page URL for Walmart pagination."""
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
