"""
Squarespace Commerce Scraper Module
Specialized scraper for Squarespace 7.0 and 7.1 stores.
Supports JSON endpoint extraction (?format=json) and DOM fallback.
"""

from playwright.async_api import Page, ElementHandle
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, urlparse
import re
import logging

from app.scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class SquarespaceScraper(BaseScraper):
    """Specialized scraper for Squarespace Commerce stores."""

    PLATFORM_NAME = "squarespace"
    PLATFORM_DOMAINS = ["squarespace.com"]

    SELECTORS = {
        "product_container": [
            ".grid-item",
            ".ProductList-item",
            "article.ProductItem",
            ".product-item",
            "[data-item-id]",
            ".nested-category-children .grid-item",
            ".products-list .product",
        ],
        "name": [
            ".grid-title",
            ".ProductList-title",
            "h1.ProductItem-details-title",
            ".product-title",
            "h2.title a",
            "h3.title a",
            ".title",
        ],
        "price": [
            ".product-price",
            ".sqs-money-native",
            ".ProductList-price",
            ".product-price .sqs-money-native",
            ".price",
        ],
        "original_price": [
            ".original-price",
            ".sqs-money-native-original",
            ".ProductList-price--original",
            "del .sqs-money-native",
            "del",
        ],
        "image": [
            "img.grid-item-image",
            ".ProductList-image img",
            "img[data-src]",
            ".image-wrapper img",
            "img",
        ],
        "link": [
            "a.grid-item-link",
            ".ProductList-item a",
            "a.ProductList-title",
            "a[data-item-id]",
            "a",
        ],
        "next_page": [
            "a.next-page",
            ".ProductList-pagination a.next",
            "a.prev-next-item--next",
            "a[rel='next']",
        ],
    }

    async def detect_products(self, page: Page) -> List[ElementHandle]:
        """Detect Squarespace product items or query Squarespace JSON endpoint."""
        # Try JSON format endpoint first (?format=json)
        json_products = await self._try_json_api(page)
        if json_products:
            return json_products

        # DOM fallback
        for selector in self.SELECTORS["product_container"]:
            try:
                await page.wait_for_selector(selector, timeout=5000)
                products = await page.query_selector_all(selector)
                if len(products) >= 1:
                    return products
            except Exception:
                continue

        for pattern in self.PRODUCT_PATTERNS["container"]:
            try:
                elements = await page.query_selector_all(pattern)
                if len(elements) >= 2:
                    return elements
            except Exception:
                continue

        return []

    async def _try_json_api(self, page: Page) -> Optional[List[Dict[str, Any]]]:
        """Try fetching product collection via Squarespace's ?format=json endpoint."""
        try:
            curr_url = page.url
            if "?" in curr_url:
                json_url = f"{curr_url}&format=json"
            else:
                json_url = f"{curr_url}?format=json"

            resp = await page.request.get(json_url)
            if resp.ok:
                payload = await resp.json()
                items = payload.get("items") or payload.get("upcoming")
                if items and isinstance(items, list) and len(items) > 0:
                    self._json_products = items
                    return items
        except Exception as e:
            logger.debug(f"Squarespace JSON format fetch skipped: {e}")
        return None

    async def extract_product_data(
        self,
        element: Any,
        page: Page
    ) -> Dict[str, Any]:
        """Extract product data from JSON object or DOM element."""
        if hasattr(self, "_json_products") and isinstance(element, dict):
            return self._extract_from_json(element, page.url)

        return await self._extract_from_dom(element, page)

    def _extract_from_json(self, item: Dict[str, Any], current_url: str) -> Dict[str, Any]:
        """Extract data from a Squarespace item JSON object."""
        struct = item.get("structuredContent") or {}
        variants = struct.get("variants") or []
        price = None
        orig_price = None
        sku = None

        if variants:
            first_v = variants[0]
            # Squarespace prices in JSON are often in cents (e.g. 2500 -> 25.00)
            raw_p = first_v.get("price")
            if raw_p is not None:
                price = float(raw_p) / 100.0 if raw_p > 100 else float(raw_p)
            raw_orig = first_v.get("salePrice")
            if raw_orig is not None:
                orig_price = float(raw_orig) / 100.0 if raw_orig > 100 else float(raw_orig)
            sku = first_v.get("sku")

        full_url = current_url
        url_id = item.get("fullUrl") or item.get("urlId")
        if url_id:
            full_url = urljoin(current_url, url_id)

        return {
            "name": item.get("title", ""),
            "description": item.get("excerpt") or item.get("body", ""),
            "price": price,
            "original_price": orig_price,
            "sku": sku,
            "image_url": item.get("assetUrl"),
            "product_url": full_url,
            "tags": item.get("tags", []),
            "availability": "In Stock",
            "platform": "squarespace",
        }

    async def _extract_from_dom(
        self,
        element: ElementHandle,
        page: Page
    ) -> Dict[str, Any]:
        """Extract product data from DOM element."""
        data = {
            "platform": "squarespace",
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

        # Original / sale price
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
                    or await img.get_attribute("data-image")
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
                    data["product_url"] = urljoin(base_url, href)
                    break

        data["availability"] = "In Stock"
        return data

    async def get_next_page(self, page: Page) -> Optional[str]:
        """Get next page URL for Squarespace pagination."""
        for selector in self.SELECTORS["next_page"]:
            try:
                next_btn = await page.query_selector(selector)
                if next_btn:
                    href = await next_btn.get_attribute("href")
                    if href:
                        return urljoin(page.url, href)
            except Exception:
                continue

        # Check URL parameter pagination: ?offset= or ?page=
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
