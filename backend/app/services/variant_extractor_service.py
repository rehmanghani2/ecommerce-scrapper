"""
Deep Variant & Inventory Extractor Service.
Extracts structured product variants (sizes, colors, SKUs, prices, stock quantities, availability)
from JSON-LD, Microdata, Shopify/WooCommerce embedded JSON objects, HTML tables, and select dropdowns.
"""

import json
import logging
import re
from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class VariantExtractorService:
    """Service to detect, parse, and normalize product variations & inventory."""

    @staticmethod
    def extract_variants_from_json_ld(soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """
        Extract variants from schema.org/Product JSON-LD scripts
        (e.g., 'offers' array, 'hasVariant', or 'model').
        """
        variants: List[Dict[str, Any]] = []
        for script in soup.find_all("script", type=lambda t: t and "ld+json" in t):
            try:
                raw_text = script.string
                if not raw_text:
                    continue
                data = json.loads(raw_text)
                items = data if isinstance(data, list) else [data]

                for item in items:
                    if not isinstance(item, dict):
                        continue
                    if item.get("@type") == "Product" or "@graph" in item:
                        graph_items = item.get("@graph", [item])
                        for node in graph_items:
                            if not isinstance(node, dict) or node.get("@type") != "Product":
                                continue

                            # Check 'hasVariant'
                            has_variants = node.get("hasVariant", [])
                            if isinstance(has_variants, list):
                                for hv in has_variants:
                                    if isinstance(hv, dict):
                                        v = VariantExtractorService._parse_json_ld_product(hv)
                                        if v:
                                            variants.append(v)

                            # Check 'offers' array
                            offers = node.get("offers", [])
                            if isinstance(offers, dict):
                                offers = [offers]
                            if isinstance(offers, list) and len(offers) > 1:
                                for off in offers:
                                    if isinstance(off, dict):
                                        v = VariantExtractorService._parse_json_ld_offer(off, node.get("name"))
                                        if v:
                                            variants.append(v)
            except Exception as e:
                logger.debug(f"JSON-LD variant parse error: {e}")
                continue
        return variants

    @staticmethod
    def _parse_json_ld_product(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        name = data.get("name") or data.get("title")
        if not name:
            return None
        
        sku = data.get("sku")
        price = None
        in_stock = True
        stock_status = "In Stock"

        offers = data.get("offers")
        if isinstance(offers, dict):
            price_val = offers.get("price")
            if price_val:
                try:
                    price = float(str(price_val).replace(",", ""))
                except ValueError:
                    pass
            avail = str(offers.get("availability", "")).lower()
            if "outofstock" in avail or "soldout" in avail:
                in_stock = False
                stock_status = "Out of Stock"

        attributes = {}
        for key in ["size", "color", "pattern", "material"]:
            if data.get(key):
                attributes[key] = str(data[key])

        return {
            "name": str(name),
            "sku": str(sku) if sku else None,
            "price": price,
            "in_stock": in_stock,
            "stock_status": stock_status,
            "attributes": attributes,
            "image_url": data.get("image"),
        }

    @staticmethod
    def _parse_json_ld_offer(offer: Dict[str, Any], default_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        name = offer.get("name") or offer.get("description") or default_name
        if not name:
            return None

        price = None
        price_val = offer.get("price")
        if price_val:
            try:
                price = float(str(price_val).replace(",", ""))
            except ValueError:
                pass

        sku = offer.get("sku")
        avail = str(offer.get("availability", "")).lower()
        in_stock = not ("outofstock" in avail or "soldout" in avail)
        stock_status = "In Stock" if in_stock else "Out of Stock"

        return {
            "name": str(name),
            "sku": str(sku) if sku else None,
            "price": price,
            "in_stock": in_stock,
            "stock_status": stock_status,
            "attributes": {},
            "image_url": offer.get("image"),
        }

    @staticmethod
    def extract_variants_from_embedded_scripts(soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """
        Extract variants from embedded JavaScript variables like:
        - window.ShopifyAnalytics.meta.product.variants
        - var meta = {product: {variants: [...]}}
        - data-product_variations attribute
        """
        variants: List[Dict[str, Any]] = []

        # 1. WooCommerce data-product_variations attribute
        form = soup.find("form", class_=lambda c: c and "variations_form" in c)
        if form and form.get("data-product_variations"):
            try:
                raw_json = form.get("data-product_variations")
                parsed = json.loads(raw_json)
                if isinstance(parsed, list):
                    for v in parsed:
                        if not isinstance(v, dict):
                            continue
                        name_parts = []
                        attrs = {}
                        for attr_k, attr_v in v.get("attributes", {}).items():
                            clean_k = attr_k.replace("attribute_pa_", "").replace("attribute_", "").replace("-", " ").title()
                            attrs[clean_k] = attr_v
                            name_parts.append(f"{clean_k}: {attr_v}")

                        price = v.get("display_price") or v.get("display_regular_price")
                        in_stock = v.get("is_in_stock", True)
                        max_qty = v.get("max_qty")

                        variants.append({
                            "variant_id": str(v.get("variation_id", "")),
                            "name": " / ".join(name_parts) if name_parts else (v.get("variation_id") or "Option"),
                            "sku": v.get("sku") or None,
                            "price": float(price) if price else None,
                            "in_stock": in_stock,
                            "stock_quantity": int(max_qty) if max_qty and str(max_qty).isdigit() else None,
                            "stock_status": "In Stock" if in_stock else "Out of Stock",
                            "attributes": attrs,
                            "image_url": v.get("image", {}).get("src") if isinstance(v.get("image"), dict) else None,
                        })
            except Exception as e:
                logger.debug(f"WooCommerce variations parse error: {e}")

        # 2. Shopify or generic JS embedded objects
        for script in soup.find_all("script"):
            script_text = script.string or ""
            if '"variants":[' in script_text or 'variants: [' in script_text:
                try:
                    match = re.search(r'["\']?variants["\']?\s*:\s*(\[\s*\{.*?\}\s*\])', script_text, re.DOTALL)
                    if match:
                        raw_variants = json.loads(match.group(1))
                        for v in raw_variants:
                            if not isinstance(v, dict) or not v.get("title"):
                                continue
                            price_raw = v.get("price")
                            price = None
                            if price_raw:
                                try:
                                    price = float(price_raw) / 100.0 if float(price_raw) > 1000 and "." not in str(price_raw) else float(price_raw)
                                except ValueError:
                                    pass

                            attrs = {}
                            for opt in ["option1", "option2", "option3"]:
                                if v.get(opt):
                                    attrs[f"Option {opt[-1]}"] = v[opt]

                            variants.append({
                                "variant_id": str(v.get("id", "")),
                                "name": v.get("title", "Variant"),
                                "sku": v.get("sku") or None,
                                "price": price,
                                "in_stock": bool(v.get("available", True)),
                                "stock_quantity": v.get("inventory_quantity"),
                                "stock_status": "In Stock" if v.get("available", True) else "Out of Stock",
                                "attributes": attrs,
                                "image_url": v.get("featured_image", {}).get("src") if isinstance(v.get("featured_image"), dict) else None,
                            })
                except Exception as e:
                    logger.debug(f"Shopify embedded script parse error: {e}")
                    continue

        return variants

    @staticmethod
    def extract_variants_from_dom_options(soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """
        Extract size/color dropdowns (<select> with name/id containing size, color, or option).
        """
        variants: List[Dict[str, Any]] = []
        selects = soup.find_all("select")
        
        for sel in selects:
            sel_id = (sel.get("id") or "").lower()
            sel_name = (sel.get("name") or "").lower()
            label = "Option"
            if any(k in sel_id or k in sel_name for k in ["size", "color", "colour", "variant", "dimension", "style"]):
                if "size" in sel_id or "size" in sel_name:
                    label = "Size"
                elif "col" in sel_id or "col" in sel_name:
                    label = "Color"
                
                options = sel.find_all("option")
                for opt in options:
                    text = opt.get_text(strip=True)
                    val = opt.get("value", "").strip()
                    if not text or not val or "choose" in text.lower() or "select" in text.lower():
                        continue

                    # Check for price change in text: e.g. "XL (+$5.00)" or "Out of stock"
                    in_stock = True
                    stock_status = "In Stock"
                    if "out of stock" in text.lower() or "sold out" in text.lower() or opt.get("disabled") is not None:
                        in_stock = False
                        stock_status = "Out of Stock"

                    price_match = re.search(r'[\$£€]?\s*(\d+[.,]\d{2})', text)
                    price = float(price_match.group(1).replace(",", "")) if price_match else None

                    clean_name = re.sub(r'[\(\[\{].*?[\)\]\}]', '', text).strip()

                    variants.append({
                        "name": f"{label}: {clean_name or text}",
                        "sku": None,
                        "price": price,
                        "in_stock": in_stock,
                        "stock_status": stock_status,
                        "attributes": {label: clean_name or text},
                        "image_url": None,
                    })

        return variants

    @staticmethod
    def normalize_variants(raw_variants: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Deduplicate and clean variant records."""
        deduped: List[Dict[str, Any]] = []
        seen_names = set()

        for v in raw_variants:
            name = (v.get("name") or "").strip()
            if not name or name.lower() in seen_names or len(name) < 2:
                continue

            seen_names.add(name.lower())

            # Parse stock status if text specifies 'Only X left'
            stock_qty = v.get("stock_quantity")
            stock_status = v.get("stock_status", "In Stock" if v.get("in_stock", True) else "Out of Stock")
            
            qty_match = re.search(r'only\s+(\d+)\s+left', name, re.IGNORECASE)
            if qty_match:
                stock_qty = int(qty_match.group(1))
                stock_status = f"Only {stock_qty} left"

            deduped.append({
                "variant_id": str(v.get("variant_id", "")) if v.get("variant_id") else None,
                "sku": str(v.get("sku", "")).strip() if v.get("sku") else None,
                "name": name[:255],
                "attributes": v.get("attributes", {}),
                "price": float(v["price"]) if v.get("price") is not None else None,
                "original_price": float(v["original_price"]) if v.get("original_price") is not None else None,
                "in_stock": bool(v.get("in_stock", True)),
                "stock_quantity": stock_qty,
                "stock_status": stock_status,
                "image_url": v.get("image_url"),
            })

        return deduped

    def extract_from_html(self, html: str) -> List[Dict[str, Any]]:
        """Comprehensive variant extraction from arbitrary HTML."""
        try:
            soup = BeautifulSoup(html, "html.parser")
        except Exception:
            return []

        all_variants: List[Dict[str, Any]] = []

        # 1. Embedded scripts (Shopify, WooCommerce, JSON objects)
        embedded = self.extract_variants_from_embedded_scripts(soup)
        if embedded:
            all_variants.extend(embedded)

        # 2. JSON-LD Schema.org offers & hasVariant
        json_ld = self.extract_variants_from_json_ld(soup)
        if json_ld:
            all_variants.extend(json_ld)

        # 3. DOM <select> dropdowns (Sizes, Colors)
        if len(all_variants) < 2:
            dom_variants = self.extract_variants_from_dom_options(soup)
            all_variants.extend(dom_variants)

        return self.normalize_variants(all_variants)


variant_extractor_service = VariantExtractorService()
