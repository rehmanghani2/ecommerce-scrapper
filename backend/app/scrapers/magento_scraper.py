"""
Magento (Adobe Commerce) Scraper Module
Specialized scraper for Magento 1 & Magento 2 e-commerce stores (Luma, Hyvä, and standard themes).
"""

from playwright.async_api import Page, ElementHandle
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin
import re
import logging

from app.scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class MagentoScraper(BaseScraper):
    """Specialized scraper for Magento / Adobe Commerce stores."""

    PLATFORM_NAME = "magento"
    PLATFORM_DOMAINS = []

    # Common Magento 1 and Magento 2 selectors
    SELECTORS = {
        "product_container": [
            ".item.product.product-item",
            "li.product-item",
            ".product-item-info",
            ".product-item",
            ".products-grid .item",
            ".products-list .item",
        ],
        "name": [
            "strong.product-item-name a",
            "a.product-item-link",
            ".product-item-name a",
            ".product-name a",
            "h2.product-name a",
            "h3.product-name a",
        ],
        "price": [
            "[data-price-type='finalPrice'] .price",
            ".special-price .price",
            "span[id^='product-price-'] .price",
            ".price-box .price",
            ".price-wrapper .price",
            ".normal-price .price",
            ".regular-price .price",
        ],
        "original_price": [
            ".old-price .price",
            "[data-price-type='oldPrice'] .price",
            ".regular-price .price",
            "del .price",
        ],
        "image": [
            "img.product-image-photo",
            "img.photo.image",
            ".product-image-container img",
            ".product-item-photo img",
            "img",
        ],
        "link": [
            "a.product-item-link",
            "a.product.photo",
            "strong.product-item-name a",
            ".product-item-info a",
            "a",
        ],
        "sku": [
            "[data-product-sku]",
            ".sku .value",
        ],
        "rating": [
            ".rating-result",
            ".rating-summary",
        ],
        "next_page": [
            "a.action.next",
            "li.pages-item-next a",
            ".pages-item-next a",
            "a[rel='next']",
            ".pages .next",
        ],
    }

    async def detect_products(self, page: Page) -> List[ElementHandle]:
        """Detect Magento product elements on the page."""
        for selector in self.SELECTORS["product_container"]:
            try:
                await page.wait_for_selector(selector, timeout=5000)
                products = await page.query_selector_all(selector)
                if len(products) >= 1:
                    return products
            except Exception:
                continue

        # Fallback generic container check
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
        """Extract product data from a Magento item element."""
        data = {
            "platform": "magento",
        }
        base_url = page.url

        # Name / Title
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

        # Original / regular price (for discounted items)
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
                    or await img.get_attribute("data-original")
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

        # SKU
        sku_val = await element.get_attribute("data-product-sku")
        if sku_val:
            data["sku"] = sku_val.strip()

        # Rating
        for selector in self.SELECTORS["rating"]:
            rating_elem = await element.query_selector(selector)
            if rating_elem:
                title_val = await rating_elem.get_attribute("title")
                if title_val:
                    match = re.search(r'(\d+)', title_val)
                    if match:
                        data["rating"] = round(float(match.group(1)) / 20.0, 1)  # 100% -> 5.0
                        break

        data["availability"] = "In Stock"
        return data

    async def get_next_page(self, page: Page) -> Optional[str]:
        """Get next page URL for Magento pagination."""
        for selector in self.SELECTORS["next_page"]:
            try:
                next_btn = await page.query_selector(selector)
                if next_btn:
                    href = await next_btn.get_attribute("href")
                    if href:
                        return urljoin(page.url, href)
            except Exception:
                continue

        # Check URL parameter pagination: ?p=2 or &p=2
        current_url = page.url
        if "p=" in current_url:
            match = re.search(r'p=(\d+)', current_url)
            if match:
                current_page = int(match.group(1))
                return re.sub(r'p=\d+', f'p={current_page + 1}', current_url)
        else:
            sep = "&" if "?" in current_url else "?"
            return f"{current_url}{sep}p=2"

        return None
