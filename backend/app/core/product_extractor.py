"""
Generic product extraction with CSS selectors and Schema.org/Open Graph fallbacks.
"""
import json
import logging
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urldefrag, urlparse

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
            "description": "[itemprop='description'], .product-description",
            "availability": "[itemprop='availability']::attr(href), [itemprop='availability']::attr(content), .stock-status, .availability",
        },
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
                    item["images"] = self._extract_images(container, base_url)
                    self._normalise(item, base_url)
                    key = self._identity(item, base_url)
                    if key not in seen:
                        seen.add(key)
                        products.append(item)

        # Structured data is usually more reliable than storefront CSS.
        for node in soup.select('script[type="application/ld+json"]'):
            try:
                payload = json.loads(node.string or node.get_text() or "")
            except (TypeError, ValueError):
                continue
            for record in self._walk_jsonld(payload):
                product = self._from_jsonld(record, base_url)
                if product:
                    key = self._identity(product, base_url)
                    if key not in seen:
                        seen.add(key)
                        products.append(product)

        # Product detail pages often have no product-card wrapper or JSON-LD.
        if not products:
            product = self._from_meta(soup, base_url)
            if product:
                products.append(product)
        return products

    @staticmethod
    def _identity(product: Dict[str, Any], base_url: str) -> str:
        """Prefer stable product identifiers over a listing-page fallback URL."""
        sku = str(product.get("sku") or "").strip().casefold()
        if sku:
            return f"sku:{sku}"
        url = str(product.get("url") or "").strip()
        if url and url != base_url:
            clean_url = urldefrag(url)[0].rstrip("/").casefold()
            if clean_url:
                return f"url:{clean_url}"
        name = re.sub(r"\s+", " ", str(product.get("name") or "")).strip().casefold()
        brand = str(product.get("brand") or "").strip().casefold()
        return f"name:{brand}:{name}" if name else f"fallback:{url}"

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

    @staticmethod
    def _extract_images(container, base_url: str) -> List[str]:
        images = []
        for image in container.select("img"):
            source = (
                image.get("data-src")
                or image.get("data-lazy-src")
                or image.get("data-original")
                or image.get("src")
            )
            if not source:
                continue
            absolute = urljoin(base_url, str(source).strip())
            if absolute not in images:
                images.append(absolute)
        return images

    @staticmethod
    def _parse_price(value: Any):
        if value in (None, ""):
            return None, None, None
        raw = str(value).strip()
        match = re.search(r"\d[\d,]*(?:\.\d{1,4})?", raw)
        if not match:
            return None, raw, ProductExtractor._currency_from_text(raw)
        numeric = match.group(0)
        if "," in numeric and "." in numeric:
            numeric = numeric.replace(",", "")
        elif "," in numeric:
            whole, fraction = numeric.rsplit(",", 1)
            numeric = f"{whole}.{fraction}" if len(fraction) in (1, 2) else f"{whole}{fraction}"
        return numeric, raw, ProductExtractor._currency_from_text(raw)

    @staticmethod
    def _currency_from_text(value: str):
        text = str(value or "").upper()
        if "£" in text or "GBP" in text:
            return "GBP"
        if "€" in text or "EUR" in text:
            return "EUR"
        if "$" in text or "USD" in text:
            return "USD"
        return None

    def _normalise(self, product: Dict[str, Any], base_url: str) -> None:
        for key in ("url", "image_url"):
            if product.get(key):
                product[key] = urljoin(base_url, str(product[key]).strip())
        if not product.get("url"):
            product["url"] = base_url

        raw_price = product.get("price")
        if raw_price is not None:
            numeric, price_text, currency = self._parse_price(raw_price)
            if numeric is not None:
                product["price"] = numeric
            if price_text:
                product["price_text"] = price_text
            if currency and not product.get("currency"):
                product["currency"] = currency

        images = product.get("images") or []
        if product.get("image_url") and product["image_url"] not in images:
            images.insert(0, product["image_url"])
        product["images"] = images
        if not product.get("image_url") and images:
            product["image_url"] = images[0]

        availability = str(product.get("availability") or "").lower()
        if availability:
            compact_availability = re.sub(r"[^a-z]", "", availability)
            product["in_stock"] = not any(
                marker in compact_availability
                for marker in ("outofstock", "soldout", "discontinued", "unavailable")
            )
            product["stock_status"] = "In Stock" if product["in_stock"] else "Out of Stock"

    def _walk_jsonld(self, payload):
        """Walk JSON-LD arrays, graphs and nested variant/product structures."""
        if isinstance(payload, list):
            for item in payload:
                yield from self._walk_jsonld(item)
        elif isinstance(payload, dict):
            kind = payload.get("@type", [])
            kinds = kind if isinstance(kind, list) else [kind]
            if any(str(value).rstrip("/").split("/")[-1].lower() == "product" for value in kinds):
                yield payload

            for key in ("@graph", "mainEntity", "itemListElement", "hasVariant"):
                nested = payload.get(key)
                if nested:
                    if key == "itemListElement" and isinstance(nested, list):
                        for entry in nested:
                            if isinstance(entry, dict):
                                yield from self._walk_jsonld(entry.get("item", entry))
                    else:
                        yield from self._walk_jsonld(nested)

    def _from_jsonld(self, record: Dict[str, Any], base_url: str):
        name = record.get("name")
        offers = record.get("offers") or {}
        if isinstance(offers, list):
            offers = offers[0] if offers else {}
        if not isinstance(offers, dict):
            offers = {}

        brand = record.get("brand") or {}
        if isinstance(brand, dict):
            brand = brand.get("name")
        image = record.get("image")
        images = image if isinstance(image, list) else ([image] if image else [])
        images = [
            value.get("url") if isinstance(value, dict) else value
            for value in images
        ]
        images = [urljoin(base_url, str(value)) for value in images if value]
        image = images[0] if images else None

        price = offers.get("price")
        if price is None:
            price = offers.get("lowPrice")
        url = record.get("url") or record.get("@id") or offers.get("url") or base_url
        if not name and price is None:
            return None

        item = {
            "name": name,
            "description": record.get("description"),
            "sku": record.get("sku") or record.get("mpn"),
            "brand": brand,
            "price": price,
            "currency": offers.get("priceCurrency"),
            "availability": offers.get("availability"),
            "url": url,
            "image_url": image,
            "images": images,
            "product_id": record.get("productID") or record.get("productId"),
            "gtin": record.get("gtin13") or record.get("gtin12") or record.get("gtin"),
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
        description = meta("og:description", "description")
        if not name or not (price or image):
            return None
        item = {
            "name": name,
            "price": price,
            "currency": meta("product:price:currency", "og:price:currency"),
            "image_url": image,
            "description": description,
            "url": base_url,
        }
        self._normalise(item, base_url)
        return item
