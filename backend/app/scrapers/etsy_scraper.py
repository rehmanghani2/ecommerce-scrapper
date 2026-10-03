"""
Etsy Marketplace Scraper Module
Specialized scraper for Etsy listings and search pages.
"""

from playwright.async_api import Page, ElementHandle
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin
import re
import logging

from app.scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class EtsyScraper(BaseScraper):
    """Specialized scraper for Etsy marketplace listings."""

    PLATFORM_NAME = "etsy"
    PLATFORM_DOMAINS = ["etsy.com"]

    SELECTORS = {
        "product_container": [
            "div.v2-listing-card",
            "li.wt-list-unstyled .v2-listing-card",
            "div[data-search-results-listing-card]",
            ".search-listings-group div.v2-listing-card",
            "div.js-merch-stash-check-listing",
            "li.wt-grid__item-xs--6",
            "div.listing-card",
        ],
        "name": [
            "h3.v2-listing-card__title",
            "h3.wt-text-caption",
            "a.listing-link h3",
            ".v2-listing-card__title",
            "h2.wt-text-caption",
            "h3",
        ],
        "brand": [
            "p.wt-text-caption.wt-text-gray",
            ".v2-listing-card__shop",
            ".wt-text-caption--subtle",
            ".shop-name",
        ],
        "price": [
            ".currency-value",
            "span.currency-value",
            "p.wt-text-title-01 .currency-value",
            ".lc-price .currency-value",
            "span.wt-screen-reader-only + span",
            ".n-listing-card__price",
        ],
        "original_price": [
            ".wt-text-strikethrough .currency-value",
            "span.wt-text-strikethrough",
            "del .currency-value",
            "del",
        ],
        "image": [
            "img.wt-width-full",
            "img.v2-listing-card__img",
            ".v2-listing-card__img img",
            "img[data-listing-card-image]",
            "img",
        ],
        "link": [
            "a.listing-link",
            "a.v2-listing-card__link",
            "a[data-listing-id]",
            "a",
        ],
        "rating": [
            "input[name='rating']",
            ".wt-rating",
            "span[data-rating]",
        ],
        "next_page": [
            "a.wt-action-group__item--secondary[rel='next']",
            "nav[aria-label='Pagination'] a.wt-is-selected + a",
            "a[rel='next']",
            ".wt-pagination__item--next a",
            ".pagination .next a",
        ],
    }

    async def detect_products(self, page: Page) -> List[ElementHandle]:
        """Detect Etsy listing cards on page."""
        for selector in self.SELECTORS["product_container"]:
            try:
                await page.wait_for_selector(selector, timeout=5000)
                products = await page.query_selector_all(selector)
                if len(products) >= 1:
                    return products
            except Exception:
                continue

        # Fallback container patterns
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
        """Extract product details from an Etsy listing element."""
        data = {
            "platform": "etsy",
        }
        base_url = page.url

        # Name / Title
        for selector in self.SELECTORS["name"]:
            name = await self._get_text(element, selector)
            if name:
                data["name"] = name
                break

        # Shop / Seller (Brand)
        for selector in self.SELECTORS["brand"]:
            shop = await self._get_text(element, selector)
            if shop:
                data["brand"] = shop
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

        # Original / Compare Price
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
                    or await img.get_attribute("data-original-image-url")
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

        # Rating
        for selector in self.SELECTORS["rating"]:
            rating_el = await element.query_selector(selector)
            if rating_el:
                val = await rating_el.get_attribute("value") or await rating_el.get_attribute("data-rating")
                if val:
                    try:
                        data["rating"] = float(val)
                        break
                    except ValueError:
                        pass

        data["availability"] = "In Stock"
        return data

    async def get_next_page(self, page: Page) -> Optional[str]:
        """Get next page URL for Etsy search/shop pagination."""
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
