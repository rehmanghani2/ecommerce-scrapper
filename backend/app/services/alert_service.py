"""
Price Drop and Stock Alerts Service.
Dispatches real-time notifications to Telegram, Slack, Discord, and Webhooks
whenever a price drop or inventory change is detected during crawls.
"""

import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.alert import AlertConfig, AlertNotificationLog
from app.config import settings

logger = logging.getLogger(__name__)


class AlertService:
    """Service for managing and dispatching price drop and stock alerts."""

    # ---------------------------------------------------------
    # 1. Telegram Dispatcher
    # ---------------------------------------------------------
    async def send_telegram_alert(
        self,
        bot_token: str,
        chat_id: str,
        alert_data: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """Send formatted alert message to Telegram via Bot API."""
        if not bot_token or not chat_id:
            return False, "Telegram requires both bot_token and chat_id"

        alert_type = alert_data.get("alert_type", "price_drop")
        name = alert_data.get("product_name", "Product")
        url = alert_data.get("product_url", "")
        currency = alert_data.get("currency", "USD")
        new_price = alert_data.get("new_price")
        old_price = alert_data.get("old_price")
        drop_pct = alert_data.get("drop_pct", 0.0)

        if alert_type == "price_drop":
            text = (
                f"🚨 *PRICE DROP DETECTED!* (-{drop_pct:.1f}%)\n\n"
                f"📦 *Product:* {name}\n"
                f"💰 *New Price:* `{currency} {new_price}` (was ~{currency} {old_price}~)\n"
                f"📉 *Savings:* `{currency} {round(old_price - new_price, 2)}`\n\n"
                f"🔗 [View Product on Store]({url})"
            )
        elif alert_type == "out_of_stock":
            text = (
                f"⚠️ *OUT OF STOCK ALERT!*\n\n"
                f"📦 *Product:* {name}\n"
                f"Status: Competitor item is now *Sold Out*.\n\n"
                f"🔗 [View Product]({url})"
            )
        else:  # back_in_stock
            text = (
                f"✅ *BACK IN STOCK ALERT!*\n\n"
                f"📦 *Product:* {name}\n"
                f"💰 *Price:* `{currency} {new_price}`\n"
                f"Status: Item is back in stock!\n\n"
                f"🔗 [View Product]({url})"
            )

        endpoint = f"https://api.telegram.org/bot{bot_token.strip()}/sendMessage"
        payload = {
            "chat_id": chat_id.strip(),
            "text": text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": False,
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(endpoint, json=payload)
                if res.status_code == 200:
                    return True, "Telegram message sent successfully"
                data = res.json()
                return False, data.get("description", f"HTTP {res.status_code}")
        except Exception as e:
            return False, f"Telegram connection error: {str(e)}"

    # ---------------------------------------------------------
    # 2. Slack Dispatcher
    # ---------------------------------------------------------
    async def send_slack_alert(
        self,
        webhook_url: str,
        alert_data: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """Send formatted alert to a Slack incoming webhook."""
        if not webhook_url:
            return False, "Slack requires an incoming webhook_url"

        alert_type = alert_data.get("alert_type", "price_drop")
        name = alert_data.get("product_name", "Product")
        url = alert_data.get("product_url", "")
        currency = alert_data.get("currency", "USD")
        new_price = alert_data.get("new_price")
        old_price = alert_data.get("old_price")
        drop_pct = alert_data.get("drop_pct", 0.0)
        img = alert_data.get("image_url")

        if alert_type == "price_drop":
            header_text = f"🚨 Price Drop Alert: -{drop_pct:.1f}% Off!"
            body_text = (
                f"*{name}*\n"
                f"• *New Price:* {currency} {new_price} (was ~{currency} {old_price}~)\n"
                f"• *Discount:* {drop_pct:.1f}%\n"
                f"<{url}|View Product Online>"
            )
        else:
            header_text = f"⚠️ Inventory Alert: {alert_type.replace('_', ' ').title()}"
            body_text = f"*{name}*\nStatus changed for: <{url}|View Product>"

        payload = {
            "blocks": [
                {
                    "type": "header",
                    "text": {"type": "plain_text", "text": header_text}
                },
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": body_text}
                }
            ]
        }

        if img:
            payload["blocks"][1]["accessory"] = {
                "type": "image",
                "image_url": img,
                "alt_text": name[:50]
            }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(webhook_url.strip(), json=payload)
                if res.status_code in (200, 204):
                    return True, "Slack alert delivered successfully"
                return False, f"HTTP {res.status_code}: {res.text[:150]}"
        except Exception as e:
            return False, f"Slack connection error: {str(e)}"

    # ---------------------------------------------------------
    # 3. Discord Dispatcher
    # ---------------------------------------------------------
    async def send_discord_alert(
        self,
        webhook_url: str,
        alert_data: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """Send rich embed alert to a Discord incoming webhook."""
        if not webhook_url:
            return False, "Discord requires a webhook_url"

        alert_type = alert_data.get("alert_type", "price_drop")
        name = alert_data.get("product_name", "Product")
        url = alert_data.get("product_url", "")
        currency = alert_data.get("currency", "USD")
        new_price = alert_data.get("new_price")
        old_price = alert_data.get("old_price")
        drop_pct = alert_data.get("drop_pct", 0.0)
        img = alert_data.get("image_url")

        if alert_type == "price_drop":
            color = 0x10B981  # Green
            title = f"🚨 Price Drop Alert (-{drop_pct:.1f}%)"
            description = f"**[{name}]({url})**\nPrice lowered on competitor website!"
            fields = [
                {"name": "New Price", "value": f"{currency} {new_price}", "inline": True},
                {"name": "Previous Price", "value": f"{currency} {old_price}", "inline": True},
                {"name": "Discount", "value": f"-{drop_pct:.1f}%", "inline": True},
            ]
        elif alert_type == "out_of_stock":
            color = 0xEF4444  # Red
            title = "⚠️ Out of Stock Alert"
            description = f"**[{name}]({url})** is now Sold Out."
            fields = []
        else:
            color = 0xF59E0B  # Amber
            title = "✅ Back in Stock Alert"
            description = f"**[{name}]({url})** is back in stock!"
            fields = [{"name": "Price", "value": f"{currency} {new_price}", "inline": True}]

        payload = {
            "embeds": [
                {
                    "title": title,
                    "description": description,
                    "url": url,
                    "color": color,
                    "fields": fields,
                    "footer": {"text": "E-Commerce Scraper • Price Monitor"},
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            ]
        }
        if img:
            payload["embeds"][0]["thumbnail"] = {"url": img}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(webhook_url.strip(), json=payload)
                if res.status_code in (200, 204):
                    return True, "Discord alert delivered successfully"
                return False, f"HTTP {res.status_code}: {res.text[:150]}"
        except Exception as e:
            return False, f"Discord connection error: {str(e)}"

    # ---------------------------------------------------------
    # 4. Generic Webhook Dispatcher
    # ---------------------------------------------------------
    async def send_generic_webhook_alert(
        self,
        webhook_url: str,
        alert_data: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """Send raw JSON alert to custom Webhook (Zapier, Make, n8n, etc.)."""
        if not webhook_url:
            return False, "Webhook requires a webhook_url"

        payload = {
            "event": "ecommerce_alert",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **alert_data
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(webhook_url.strip(), json=payload)
                if res.status_code in (200, 201, 202, 204):
                    return True, "Webhook delivered successfully"
                return False, f"HTTP {res.status_code}: {res.text[:150]}"
        except Exception as e:
            return False, f"Webhook error: {str(e)}"

    # ---------------------------------------------------------
    # 5. Channel Test Trigger
    # ---------------------------------------------------------
    async def test_channel(self, channel: str, credentials: Dict[str, Any]) -> Tuple[bool, str]:
        """Send a sample test notification to verify channel credentials."""
        sample_data = {
            "alert_type": "price_drop",
            "product_name": "Sony WH-1000XM5 Wireless Headphones",
            "product_url": "https://example.com/products/sony-headphones",
            "currency": "USD",
            "old_price": 399.99,
            "new_price": 329.99,
            "drop_pct": 17.5,
            "image_url": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=300",
        }

        ch = channel.lower()
        if ch == "telegram":
            token = credentials.get("bot_token") or credentials.get("token", "")
            chat_id = credentials.get("chat_id", "")
            return await self.send_telegram_alert(token, chat_id, sample_data)
        elif ch == "slack":
            url = credentials.get("webhook_url", "")
            return await self.send_slack_alert(url, sample_data)
        elif ch == "discord":
            url = credentials.get("webhook_url", "")
            return await self.send_discord_alert(url, sample_data)
        elif ch in ("webhook", "email"):
            url = credentials.get("webhook_url", "")
            return await self.send_generic_webhook_alert(url, sample_data)
        else:
            return False, f"Unsupported channel: {channel}"

    # ---------------------------------------------------------
    # 6. Evaluation & Auto-Trigger
    # ---------------------------------------------------------
    async def process_price_change(
        self,
        db: AsyncSession,
        product_id: int,
        product_name: str,
        product_url: str,
        old_price: float,
        new_price: float,
        currency: str = "USD",
        image_url: Optional[str] = None
    ):
        """
        Evaluate if a price drop triggers an alert across all configured channels.
        """
        if old_price <= 0 or new_price >= old_price:
            return

        drop_pct = round(((old_price - new_price) / old_price) * 100, 2)
        alert_data = {
            "alert_type": "price_drop",
            "product_id": product_id,
            "product_name": product_name,
            "product_url": product_url,
            "currency": currency,
            "old_price": old_price,
            "new_price": new_price,
            "drop_pct": drop_pct,
            "image_url": image_url,
        }

        # Query active AlertConfigs from DB
        stmt = select(AlertConfig).where(AlertConfig.is_active == True)
        res = await db.execute(stmt)
        configs = res.scalars().all()

        for cfg in configs:
            if drop_pct < (cfg.min_drop_percentage or 0.0):
                continue

            creds = {}
            if cfg.credentials:
                try:
                    creds = json.loads(cfg.credentials)
                except Exception:
                    pass

            success = False
            msg = ""
            ch = cfg.channel.lower()

            if ch == "telegram":
                success, msg = await self.send_telegram_alert(
                    creds.get("bot_token", ""),
                    creds.get("chat_id", ""),
                    alert_data
                )
            elif ch == "slack":
                success, msg = await self.send_slack_alert(
                    creds.get("webhook_url", ""),
                    alert_data
                )
            elif ch == "discord":
                success, msg = await self.send_discord_alert(
                    creds.get("webhook_url", ""),
                    alert_data
                )
            elif ch in ("webhook", "email"):
                success, msg = await self.send_generic_webhook_alert(
                    creds.get("webhook_url", ""),
                    alert_data
                )

            # Record audit log
            log = AlertNotificationLog(
                product_id=product_id,
                product_name=product_name,
                product_url=product_url,
                alert_type="price_drop",
                channel=ch,
                old_price=old_price,
                new_price=new_price,
                price_change_percentage=drop_pct,
                currency=currency,
                status="sent" if success else "failed",
                error_message=None if success else msg,
                payload_snapshot=json.dumps(alert_data)
            )
            db.add(log)
            cfg.last_triggered_at = datetime.now(timezone.utc)

        await db.commit()


alert_service = AlertService()
