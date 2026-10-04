"""
Store and Cloud Integration Service.
Handles 1-Click Sync and Template Exports for:
- Shopify (REST Admin API & Shopify-ready CSV)
- WooCommerce (REST API v3 & WooCommerce-ready CSV)
- Google Sheets (Webhook / Apps Script & Clean Sheets CSV)
"""

import io
import csv
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import httpx

from app.models.product import Product

logger = logging.getLogger(__name__)


class StoreIntegrationService:
    """Service to handle integrations with Shopify, WooCommerce, and Google Sheets."""

    # -------------------------------------------------------------
    # 1. SHOPIFY INTEGRATION
    # -------------------------------------------------------------
    @staticmethod
    def _clean_shopify_url(shop_url: str) -> str:
        """Normalize Shopify store URL to host format: example.myshopify.com"""
        url = shop_url.strip().lower()
        url = url.replace("https://", "").replace("http://", "").rstrip("/")
        if not url.endswith(".myshopify.com") and "." not in url:
            url = f"{url}.myshopify.com"
        return url

    async def test_shopify(self, shop_url: str, access_token: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Verify Shopify Admin API credentials by calling shop.json."""
        cleaned_url = self._clean_shopify_url(shop_url)
        endpoint = f"https://{cleaned_url}/admin/api/2024-01/shop.json"
        headers = {
            "X-Shopify-Access-Token": access_token.strip(),
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.get(endpoint, headers=headers)
                if res.status_code == 200:
                    shop_data = res.json().get("shop", {})
                    return True, "Shopify connection successful!", {
                        "name": shop_data.get("name"),
                        "domain": shop_data.get("domain") or cleaned_url,
                        "email": shop_data.get("email"),
                        "currency": shop_data.get("currency"),
                    }
                elif res.status_code == 401 or res.status_code == 403:
                    return False, "Shopify authentication failed. Check your Access Token.", None
                else:
                    return False, f"Shopify returned HTTP {res.status_code}: {res.text[:200]}", None
        except Exception as e:
            return False, f"Failed to connect to Shopify: {str(e)}", None

    async def push_to_shopify(
        self,
        products: List[Product],
        shop_url: str,
        access_token: str,
        publish_status: str = "draft"
    ) -> Dict[str, Any]:
        """Push products directly into Shopify catalog via Admin API."""
        cleaned_url = self._clean_shopify_url(shop_url)
        endpoint = f"https://{cleaned_url}/admin/api/2024-01/products.json"
        headers = {
            "X-Shopify-Access-Token": access_token.strip(),
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        synced = 0
        failed = 0
        items_result = []

        async with httpx.AsyncClient(timeout=30.0) as client:
            for p in products:
                # Format price
                price_str = f"{p.price:.2f}" if p.price is not None else "0.00"
                compare_at = f"{p.previous_price:.2f}" if (p.previous_price and p.price and p.previous_price > p.price) else None

                # Build body HTML
                body_parts = []
                if p.description:
                    body_parts.append(f"<p>{p.description}</p>")
                if p.url:
                    body_parts.append(f"<p><small>Scraped from: <a href='{p.url}' target='_blank'>{p.source_domain or p.url}</a></small></p>")
                body_html = "".join(body_parts)

                tags = ["scraped", "ecommerce-scraper"]
                if p.source_domain:
                    tags.append(p.source_domain.replace(".", "-"))
                if p.brand:
                    tags.append(p.brand)

                images = []
                if p.image_url and p.image_url.startswith("http"):
                    images.append({"src": p.image_url})

                payload = {
                    "product": {
                        "title": p.name or "Imported Product",
                        "body_html": body_html,
                        "vendor": p.brand or p.source_domain or "Scraper Import",
                        "product_type": p.category or "General",
                        "status": "active" if publish_status == "active" else "draft",
                        "tags": ", ".join(tags),
                        "variants": [
                            {
                                "price": price_str,
                                "compare_at_price": compare_at,
                                "sku": p.sku or f"SCRP-{p.id}",
                                "requires_shipping": True,
                                "inventory_management": "shopify" if p.in_stock else None,
                            }
                        ],
                        "images": images,
                    }
                }

                try:
                    res = await client.post(endpoint, json=payload, headers=headers)
                    if res.status_code in (200, 201):
                        res_json = res.json().get("product", {})
                        ext_id = str(res_json.get("id"))
                        ext_url = f"https://{cleaned_url}/admin/products/{ext_id}"
                        synced += 1
                        items_result.append({
                            "product_id": p.id,
                            "name": p.name,
                            "status": "success",
                            "external_id": ext_id,
                            "external_url": ext_url,
                        })
                    else:
                        failed += 1
                        err_text = res.text[:200]
                        items_result.append({
                            "product_id": p.id,
                            "name": p.name,
                            "status": "failed",
                            "error": f"HTTP {res.status_code}: {err_text}",
                        })
                except Exception as e:
                    failed += 1
                    items_result.append({
                        "product_id": p.id,
                        "name": p.name,
                        "status": "failed",
                        "error": str(e),
                    })

        return {
            "success": synced > 0 or failed == 0,
            "platform": "shopify",
            "total": len(products),
            "synced": synced,
            "failed": failed,
            "items": items_result,
            "message": f"Shopify Sync: {synced} synced, {failed} failed out of {len(products)} products.",
        }

    @staticmethod
    def generate_shopify_csv(products: List[Product]) -> str:
        """Generate official Shopify Product CSV format."""
        output = io.StringIO()
        fieldnames = [
            "Handle", "Title", "Body (HTML)", "Vendor", "Product Category", "Type",
            "Tags", "Published", "Option1 Name", "Option1 Value", "Variant SKU",
            "Variant Grams", "Variant Inventory Tracker", "Variant Inventory Qty",
            "Variant Inventory Policy", "Variant Fulfillment Service", "Variant Price",
            "Variant Compare At Price", "Variant Requires Shipping", "Variant Taxable",
            "Variant Barcode", "Image Src", "Image Position", "Image Alt Text",
            "Gift Card", "SEO Title", "SEO Description", "Google Shopping / Google Product Category",
            "Google Shopping / Gender", "Google Shopping / Age Group", "Google Shopping / MPN",
            "Google Shopping / Condition", "Google Shopping / Custom Product", "Google Shopping / Custom Label 0",
            "Status"
        ]

        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        for p in products:
            title = p.name or "Product"
            handle = "".join(c if c.isalnum() else "-" for c in title.lower()).strip("-")[:60]
            if not handle:
                handle = f"product-{p.id}"

            price_str = f"{p.price:.2f}" if p.price is not None else "0.00"
            compare_at = f"{p.previous_price:.2f}" if (p.previous_price and p.price and p.previous_price > p.price) else ""

            body = f"<p>{p.description or ''}</p>"
            if p.url:
                body += f"<p><small>Source: <a href='{p.url}'>{p.source_domain or 'Link'}</a></small></p>"

            row = {
                "Handle": handle,
                "Title": title,
                "Body (HTML)": body,
                "Vendor": p.brand or p.source_domain or "Scraper Import",
                "Product Category": p.category or "",
                "Type": p.category or "General",
                "Tags": f"scraped, {p.source_domain or ''}, {p.brand or ''}".strip(", "),
                "Published": "true",
                "Option1 Name": "Title",
                "Option1 Value": "Default Title",
                "Variant SKU": p.sku or f"SCRP-{p.id}",
                "Variant Grams": "0",
                "Variant Inventory Tracker": "shopify" if p.in_stock else "",
                "Variant Inventory Qty": "100" if p.in_stock else "0",
                "Variant Inventory Policy": "deny",
                "Variant Fulfillment Service": "manual",
                "Variant Price": price_str,
                "Variant Compare At Price": compare_at,
                "Variant Requires Shipping": "true",
                "Variant Taxable": "true",
                "Variant Barcode": "",
                "Image Src": p.image_url or "",
                "Image Position": "1" if p.image_url else "",
                "Image Alt Text": title if p.image_url else "",
                "Gift Card": "FALSE",
                "SEO Title": title,
                "SEO Description": (p.description or "")[:155],
                "Google Shopping / Google Product Category": "",
                "Google Shopping / Gender": "",
                "Google Shopping / Age Group": "",
                "Google Shopping / MPN": p.sku or "",
                "Google Shopping / Condition": "new",
                "Google Shopping / Custom Product": "FALSE",
                "Google Shopping / Custom Label 0": p.source_domain or "",
                "Status": "draft",
            }
            writer.writerow(row)

        return output.getvalue()

    # -------------------------------------------------------------
    # 2. WOOCOMMERCE INTEGRATION
    # -------------------------------------------------------------
    @staticmethod
    def _clean_wc_url(store_url: str) -> str:
        """Normalize WooCommerce store URL with https://"""
        url = store_url.strip()
        if not url.startswith("http://") and not url.startswith("https://"):
            url = f"https://{url}"
        return url.rstrip("/")

    async def test_woocommerce(
        self,
        store_url: str,
        consumer_key: str,
        consumer_secret: str
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Verify WooCommerce REST API credentials."""
        cleaned_url = self._clean_wc_url(store_url)
        endpoint = f"{cleaned_url}/wp-json/wc/v3/system_status"
        auth = (consumer_key.strip(), consumer_secret.strip())

        try:
            async with httpx.AsyncClient(timeout=15.0, verify=False) as client:
                res = await client.get(endpoint, auth=auth)
                if res.status_code == 200:
                    status_data = res.json().get("environment", {})
                    return True, "WooCommerce connection successful!", {
                        "site_url": status_data.get("site_url", cleaned_url),
                        "wc_version": status_data.get("version"),
                        "wp_version": status_data.get("wp_version"),
                    }
                # Try fallback products endpoint if system_status is restricted
                fallback_ep = f"{cleaned_url}/wp-json/wc/v3/products?per_page=1"
                fb_res = await client.get(fallback_ep, auth=auth)
                if fb_res.status_code == 200:
                    return True, "WooCommerce credentials verified successfully!", {"site_url": cleaned_url}
                elif fb_res.status_code in (401, 403):
                    return False, "WooCommerce authentication failed. Check Consumer Key and Consumer Secret.", None
                else:
                    return False, f"WooCommerce returned HTTP {fb_res.status_code}: {fb_res.text[:200]}", None
        except Exception as e:
            return False, f"Failed to connect to WooCommerce: {str(e)}", None

    async def push_to_woocommerce(
        self,
        products: List[Product],
        store_url: str,
        consumer_key: str,
        consumer_secret: str,
        publish_status: str = "publish"
    ) -> Dict[str, Any]:
        """Push products directly into WooCommerce catalog via REST API."""
        cleaned_url = self._clean_wc_url(store_url)
        endpoint = f"{cleaned_url}/wp-json/wc/v3/products"
        auth = (consumer_key.strip(), consumer_secret.strip())

        synced = 0
        failed = 0
        items_result = []

        async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
            for p in products:
                price_str = f"{p.price:.2f}" if p.price is not None else ""
                sale_price = f"{p.price:.2f}" if (p.previous_price and p.price and p.previous_price > p.price) else ""
                regular_price = f"{p.previous_price:.2f}" if sale_price else price_str

                images = []
                if p.image_url and p.image_url.startswith("http"):
                    images.append({"src": p.image_url, "alt": p.name or "Product"})

                categories = []
                if p.category:
                    categories.append({"name": p.category})

                payload = {
                    "name": p.name or "Imported Product",
                    "type": "simple",
                    "status": "publish" if publish_status in ("publish", "active") else "draft",
                    "regular_price": regular_price,
                    "sale_price": sale_price,
                    "description": p.description or "",
                    "short_description": (p.description or "")[:200],
                    "sku": p.sku or f"WC-SCRP-{p.id}",
                    "categories": categories,
                    "images": images,
                    "manage_stock": False,
                    "in_stock": p.in_stock if p.in_stock is not None else True,
                    "meta_data": [
                        {"key": "scraped_source_url", "value": p.url or ""},
                        {"key": "scraped_domain", "value": p.source_domain or ""},
                    ],
                }

                try:
                    res = await client.post(endpoint, json=payload, auth=auth)
                    if res.status_code in (200, 201):
                        res_json = res.json()
                        ext_id = str(res_json.get("id"))
                        ext_url = res_json.get("permalink") or f"{cleaned_url}/?p={ext_id}"
                        synced += 1
                        items_result.append({
                            "product_id": p.id,
                            "name": p.name,
                            "status": "success",
                            "external_id": ext_id,
                            "external_url": ext_url,
                        })
                    else:
                        failed += 1
                        items_result.append({
                            "product_id": p.id,
                            "name": p.name,
                            "status": "failed",
                            "error": f"HTTP {res.status_code}: {res.text[:200]}",
                        })
                except Exception as e:
                    failed += 1
                    items_result.append({
                        "product_id": p.id,
                        "name": p.name,
                        "status": "failed",
                        "error": str(e),
                    })

        return {
            "success": synced > 0 or failed == 0,
            "platform": "woocommerce",
            "total": len(products),
            "synced": synced,
            "failed": failed,
            "items": items_result,
            "message": f"WooCommerce Sync: {synced} synced, {failed} failed out of {len(products)} products.",
        }

    @staticmethod
    def generate_woocommerce_csv(products: List[Product]) -> str:
        """Generate official WooCommerce Product CSV template."""
        output = io.StringIO()
        fieldnames = [
            "ID", "Type", "SKU", "Name", "Published", "Is featured?", "Visibility in catalog",
            "Short description", "Description", "Date sale price starts", "Date sale price ends",
            "Tax status", "Tax class", "In stock?", "Stock", "Backorders allowed?", "Sold individually?",
            "Weight (kg)", "Length (cm)", "Width (cm)", "Height (cm)", "Allow customer reviews?",
            "Purchase note", "Sale price", "Regular price", "Categories", "Tags", "Shipping class",
            "Images", "Download limit", "Download expiry days", "Parent", "Grouped products",
            "Upsells", "Cross-sells", "External URL", "Button text", "Position"
        ]

        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        for p in products:
            price_str = f"{p.price:.2f}" if p.price is not None else ""
            sale_price = f"{p.price:.2f}" if (p.previous_price and p.price and p.previous_price > p.price) else ""
            regular_price = f"{p.previous_price:.2f}" if sale_price else price_str

            row = {
                "ID": "",
                "Type": "simple",
                "SKU": p.sku or f"WC-SCRP-{p.id}",
                "Name": p.name or "Product",
                "Published": "1",
                "Is featured?": "0",
                "Visibility in catalog": "visible",
                "Short description": (p.description or "")[:200],
                "Description": p.description or "",
                "Date sale price starts": "",
                "Date sale price ends": "",
                "Tax status": "taxable",
                "Tax class": "",
                "In stock?": "1" if p.in_stock else "0",
                "Stock": "100" if p.in_stock else "0",
                "Backorders allowed?": "0",
                "Sold individually?": "0",
                "Weight (kg)": "",
                "Length (cm)": "",
                "Width (cm)": "",
                "Height (cm)": "",
                "Allow customer reviews?": "1",
                "Purchase note": "",
                "Sale price": sale_price,
                "Regular price": regular_price,
                "Categories": p.category or "",
                "Tags": f"{p.source_domain or ''}, {p.brand or ''}".strip(", "),
                "Shipping class": "",
                "Images": p.image_url or "",
                "Download limit": "",
                "Download expiry days": "",
                "Parent": "",
                "Grouped products": "",
                "Upsells": "",
                "Cross-sells": "",
                "External URL": p.url or "",
                "Button text": "Buy Product",
                "Position": "0",
            }
            writer.writerow(row)

        return output.getvalue()

    # -------------------------------------------------------------
    # 3. GOOGLE SHEETS / WEBHOOK INTEGRATION
    # -------------------------------------------------------------
    async def test_google_sheets(self, webhook_url: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Test Google Sheets Apps Script or Webhook URL."""
        url = webhook_url.strip()
        test_payload = {
            "action": "ping",
            "message": "Test connection from Ecommerce Scraper Platform",
            "timestamp": datetime.utcnow().isoformat(),
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.post(url, json=test_payload)
                if res.status_code in (200, 201, 302):
                    return True, "Google Sheets Webhook responded successfully!", {
                        "status_code": res.status_code,
                        "response": res.text[:200]
                    }
                else:
                    return False, f"Webhook returned HTTP {res.status_code}: {res.text[:200]}", None
        except Exception as e:
            return False, f"Failed to reach Google Sheets Webhook: {str(e)}", None

    async def push_to_google_sheets(
        self,
        products: List[Product],
        webhook_url: str
    ) -> Dict[str, Any]:
        """Push structured product data to Google Sheets via Webhook/Apps Script."""
        url = webhook_url.strip()
        data = [
            {
                "id": p.id,
                "name": p.name,
                "price": p.price,
                "currency": p.currency or "USD",
                "previous_price": p.previous_price,
                "price_change": p.price_change,
                "in_stock": "In Stock" if p.in_stock else "Out of Stock",
                "brand": p.brand or "",
                "category": p.category or "",
                "source_domain": p.source_domain or "",
                "url": p.url or "",
                "image_url": p.image_url or "",
                "scraped_at": p.scraped_at.isoformat() if p.scraped_at else datetime.utcnow().isoformat(),
            }
            for p in products
        ]

        payload = {
            "action": "append_products",
            "timestamp": datetime.utcnow().isoformat(),
            "count": len(products),
            "products": data,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                res = await client.post(url, json=payload)
                if res.status_code in (200, 201, 302):
                    items = [
                        {"product_id": p.id, "name": p.name, "status": "success", "external_id": str(p.id)}
                        for p in products
                    ]
                    return {
                        "success": True,
                        "platform": "google_sheets",
                        "total": len(products),
                        "synced": len(products),
                        "failed": 0,
                        "items": items,
                        "message": f"Successfully synced {len(products)} products to Google Sheets!",
                    }
                else:
                    return {
                        "success": False,
                        "platform": "google_sheets",
                        "total": len(products),
                        "synced": 0,
                        "failed": len(products),
                        "items": [],
                        "message": f"Google Sheets Webhook returned HTTP {res.status_code}: {res.text[:200]}",
                    }
        except Exception as e:
            return {
                "success": False,
                "platform": "google_sheets",
                "total": len(products),
                "synced": 0,
                "failed": len(products),
                "items": [],
                "message": f"Error posting to Google Sheets webhook: {str(e)}",
            }

    @staticmethod
    def generate_google_sheets_csv(products: List[Product]) -> str:
        """Generate clean CSV formatted for easy copy-pasting or importing into Google Sheets."""
        output = io.StringIO()
        fieldnames = [
            "ID", "Product Name", "Price", "Previous Price", "Price Change (%)", "Currency",
            "Availability", "Brand", "Category", "Rating", "Source Domain", "Product URL",
            "Image URL", "Date Scraped"
        ]

        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        for p in products:
            price_change_str = ""
            if p.price_change_percentage is not None:
                price_change_str = f"{p.price_change_percentage:+.1f}%"

            row = {
                "ID": p.id,
                "Product Name": p.name or "",
                "Price": f"{p.price:.2f}" if p.price is not None else "",
                "Previous Price": f"{p.previous_price:.2f}" if p.previous_price is not None else "",
                "Price Change (%)": price_change_str,
                "Currency": p.currency or "USD",
                "Availability": "In Stock" if p.in_stock else "Out of Stock",
                "Brand": p.brand or "",
                "Category": p.category or "",
                "Rating": f"{p.rating:.1f}" if p.rating is not None else "",
                "Source Domain": p.source_domain or "",
                "Product URL": p.url or "",
                "Image URL": p.image_url or "",
                "Date Scraped": p.scraped_at.strftime("%Y-%m-%d %H:%M") if p.scraped_at else "",
            }
            writer.writerow(row)

        return output.getvalue()


store_integration_service = StoreIntegrationService()
