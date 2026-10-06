"""
Automated Competitor Repricing and Price Matching Service.
Calculates optimal competitive pricing based on user rules (beat by %, beat by fixed $, match price)
with margin guardrails (floor and ceiling prices), and executes updates on:
- Shopify (REST Admin API product / variant update)
- WooCommerce (REST API v3 product update)
- Custom Webhook (HTTP POST payload with HMAC signature or bearer token)
"""

import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.repricing import RepricingRule, RepricingLog
from app.models.integration import IntegrationConfig
from app.models.product import Product
from app.services.store_integration_service import store_integration_service

logger = logging.getLogger(__name__)


class RepricingService:
    """Service to evaluate pricing rules and trigger automated repricing actions."""

    @staticmethod
    def calculate_new_price(
        competitor_price: float,
        strategy: str,
        adjustment_value: float,
        min_floor_price: Optional[float] = None,
        max_ceiling_price: Optional[float] = None,
    ) -> Tuple[float, str]:
        """
        Compute new price based on rule strategy with floor and ceiling limits.
        Strategies:
        - 'beat_by_percentage': competitor_price * (1 - adjustment_value / 100)
        - 'beat_by_fixed': competitor_price - adjustment_value
        - 'match_price': competitor_price
        - 'markup_percentage': competitor_price * (1 + adjustment_value / 100)
        """
        price = competitor_price

        if strategy == "beat_by_percentage":
            price = competitor_price * (1.0 - (adjustment_value / 100.0))
        elif strategy == "beat_by_fixed":
            price = competitor_price - adjustment_value
        elif strategy == "match_price":
            price = competitor_price
        elif strategy == "markup_percentage":
            price = competitor_price * (1.0 + (adjustment_value / 100.0))

        price = round(price, 2)
        status = "applied"

        # Margin guardrails
        if min_floor_price is not None and price < float(min_floor_price):
            price = round(float(min_floor_price), 2)
            status = "bounded_by_floor"
        elif max_ceiling_price is not None and price > float(max_ceiling_price):
            price = round(float(max_ceiling_price), 2)
            status = "bounded_by_ceiling"

        return price, status

    async def update_shopify_price_by_sku(
        self,
        shop_url: str,
        access_token: str,
        sku: str,
        new_price: float,
        compare_at_price: Optional[float] = None
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Locate product variant in Shopify by SKU and update its price.
        """
        cleaned_url = store_integration_service._clean_shopify_url(shop_url)
        headers = {
            "X-Shopify-Access-Token": access_token.strip(),
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        # 1. Search product by SKU: GET /admin/api/2024-01/products.json?fields=id,variants
        search_endpoint = f"https://{cleaned_url}/admin/api/2024-01/products.json"
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                res = await client.get(search_endpoint, headers=headers)
                if res.status_code != 200:
                    return False, f"Shopify API error (HTTP {res.status_code}): {res.text[:150]}", None

                products = res.json().get("products", [])
                target_variant_id = None
                for prod in products:
                    for var in prod.get("variants", []):
                        if var.get("sku") and var.get("sku").strip().lower() == sku.strip().lower():
                            target_variant_id = var.get("id")
                            break
                    if target_variant_id:
                        break

                if not target_variant_id:
                    return False, f"Variant with SKU '{sku}' not found in Shopify catalog", None

                # 2. Update variant price: PUT /admin/api/2024-01/variants/{id}.json
                update_endpoint = f"https://{cleaned_url}/admin/api/2024-01/variants/{target_variant_id}.json"
                payload = {
                    "variant": {
                        "id": target_variant_id,
                        "price": f"{new_price:.2f}",
                    }
                }
                if compare_at_price and compare_at_price > new_price:
                    payload["variant"]["compare_at_price"] = f"{compare_at_price:.2f}"

                up_res = await client.put(update_endpoint, json=payload, headers=headers)
                if up_res.status_code in (200, 201):
                    return True, f"Successfully updated Shopify variant {target_variant_id} price to {new_price:.2f}", up_res.json()
                else:
                    return False, f"Shopify update failed (HTTP {up_res.status_code}): {up_res.text[:150]}", None

        except Exception as e:
            logger.error(f"Error updating Shopify variant {sku}: {e}")
            return False, str(e), None

    async def update_woocommerce_price_by_sku(
        self,
        store_url: str,
        consumer_key: str,
        consumer_secret: str,
        sku: str,
        new_price: float,
        regular_price: Optional[float] = None
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Locate product in WooCommerce by SKU and update its price.
        """
        cleaned_url = store_integration_service._clean_wc_url(store_url)
        auth = (consumer_key.strip(), consumer_secret.strip())

        search_endpoint = f"{cleaned_url}/wp-json/wc/v3/products?sku={sku.strip()}"
        try:
            async with httpx.AsyncClient(timeout=20.0, verify=False) as client:
                res = await client.get(search_endpoint, auth=auth)
                if res.status_code != 200:
                    return False, f"WooCommerce search failed (HTTP {res.status_code}): {res.text[:150]}", None

                products = res.json()
                if not products or not isinstance(products, list):
                    return False, f"Product with SKU '{sku}' not found in WooCommerce catalog", None

                wc_product_id = products[0].get("id")

                # Update product price
                update_endpoint = f"{cleaned_url}/wp-json/wc/v3/products/{wc_product_id}"
                payload = {
                    "regular_price": f"{regular_price:.2f}" if regular_price else f"{new_price:.2f}",
                    "sale_price": f"{new_price:.2f}" if regular_price else "",
                }

                up_res = await client.put(update_endpoint, json=payload, auth=auth)
                if up_res.status_code in (200, 201):
                    return True, f"Successfully updated WooCommerce product {wc_product_id} price to {new_price:.2f}", up_res.json()
                else:
                    return False, f"WooCommerce update failed (HTTP {up_res.status_code}): {up_res.text[:150]}", None

        except Exception as e:
            logger.error(f"Error updating WooCommerce product {sku}: {e}")
            return False, str(e), None

    async def trigger_custom_webhook(
        self,
        webhook_url: str,
        payload: Dict[str, Any],
        secret: Optional[str] = None
    ) -> Tuple[bool, str]:
        """Send repricing event payload to user's custom webhook endpoint."""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "ECommerce-Scraper-Repricer/1.0",
        }
        if secret:
            headers["Authorization"] = f"Bearer {secret.strip()}"
            headers["X-Repricer-Secret"] = secret.strip()

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.post(webhook_url, json=payload, headers=headers)
                if 200 <= res.status_code < 300:
                    return True, f"Webhook accepted (HTTP {res.status_code})"
                else:
                    return False, f"Webhook returned HTTP {res.status_code}: {res.text[:150]}"
        except Exception as e:
            return False, f"Webhook connection error: {str(e)}"

    async def evaluate_and_reprice_product(
        self,
        db: AsyncSession,
        product: Product,
        competitor_price: float,
        competitor_domain: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Evaluate active repricing rules against a newly scraped product price and execute updates.
        """
        results: List[Dict[str, Any]] = []

        # Find active rules
        query = select(RepricingRule).where(RepricingRule.is_active == True)
        res = await db.execute(query)
        rules = res.scalars().all()

        for rule in rules:
            # Check domain filter if specified
            if rule.target_domain:
                if not competitor_domain or rule.target_domain.lower() not in competitor_domain.lower():
                    continue

            new_price, guardrail_status = self.calculate_new_price(
                competitor_price=competitor_price,
                strategy=rule.strategy or "beat_by_percentage",
                adjustment_value=rule.adjustment_value or 2.0,
                min_floor_price=float(rule.min_floor_price) if rule.min_floor_price else None,
                max_ceiling_price=float(rule.max_ceiling_price) if rule.max_ceiling_price else None,
            )

            platform = rule.target_platform.lower()
            success = False
            msg = ""
            resp_payload = None

            # Retrieve integration credentials if linked
            creds = {}
            if rule.integration_config_id:
                int_cfg = await db.get(IntegrationConfig, rule.integration_config_id)
                if int_cfg and int_cfg.credentials:
                    try:
                        creds = json.loads(int_cfg.credentials)
                    except Exception:
                        pass

            sku = product.sku or f"PROD-{product.id}"

            if platform == "shopify":
                shop_url = creds.get("shop_url") or creds.get("domain") or ""
                access_token = creds.get("access_token") or ""
                if shop_url and access_token:
                    success, msg, resp_payload = await self.update_shopify_price_by_sku(
                        shop_url=shop_url,
                        access_token=access_token,
                        sku=sku,
                        new_price=new_price,
                        compare_at_price=float(product.previous_price or competitor_price)
                    )
                else:
                    msg = "Missing Shopify credentials in linked IntegrationConfig"

            elif platform == "woocommerce":
                store_url = creds.get("store_url") or creds.get("url") or ""
                ck = creds.get("consumer_key") or ""
                cs = creds.get("consumer_secret") or ""
                if store_url and ck and cs:
                    success, msg, resp_payload = await self.update_woocommerce_price_by_sku(
                        store_url=store_url,
                        consumer_key=ck,
                        consumer_secret=cs,
                        sku=sku,
                        new_price=new_price,
                        regular_price=float(product.previous_price or competitor_price)
                    )
                else:
                    msg = "Missing WooCommerce credentials in linked IntegrationConfig"

            elif platform in ("custom_webhook", "webhook"):
                target_url = rule.webhook_url
                if target_url:
                    event_data = {
                        "event": "price_match_repricing",
                        "rule_id": rule.id,
                        "rule_name": rule.name,
                        "product_id": product.id,
                        "product_name": product.name,
                        "sku": sku,
                        "competitor_domain": competitor_domain,
                        "competitor_price": competitor_price,
                        "calculated_new_price": new_price,
                        "strategy": rule.strategy,
                        "guardrail_status": guardrail_status,
                        "currency": product.currency or "USD",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                    success, msg = await self.trigger_custom_webhook(
                        webhook_url=target_url,
                        payload=event_data,
                        secret=rule.webhook_secret
                    )
                else:
                    msg = "No webhook URL configured for rule"

            # Create audit log
            log = RepricingLog(
                rule_id=rule.id,
                product_id=product.id,
                product_name=product.name,
                product_sku=sku,
                competitor_domain=competitor_domain,
                competitor_price=competitor_price,
                original_store_price=product.price,
                calculated_new_price=new_price,
                currency=product.currency or "USD",
                target_platform=platform,
                status="applied" if success else ("bounded_guardrail" if guardrail_status != "applied" else "failed"),
                reason=f"{guardrail_status}: {msg}",
                response_payload=json.dumps(resp_payload) if resp_payload else None
            )
            db.add(log)

            if success:
                rule.total_repriced = (rule.total_repriced or 0) + 1
            rule.last_triggered_at = datetime.now(timezone.utc)

            results.append({
                "rule_id": rule.id,
                "rule_name": rule.name,
                "new_price": new_price,
                "status": "applied" if success else "failed",
                "message": msg,
            })

        return results


repricing_service = RepricingService()
