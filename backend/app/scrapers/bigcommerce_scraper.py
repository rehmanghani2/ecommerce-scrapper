"""
BigCommerce Scraper Module
Specialized scraper for BigCommerce stores (Cornerstone and Stencil themes).
"""

from playwright.async_api import Page, ElementHandle
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin
import re
import logging

from app.scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class BigCommerceScraper(BaseScraper):
    """Specialized scraper for BigCommerce stores."""

    PLATFORM_NAME = "bigcommerce"
    PLATFORM_DOMAINS = ["mybigcommerce.com"]

    # Standard BigCommerce Stencil selectors
    SELECTORS = {
        "product_container": [
            "article.card",
            ".productGrid .product",
            ".productGrid .product-grid-item",
            ".card[data-test='card']",
            ".productCarousel-slide",
            "li.product",
        ],
        "name": [
            ".card-title a",
            "h3.card-title a",
            "h4.card-title a",
            ".card-title",
            "a.card-title",
            "[data-test-info-type='productTitle'] a",
        ],
        "brand": [
            ".card-text--brand",
            ".card-brand",
            "[data-test-info-type='brandName']",
            ".card-text[data-test-info-type='brand']",
        ],
        "price": [
            ".price--withoutTax",
            ".price--withTax",
            ".price--main",
            ".price-section .price",
            ".card-text--price .price",
            "[data-product-price-without-tax]",
            "[data-product-price-with-tax]",
            "span.price",
        ],
        "original_price": [
            ".price--rrp",
            ".price--non-sale",
            ".price--compareAt",
            "[data-product-rrp-without-tax]",
            "span.price--rrp",
            "del.price",
        ],
        "image": [
            ".card-img-container img",
            ".card-image",
            "img.card-image",
            ".card-figure img",
            "img",
        ],
        "link": [
            ".card-title a",
            ".card-figure__link",
            "a.card-figure__link",
            "a.card-image-link",
            "a",
        ],
        "rating": [
            "[data-test='rating']",
            ".rating--small",
            ".card-rating",
        ],
        "next_page": [
            ".pagination-item--next a",
            ".pagination-next a",
            "a.pagination-link--next",
            "a[rel='next']",
            ".pagination .next a",
        ],
    }

    async def detect_products(self, page: Page) -> List[ElementHandle]:
        """Detect BigCommerce product cards on the page."""
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
        """Extract product data from a BigCommerce card element."""
        data = {
            "platform": "bigcommerce",
        }
        base_url = page.url

        # Name / Title
        for selector in self.SELECTORS["name"]:
            name = await self._get_text(element, selector)
            if name:
                data["name"] = name
                break

        # Brand
        for selector in self.SELECTORS["brand"]:
            brand = await self._get_text(element, selector)
            if brand:
                data["brand"] = brand
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

        # Original / RRP Price
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
                    or await img.get_attribute("data-srcset")
                )
                if src:
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
        """Get next page URL for BigCommerce pagination."""
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
