"""
Generic product extraction with CSS selectors and JSON-LD fallback.
"""
import json
import logging
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class ProductExtractor:
    """Extract normalized product records from rendered storefront HTML."""

    DEFAULT_SELECTORS = {
        "product_container": ".product, .product-item, .product-card, .product-tile, [data-product], [itemtype*='Product']",
        "fields": {
            "name": ".product-title, .product-name, .title, .name, [itemprop='name'], h2, h3",
            "price": ".price, .product-price, .amount, .current-price, .money, [itemprop='price']",
            "image_url": "img::attr(data-src), img::attr(data-lazy-src), img::attr(src), [itemprop='image']::attr(content)",
            "url": "a::attr(href), [itemprop='url']::attr(href)",
            "sku": "[itemprop='sku']::attr(content), [data-sku]::attr(data-sku)",
            "brand": "[itemprop='brand']::attr(content), .product-brand, .brand",
            "description": "[itemprop='description'], .product-description"
        }
    }

    def __init__(self, selector_config: Optional[Dict[str, Any]] = None):
        self.selector_config = selector_config or self.DEFAULT_SELECTORS
        if not self.selector_config.get("product_container") and self.selector_config.get("product_card"):
            self.selector_config["product_container"] = self.selector_config["product_card"]

    def extract(self, html: str, base_url: str) -> List[Dict[str, Any]]:
        soup = BeautifulSoup(html or "", "lxml")
        selectors = self.selector_config.get("fields", {})
        container_selector = self.selector_config.get("product_container")
        products: List[Dict[str, Any]] = []
        seen = set()

        if container_selector:
            for container in soup.select(container_selector):
                item: Dict[str, Any] = {}
                for field, selector in selectors.items():
                    try:
                        value = self._extract_field(container, selector)
                        if value:
                            item[field] = value
                    except Exception as exc:
                        logger.debug("Could not extract %s: %s", field, exc)
                if item.get("name") or item.get("price"):
                    self._normalise(item, base_url)
                    if item.get("url") not in seen:
                        seen.add(item.get("url"))
                        products.append(item)

        # Product structured data is often more reliable than storefront CSS.
        for node in soup.select('script[type="application/ld+json"]'):
            try:
                payload = json.loads(node.string or node.get_text() or "")
            except (TypeError, ValueError):
                continue
            for record in self._walk_jsonld(payload):
                product = self._from_jsonld(record, base_url)
                if product and product.get("url") not in seen:
                    seen.add(product.get("url"))
                    products.append(product)

        # A product detail page may not contain a product-card wrapper.
        if not products:
            product = self._from_meta(soup, base_url)
            if product:
                products.append(product)
        return products

    def _extract_field(self, container, selector: str):
        if not selector:
            return None
        for candidate in (part.strip() for part in selector.split(",")):
            try:
                if "::attr(" in candidate:
                    css, attr = candidate.split("::attr(", 1)
                    attr = attr.rstrip(")")
                    element = container.select_one(css) if css else container
                    value = element.get(attr) if element else None
                else:
                    element = container.select_one(candidate)
                    value = element.get("content") if element and element.has_attr("content") else (
                        element.get_text(" ", strip=True) if element else None
                    )
                if value:
                    return str(value).strip()
            except Exception:
                continue
        return None

    def _normalise(self, product: Dict[str, Any], base_url: str) -> None:
        for key in ("url", "image_url"):
            if product.get(key):
                product[key] = urljoin(base_url, product[key])
        if not product.get("url"):
            product["url"] = base_url
        if product.get("price"):
            match = re.search(r"\d[\d,.]*", str(product["price"]))
            if match:
                product["price_text"] = str(product["price"])
                product["price"] = match.group(0).replace(",", "")

    def _walk_jsonld(self, payload):
        if isinstance(payload, list):
            for item in payload:
                yield from self._walk_jsonld(item)
        elif isinstance(payload, dict):
            graph = payload.get("@graph")
            if graph:
                yield from self._walk_jsonld(graph)
            kind = payload.get("@type", [])
            kinds = kind if isinstance(kind, list) else [kind]
            if any(str(value).lower() == "product" for value in kinds):
                yield payload

    def _from_jsonld(self, record: Dict[str, Any], base_url: str):
        name = record.get("name")
        offers = record.get("offers") or {}
        if isinstance(offers, list):
            offers = offers[0] if offers else {}
        brand = record.get("brand") or {}
        if isinstance(brand, dict):
            brand = brand.get("name")
        image = record.get("image")
        if isinstance(image, list):
            image = image[0] if image else None
        if isinstance(image, dict):
            image = image.get("url")
        url = record.get("url") or record.get("@id") or base_url
        if not name and not offers:
            return None
        item = {
            "name": name,
            "description": record.get("description"),
            "sku": record.get("sku") or record.get("mpn"),
            "brand": brand,
            "price": offers.get("price"),
            "currency": offers.get("priceCurrency"),
            "availability": offers.get("availability"),
            "image_url": image,
            "url": url,
        }
        self._normalise(item, base_url)
        return {key: value for key, value in item.items() if value not in (None, "")}

    def _from_meta(self, soup: BeautifulSoup, base_url: str):
        def meta(*names):
            for name in names:
                tag = soup.find("meta", attrs={"property": name}) or soup.find("meta", attrs={"name": name})
                if tag and tag.get("content"):
                    return tag["content"].strip()
            return None
        name = meta("og:title", "twitter:title") or (soup.title.get_text(strip=True) if soup.title else None)
        price = meta("product:price:amount", "og:price:amount")
        image = meta("og:image", "twitter:image")
        if not name or not (price or image):
            return None
        item = {"name": name, "price": price, "image_url": image, "url": base_url}
        self._normalise(item, base_url)
        return item
