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
            "availability": "[itemprop='availability']::attr(href), [itemprop='availability']::attr(content), [itemprop='availability'], .stock-status, .availability",
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
        breadcrumbs = self._extract_breadcrumbs(soup)

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
        platform_product = self._extract_platform_product(soup, base_url)
        if platform_product:
            existing = next((item for item in products if item.get("url") == platform_product.get("url")), None)
            if existing:
                if platform_product.get("variants"):
                    existing["variants"] = platform_product["variants"]
                for field in ("sku", "brand", "description", "price", "currency", "image_url", "images"):
                    if not existing.get(field) and platform_product.get(field):
                        existing[field] = platform_product[field]
            else:
                products.append(platform_product)
        for product in products:
            if breadcrumbs:
                product.setdefault("categories", breadcrumbs)
                product.setdefault("category", breadcrumbs[-1])
                product.setdefault("subcategory", breadcrumbs[-2] if len(breadcrumbs) > 1 else None)
                product.setdefault("category_path", " > ".join(breadcrumbs))
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

            for key in ("@graph", "mainEntity", "itemListElement"):
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

        variants = []
        raw_variants = record.get("hasVariant") or []
        if isinstance(raw_variants, dict):
            raw_variants = [raw_variants]
        for variant in raw_variants if isinstance(raw_variants, list) else []:
            if not isinstance(variant, dict):
                continue
            variant_offers = variant.get("offers") or {}
            if isinstance(variant_offers, list):
                variant_offers = variant_offers[0] if variant_offers else {}
            if not isinstance(variant_offers, dict):
                variant_offers = {}
            variant_price, _, _ = self._parse_price(variant_offers.get("price"))
            variant_availability = str(variant_offers.get("availability") or "").lower()
            variant_image = variant.get("image")
            if isinstance(variant_image, list):
                variant_image = variant_image[0] if variant_image else None
            if isinstance(variant_image, dict):
                variant_image = variant_image.get("url")
            attributes = {
                key: variant[key]
                for key in ("size", "color", "colour", "material", "pattern")
                if variant.get(key) not in (None, "")
            }
            variants.append({
                "variant_id": str(variant.get("productID") or variant.get("sku") or ""),
                "sku": variant.get("sku"),
                "name": variant.get("name") or name or "Variant",
                "price": variant_price,
                "in_stock": not any(marker in re.sub(r"[^a-z]", "", variant_availability) for marker in ("outofstock", "soldout", "discontinued")),
                "attributes": attributes,
                "image_url": urljoin(base_url, str(variant_image)) if variant_image else None,
            })

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
            "variants": variants,
        }
        self._normalise(item, base_url)
        return {key: value for key, value in item.items() if value not in (None, "")}

    @staticmethod
    def _extract_breadcrumbs(soup: BeautifulSoup) -> List[str]:
        selectors = ("nav[aria-label*='breadcrumb' i] li", "ol.breadcrumb li", "ul.breadcrumb li", ".breadcrumbs li", ".breadcrumb li", "nav[aria-label*='breadcrumb' i] a", "ol.breadcrumb a", "ul.breadcrumb a", ".breadcrumbs a", ".breadcrumb a")
        for selector in selectors:
            labels = []
            for node in soup.select(selector):
                label = re.sub(r"\s+", " ", node.get_text(" ", strip=True)).strip()
                if label and label.casefold() not in ("home", "homepage") and label.casefold() not in [v.casefold() for v in labels]:
                    labels.append(label)
            if labels:
                return labels
        return []

    def _extract_platform_product(self, soup: BeautifulSoup, base_url: str):
        for node in soup.select('script[type="application/json"], script[id*="ProductJson" i]'):
            try:
                payload = json.loads(node.string or node.get_text() or "")
            except (TypeError, ValueError):
                continue
            for record in self._walk_json_objects(payload):
                if isinstance(record.get("variants"), list) and record.get("title") and (record.get("handle") or record.get("vendor")):
                    return self._from_shopify_json(record, base_url)
        form = soup.select_one("form.variations_form[data-product_variations]")
        if form:
            try:
                variations = json.loads(form.get("data-product_variations") or "[]")
            except (TypeError, ValueError):
                variations = []
            if isinstance(variations, list) and variations:
                return self._from_woocommerce(soup, variations, base_url)
        return None

    @staticmethod
    def _walk_json_objects(payload):
        if isinstance(payload, list):
            for item in payload:
                yield from ProductExtractor._walk_json_objects(item)
        elif isinstance(payload, dict):
            yield payload
            for value in payload.values():
                if isinstance(value, (dict, list)):
                    yield from ProductExtractor._walk_json_objects(value)

    def _from_shopify_json(self, record: Dict[str, Any], base_url: str):
        images = [urljoin(base_url, str((img.get("src") if isinstance(img, dict) else img))) for img in record.get("images", []) if img]
        variants = []
        option_names = [str(value) for value in (record.get("options") or [])]
        for variant in record.get("variants") or []:
            if not isinstance(variant, dict):
                continue
            attributes = {option_names[i]: variant.get(f"option{i + 1}") for i in range(len(option_names)) if variant.get(f"option{i + 1}") not in (None, "", "Default Title")}
            featured = variant.get("featured_image") or {}
            image = featured.get("src") if isinstance(featured, dict) else featured
            price = self._parse_price(variant.get("price"))[0]
            original = self._parse_price(variant.get("compare_at_price"))[0]
            variants.append({"variant_id": str(variant.get("id") or ""), "sku": variant.get("sku"), "name": variant.get("public_title") or variant.get("title") or record.get("title") or "Variant", "price": price, "original_price": original, "in_stock": bool(variant.get("available", False)), "stock_quantity": variant.get("inventory_quantity"), "attributes": attributes, "image_url": urljoin(base_url, str(image)) if image else None})
        first = (record.get("variants") or [{}])[0]
        return {"name": record.get("title"), "description": BeautifulSoup(record.get("body_html") or "", "lxml").get_text(" ", strip=True), "sku": first.get("sku"), "product_id": str(record.get("id")) if record.get("id") else None, "brand": record.get("vendor"), "price": self._parse_price(first.get("price"))[0], "currency": self._currency_from_text(str(first.get("price") or "")), "url": urljoin(base_url, "/products/" + str(record.get("handle"))) if record.get("handle") else base_url, "image_url": images[0] if images else None, "images": images, "variants": variants, "platform": "shopify", "product_type": record.get("product_type"), "tags": record.get("tags") or []}

    def _from_woocommerce(self, soup: BeautifulSoup, variations: List[Dict[str, Any]], base_url: str):
        title = soup.select_one("h1.product_title, .product_title, h1.entry-title")
        name = title.get_text(" ", strip=True) if title else None
        if not name:
            return None
        price_node = soup.select_one("p.price .woocommerce-Price-amount, .summary .price")
        raw_price = price_node.get_text(" ", strip=True) if price_node else None
        sku_node = soup.select_one(".sku")
        image_node = soup.select_one(".woocommerce-product-gallery__image img, img.wp-post-image")
        image = (image_node.get("data-src") or image_node.get("src")) if image_node else None
        variants = []
        for variation in variations:
            if not isinstance(variation, dict):
                continue
            attrs = {str(k).replace("attribute_", "").replace("pa_", "").replace("-", " ").title(): v for k, v in (variation.get("attributes") or {}).items() if v not in (None, "")}
            image_data = variation.get("image") or {}
            variant_image = (image_data.get("full_src") or image_data.get("src")) if isinstance(image_data, dict) else None
            variants.append({"variant_id": str(variation.get("variation_id") or ""), "sku": variation.get("sku"), "name": " / ".join(str(v) for v in attrs.values()) or name, "price": self._parse_price(variation.get("display_price"))[0], "original_price": self._parse_price(variation.get("display_regular_price"))[0], "in_stock": bool(variation.get("is_in_stock", False)), "stock_quantity": variation.get("max_qty"), "attributes": attrs, "image_url": urljoin(base_url, str(variant_image)) if variant_image else None})
        canonical = soup.find("link", rel="canonical")
        return {"name": name, "sku": sku_node.get_text(" ", strip=True) if sku_node else None, "price": self._parse_price(raw_price)[0], "currency": self._currency_from_text(raw_price or ""), "url": urljoin(base_url, canonical.get("href")) if canonical and canonical.get("href") else base_url, "image_url": urljoin(base_url, image) if image else None, "images": [urljoin(base_url, image)] if image else [], "variants": variants, "platform": "woocommerce"}
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
