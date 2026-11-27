"""
Conservative normalization and exact deduplication for scraped product records.

Identity is scoped to a retailer. Canonical product URLs are preferred because
variant query parameters can represent distinct purchasable products. Strong
identifiers are fallbacks only when a URL is unavailable; fuzzy title matching
is intentionally excluded from record-level deduplication.
"""
import html
import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import logging

logger = logging.getLogger(__name__)


class DataCleaner:
    CURRENCY_MAP = {
        "$": "USD", "€": "EUR", "£": "GBP", "₹": "INR", "¥": "JPY",
        "USD": "USD", "US$": "USD", "EUR": "EUR", "GBP": "GBP",
        "INR": "INR", "JPY": "JPY", "CAD": "CAD", "AUD": "AUD",
    }
    TRACKING_KEYS = {
        "gclid", "fbclid", "msclkid", "dclid", "yclid", "referrer",
        "ref", "source", "campaign", "tracking",
    }
    INVALID_IDENTIFIERS = {"", "na", "n/a", "none", "null", "unknown", "default", "0"}

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url

    def clean_products(self, products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Normalize records and merge only records with a strong exact identity."""
        output: List[Dict[str, Any]] = []
        positions: Dict[str, int] = {}

        for raw in products or []:
            if not isinstance(raw, dict):
                continue
            clean = self.clean_product(raw)
            if not clean or not self._is_product_record(clean):
                continue

            identity = self._identity_key(clean)
            if identity and identity in positions:
                index = positions[identity]
                output[index] = self._merge_records(output[index], clean)
                continue

            if identity:
                positions[identity] = len(output)
            output.append(clean)

        return output

    def clean_product(self, product: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Return a normalized copy without mutating the extractor's source object."""
        try:
            cleaned = dict(product)
            for key, value in list(cleaned.items()):
                if isinstance(value, str):
                    cleaned[key] = self._clean_text(value)

            raw_price = cleaned.get("price")
            if raw_price not in (None, ""):
                numeric, detected_currency = self._parse_price(raw_price)
                if numeric is not None:
                    cleaned["price"] = numeric
                elif isinstance(raw_price, str):
                    # Keep an unparseable source value rather than silently erasing it.
                    cleaned["price_text"] = raw_price
                    cleaned["price"] = None
                if detected_currency:
                    cleaned["currency"] = detected_currency
                elif cleaned.get("currency"):
                    cleaned["currency"] = str(cleaned["currency"]).strip().upper()

            for key in ("url", "image_url"):
                if cleaned.get(key):
                    cleaned[key] = self._canonicalize_url(cleaned[key])

            if not cleaned.get("url") and self.base_url:
                cleaned["url"] = self._canonicalize_url(self.base_url)

            images = cleaned.get("images") or []
            if isinstance(images, str):
                images = [images]
            normalized_images = []
            for image in images:
                value = self._canonicalize_url(image)
                if value and value not in normalized_images:
                    normalized_images.append(value)
            if cleaned.get("image_url") and cleaned["image_url"] not in normalized_images:
                normalized_images.insert(0, cleaned["image_url"])
            cleaned["images"] = normalized_images

            for field in ("sku", "product_id", "gtin", "gtin8", "gtin12", "gtin13", "gtin14", "ean", "upc", "mpn"):
                value = cleaned.get(field)
                if value is not None:
                    cleaned[field] = self._clean_identifier(value)

            if cleaned.get("brand"):
                cleaned["brand"] = self._clean_text(str(cleaned["brand"]))
            if cleaned.get("name"):
                cleaned["name"] = self._clean_text(str(cleaned["name"]))
            return cleaned
        except (TypeError, ValueError, InvalidOperation):
            logger.exception("Failed to clean product record")
            return None

    @staticmethod
    def _clean_text(value: str) -> str:
        text = html.unescape(str(value))
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    @classmethod
    def _clean_identifier(cls, value: Any) -> Optional[str]:
        text = re.sub(r"\s+", "", str(value)).strip()
        return None if text.casefold() in cls.INVALID_IDENTIFIERS else text

    @classmethod
    def _parse_price(cls, value: Any):
        """Parse common UK/US/EU price formats using Decimal (no binary float drift)."""
        if value is None or value == "":
            return None, None
        if isinstance(value, (int, float, Decimal)):
            try:
                number = Decimal(str(value))
                return float(number.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)), None
            except InvalidOperation:
                return None, None

        text = str(value).strip().upper()
        currency = None
        for marker, code in sorted(cls.CURRENCY_MAP.items(), key=lambda item: len(item[0]), reverse=True):
            if marker in text:
                currency = code
                break

        match = re.search(r"[-+]?[0-9][0-9.,\s]*", text)
        if not match:
            return None, currency
        number_text = re.sub(r"\s+", "", match.group(0)).strip(".,")
        if "," in number_text and "." in number_text:
            # The last separator is treated as the decimal separator.
            if number_text.rfind(",") > number_text.rfind("."):
                number_text = number_text.replace(".", "").replace(",", ".")
            else:
                number_text = number_text.replace(",", "")
        elif "," in number_text:
            tail = number_text.rsplit(",", 1)[1]
            number_text = number_text.replace(",", ".") if len(tail) in (1, 2) else number_text.replace(",", "")
        elif number_text.count(".") > 1:
            parts = number_text.split(".")
            number_text = "".join(parts[:-1]) + "." + parts[-1]

        try:
            number = Decimal(number_text)
            return float(number.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)), currency
        except InvalidOperation:
            return None, currency

    @classmethod
    def _canonicalize_url(cls, url: Optional[str]) -> Optional[str]:
        """Drop fragments and tracking parameters, but preserve product/variant query data."""
        if not url:
            return None
        try:
            parsed = urlsplit(str(url).strip())
            if parsed.scheme.lower() not in ("http", "https") or not parsed.hostname:
                return str(url).strip()
            scheme = parsed.scheme.lower()
            host = parsed.hostname.lower()
            port = parsed.port
            netloc = host
            if port and not ((scheme == "http" and port == 80) or (scheme == "https" and port == 443)):
                netloc = f"{host}:{port}"
            path = parsed.path or "/"
            if path != "/":
                path = re.sub(r"/{2,}", "/", path).rstrip("/") or "/"
            query_items = []
            for key, value in parse_qsl(parsed.query, keep_blank_values=True):
                lowered = key.lower()
                if lowered.startswith("utm_") or lowered in cls.TRACKING_KEYS:
                    continue
                query_items.append((key, value))
            query_items.sort(key=lambda item: (item[0].lower(), item[1]))
            return urlunsplit((scheme, netloc, path, urlencode(query_items, doseq=True), ""))
        except (TypeError, ValueError):
            return str(url).strip()

    def _identity_key(self, product: Dict[str, Any]) -> Optional[str]:
        url = self._canonicalize_url(product.get("url"))
        source = str(product.get("source_domain") or "").strip().lower()
        if not source and (url or self.base_url):
            source = (urlsplit(url or self.base_url).hostname or "").lower()

        # URL is strongest at retailer level and retains meaningful variant parameters.
        if url:
            return f"url:{source}:{url}"

        for field in ("gtin14", "gtin13", "gtin12", "gtin8", "gtin", "ean", "upc", "sku", "product_id", "mpn"):
            value = self._clean_identifier(product.get(field))
            if value:
                normalized = re.sub(r"[^a-z0-9]", "", value.casefold())
                if len(normalized) >= 3:
                    brand = re.sub(r"\W+", "", str(product.get("brand") or "").casefold())
                    return f"{field}:{source}:{brand}:{normalized}"
        # Do not merge by title/price: unrelated products often share both.
        return None

    @staticmethod
    def _is_product_record(product: Dict[str, Any]) -> bool:
        name = str(product.get("name") or product.get("title") or "").strip()
        return bool(name and name.casefold() not in {
            "add to cart", "buy now", "view details", "learn more", "read more"
        })

    @staticmethod
    def _merge_records(existing: Dict[str, Any], incoming: Dict[str, Any]) -> Dict[str, Any]:
        """Fill missing fields and union galleries/variants without overwriting good values."""
        merged = dict(existing)
        for key, value in incoming.items():
            if value in (None, "", [], {}):
                continue
            if merged.get(key) in (None, "", [], {}):
                merged[key] = value
                continue
            if key in ("images", "tags", "features"):
                values = list(merged.get(key) or [])
                for item in value if isinstance(value, list) else [value]:
                    if item not in values:
                        values.append(item)
                merged[key] = values
            elif key == "variants":
                values = list(merged.get(key) or [])
                seen = {
                    str(v.get("variant_id") or v.get("sku") or v.get("name") or "").casefold()
                    for v in values if isinstance(v, dict)
                }
                for variant in value if isinstance(value, list) else []:
                    if not isinstance(variant, dict):
                        continue
                    key_value = str(variant.get("variant_id") or variant.get("sku") or variant.get("name") or "").casefold()
                    if key_value and key_value not in seen:
                        values.append(variant)
                        seen.add(key_value)
                merged[key] = values
        if not merged.get("image_url") and merged.get("images"):
            merged["image_url"] = merged["images"][0]
        return merged

    # Backwards-compatible helper retained for existing callers/tests.
    def _fingerprint(self, product: Dict[str, Any]) -> str:
        return self._identity_key(product) or ""
