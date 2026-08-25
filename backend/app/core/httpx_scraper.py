"""
HttpxScraper — Reliable, library-based product scraper.

Uses httpx (async HTTP) + BeautifulSoup for HTML parsing.
Works inside FastAPI BackgroundTasks without Playwright complications.
"""

import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Callable, Awaitable
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-GB,en;q=0.9",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

# Known platform selectors by domain keyword
PLATFORM_SELECTORS: Dict[str, Dict] = {
    "rs-online.com": {
        "platform": "RS Online",
        "product_container": "div[data-testid='product-card']",
        "name": "a[data-testid='product-card-title-link']",
        "price": ".items-baseline span.font-bold",
        "image": "img",
        "link": "a[data-testid='product-card-title-link']",
    },
    "books.toscrape.com": {
        "platform": "Books To Scrape",
        "product_container": "article.product_pod",
        "name": "h3 a",
        "price": ".price_color",
        "image": "img",
        "link": "h3 a",
    },
    "webscraper.io": {
        "platform": "WebScraper Test",
        "product_container": ".thumbnail",
        "name": ".title",
        "price": ".price",
        "image": "img",
        "link": "a",
    },
    "shopify": {
        "platform": "Shopify",
        "product_container": ".product-card, .product-item, .grid__item",
        "name": ".product-card__title, .product-item__title, h3",
        "price": ".price, .product-price, .money",
        "image": "img",
        "link": "a",
    },
    "allbirds": {
        "platform": "Allbirds",
        "product_container": "div.grid div.bg-white.flex-col",
        "name": "p.font-sans.text-xs.font-medium.tracking-wider",
        "price": "p.font-sans span",
        "image": "img",
        "link": "a",
    },
    "woocommerce": {
        "platform": "WooCommerce",
        "product_container": "li.product, .product-type-simple",
        "name": "h2.woocommerce-loop-product__title, h3",
        "price": ".price, .woocommerce-Price-amount",
        "image": "img",
        "link": "a",
    },
    "amazon": {
        "platform": "Amazon",
        "product_container": "div[data-component-type='s-search-result']",
        "name": "h2 a.a-link-normal span",
        "price": "span.a-price span.a-offscreen",
        "image": "img.s-image",
        "link": "h2 a.a-link-normal",
    },
    "ebay": {
        "platform": "eBay",
        "product_container": ".s-item, li.s-item",
        "name": ".s-item__title",
        "price": ".s-item__price",
        "image": ".s-item__image-img, img",
        "link": "a.s-item__link",
    },
    "daraz": {
        "platform": "Daraz",
        "product_container": "div[data-qa-locator='product-item']",
        "name": "a[title], div[class*='title']",
        "price": "span[class*='price']",
        "image": "img",
        "link": "a",
    },
}

GENERIC_SELECTORS = {
    "platform": "Generic",
    "product_container": (
        "article.product_pod, "
        ".product, .product-item, .product-card, .product-tile, "
        "article.product, li.product, "
        ".item-card, .catalog-item, .card, "
        "[class*='product-card'], [class*='product_pod'], [class*='item-card']"
    ),
    "name": "h1, h2, h3 a, h4, .name, .title, .product-name, .product-title",
    "price": ".price_color, .price, .amount, .cost, [class*='price']",
    "image": "img",
    "link": "a",
}


def _get_selectors(url: str) -> Dict:
    domain = urlparse(url).netloc.lower()
    for key, sel in PLATFORM_SELECTORS.items():
        if key in domain:
            return sel
    return GENERIC_SELECTORS


def _extract_products(html: str, page_url: str, selectors: Dict) -> List[Dict[str, Any]]:
    """Extract product data from HTML using BeautifulSoup."""
    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:
        soup = BeautifulSoup(html, "html.parser")

    products = []

    containers = soup.select(selectors["product_container"])
    if not containers:
        return products

    for container in containers:
        try:
            name_el = container.select_one(selectors["name"])
            name = name_el.get_text(strip=True) if name_el else None

            price_el = container.select_one(selectors["price"])
            price_text = price_el.get_text(strip=True) if price_el else None

            img_el = container.select_one(selectors["image"])
            image_url = None
            if img_el:
                image_url = img_el.get("src") or img_el.get("data-src") or img_el.get("data-lazy")
                if image_url:
                    image_url = urljoin(page_url, image_url)

            if selectors["link"] == "self":
                link_el = container if container.name == "a" else container.find("a")
            else:
                link_el = container.select_one(selectors["link"])
                
            product_url = None
            if link_el:
                href = link_el.get("href", "")
                product_url = urljoin(page_url, href) if href else page_url

            if name and len(name) > 2:
                # Parse price
                price_val = None
                if price_text:
                    nums = re.findall(r"[\d,]+\.?\d*", price_text.replace(",", ""))
                    if nums:
                        try:
                            price_val = float(nums[0])
                        except ValueError:
                            pass

                products.append({
                    "name": name[:500],
                    "price": price_val,
                    "price_text": price_text,
                    "image_url": image_url,
                    "url": product_url or page_url,
                })
        except Exception:
            continue

    return products


def _extract_links(html: str, base_url: str, allowed_domain: str) -> List[str]:
    """Extract internal links from HTML."""
    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:
        soup = BeautifulSoup(html, "html.parser")

    links = set()
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith(("#", "javascript:", "mailto:")):
            continue
        full_url = urljoin(base_url, href).split("#")[0].rstrip("/")
        parsed = urlparse(full_url)
        if parsed.scheme in ("http", "https") and allowed_domain in parsed.netloc:
            links.add(full_url)
    return list(links)


class HttpxScraper:
    """
    Reliable async scraper using httpx + BeautifulSoup.
    Runs cleanly inside FastAPI BackgroundTasks.
    """

    def __init__(
        self,
        job_id: int,
        start_url: str,
        *,
        max_pages: int = 100,
        max_products: int = 10000,
        max_depth: int = 3,
        request_delay: float = 1.0,
        proxy: Optional[str] = None,
        on_log: Optional[Callable[[str, str], Awaitable[None]]] = None,
        on_product_batch: Optional[Callable[[List[Dict]], Awaitable[None]]] = None,
        on_page_done: Optional[Callable[[str, bool, int], Awaitable[None]]] = None,
    ):
        self.job_id = job_id
        self.start_url = start_url.rstrip("/")
        self.max_pages = max_pages
        self.max_products = max_products
        self.max_depth = max_depth
        self.request_delay = request_delay
        self.proxy = proxy

        parsed = urlparse(start_url)
        self.allowed_domain = parsed.netloc

        self.selectors = _get_selectors(start_url)
        self.platform = self.selectors.get("platform", "Generic")

        self.on_log = on_log
        self.on_product_batch = on_product_batch
        self.on_page_done = on_page_done

        self._visited: set = set()
        self._queue: List[tuple] = [(self.start_url, 0)]  # (url, depth)
        self._total_products = 0

    async def _log(self, message: str, level: str = "info"):
        logger.info(f"[Job {self.job_id}] {message}")
        if self.on_log:
            await self.on_log(message, level)

    async def run(self):
        await self._log(f"Starting scrape of {self.start_url}")
        await self._log(f"Detected platform: {self.platform}")
        await self._log(f"Max pages: {self.max_pages} | Max products: {self.max_products}")

        pages_scraped = 0
        timeout = httpx.Timeout(30.0)

        client_kwargs = {
            "headers": HEADERS,
            "timeout": timeout,
            "follow_redirects": True,
            "verify": False,
        }
        if self.proxy:
            client_kwargs["proxy"] = self.proxy
            await self._log(f"  ↳ Using HTTPX proxy: {self.proxy}")

        async with httpx.AsyncClient(**client_kwargs) as client:

            while self._queue and pages_scraped < self.max_pages and self._total_products < self.max_products:
                url, depth = self._queue.pop(0)

                if url in self._visited:
                    continue
                self._visited.add(url)

                await self._log(f"[{pages_scraped + 1}/{self.max_pages}] Fetching: {url}")

                try:
                    response = await client.get(url)
                    status = response.status_code

                    if status >= 400:
                        await self._log(f"  ↳ HTTP {status} — skipping", "warning")
                        if self.on_page_done:
                            await self.on_page_done(url, False, pages_scraped)
                        continue

                    html = response.text
                    pages_scraped += 1

                    # Extract products
                    products = _extract_products(html, url, self.selectors)
                    if products:
                        await self._log(f"  ↳ Found {len(products)} products on page")
                        if self.on_product_batch:
                            await self.on_product_batch(products)
                        self._total_products += len(products)
                    else:
                        await self._log(f"  ↳ No products found on this page", "debug")

                    # Extract links if not max depth
                    if depth < self.max_depth:
                        links = _extract_links(html, url, self.allowed_domain)
                        new_links = [l for l in links if l not in self._visited]
                        await self._log(f"  ↳ Found {len(new_links)} new links to follow", "debug")
                        for link in new_links:
                            self._queue.append((link, depth + 1))

                    if self.on_page_done:
                        await self.on_page_done(url, True, pages_scraped)

                    await asyncio.sleep(self.request_delay)

                except httpx.TimeoutException:
                    await self._log(f"  ↳ Timeout fetching {url}", "warning")
                    if self.on_page_done:
                        await self.on_page_done(url, False, pages_scraped)
                except Exception as e:
                    await self._log(f"  ↳ Error: {e}", "error")
                    if self.on_page_done:
                        await self.on_page_done(url, False, pages_scraped)

        await self._log(
            f"Scrape complete. Pages: {pages_scraped}, Products: {self._total_products}"
        )
