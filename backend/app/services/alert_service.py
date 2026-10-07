"""
Multi-Store Automated Webhook & Slack/Discord Notification Dispatcher.
Dispatches real-time notifications to Slack, Discord, Telegram, and authenticated custom Webhooks
whenever price drops, stockouts, Buy Box losses, or SERP rank shifts are detected.
"""

import json
import logging
import hmac
import hashlib
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.alert import AlertConfig, AlertNotificationLog
from app.config import settings

logger = logging.getLogger(__name__)


class AlertService:
    """Service for managing and dispatching multi-store notifications and webhooks."""

    def compute_hmac_signature(self, payload_bytes: bytes, secret: str) -> str:
        """Compute HMAC-SHA256 signature for outbound webhook verification."""
        if not secret:
            return ""
        digest = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
        return f"sha256={digest}"

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
        store = alert_data.get("store_domain", "Store")

        if alert_type == "price_drop":
            new_price = alert_data.get("new_price")
            old_price = alert_data.get("old_price")
            drop_pct = alert_data.get("drop_pct", 0.0)
            text = (
                f"🚨 *PRICE DROP DETECTED!* (-{drop_pct:.1f}%)\n\n"
                f"📦 *Product:* {name}\n"
                f"🏪 *Store:* `{store}`\n"
                f"💰 *New Price:* `{currency} {new_price}` (was ~{currency} {old_price}~)\n"
                f"📉 *Savings:* `{currency} {round(old_price - new_price, 2)}`\n\n"
                f"🔗 [View Product on Store]({url})"
            )
        elif alert_type == "buybox_lost":
            winner = alert_data.get("current_winner", "Competitor")
            winner_price = alert_data.get("winner_price", 0.0)
            target_price = alert_data.get("target_winning_price", 0.0)
            text = (
                f"⚠️ *BUY BOX LOST TO COMPETITOR!*\n\n"
                f"📦 *Product:* {name}\n"
                f"🏪 *Store:* `{store}`\n"
                f"👤 *New Winner:* `{winner}` at `{currency} {winner_price}`\n"
                f"🎯 *Recommended Target Price:* `{currency} {target_price}`\n\n"
                f"🔗 [Inspect Listing]({url})"
            )
        elif alert_type == "buybox_won":
            winner_price = alert_data.get("winner_price", 0.0)
            text = (
                f"🏆 *BUY BOX RECAPTURED!*\n\n"
                f"📦 *Product:* {name}\n"
                f"🏪 *Store:* `{store}`\n"
                f"💰 *Winning Price:* `{currency} {winner_price}`\n\n"
                f"🔗 [View Listing]({url})"
            )
        elif alert_type == "serp_shift":
            kw = alert_data.get("keyword", "Keyword")
            old_r = alert_data.get("old_rank", "?")
            new_r = alert_data.get("new_rank", "?")
            text = (
                f"🔍 *SERP RANKING SHIFT!*\n\n"
                f"📦 *Product:* {name}\n"
                f"🔑 *Keyword:* `{kw}`\n"
                f"📉 *Rank Moved:* `#{old_r}` ➔ `#{new_r}` on `{store}`\n\n"
                f"🔗 [View SERP Target]({url})"
            )
        elif alert_type == "out_of_stock":
            text = (
                f"⚠️ *OUT OF STOCK ALERT!*\n\n"
                f"📦 *Product:* {name}\n"
                f"🏪 *Store:* `{store}`\n"
                f"Status: Item is now *Sold Out*.\n\n"
                f"🔗 [View Product]({url})"
            )
        else:  # back_in_stock
            price = alert_data.get("new_price") or alert_data.get("price")
            text = (
                f"✅ *BACK IN STOCK ALERT!*\n\n"
                f"📦 *Product:* {name}\n"
                f"🏪 *Store:* `{store}`\n"
                f"💰 *Price:* `{currency} {price}`\n\n"
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
        """Send formatted alert to a Slack incoming webhook with rich Blocks."""
        if not webhook_url:
            return False, "Slack requires an incoming webhook_url"

        alert_type = alert_data.get("alert_type", "price_drop")
        name = alert_data.get("product_name", "Product")
        url = alert_data.get("product_url", "")
        currency = alert_data.get("currency", "USD")
        img = alert_data.get("image_url")
        store = alert_data.get("store_domain", "Store")

        if alert_type == "price_drop":
            new_price = alert_data.get("new_price")
            old_price = alert_data.get("old_price")
            drop_pct = alert_data.get("drop_pct", 0.0)
            header_text = f"🚨 Price Drop Alert: -{drop_pct:.1f}% Off!"
            body_text = (
                f"*{name}*\n"
                f"• *New Price:* {currency} {new_price} (was ~{currency} {old_price}~)\n"
                f"• *Savings:* {currency} {round(old_price - new_price, 2)} (-{drop_pct:.1f}%)\n"
                f"• *Store:* `{store}`\n"
                f"<{url}|View Product Online>"
            )
        elif alert_type == "buybox_lost":
            winner = alert_data.get("current_winner", "Competitor")
            winner_price = alert_data.get("winner_price", 0.0)
            target_price = alert_data.get("target_winning_price", 0.0)
            header_text = f"⚠️ Buy Box Lost on {store}"
            body_text = (
                f"*{name}*\n"
                f"• *New Buy Box Owner:* `{winner}`\n"
                f"• *Winning Price:* {currency} {winner_price}\n"
                f"• *Target Price (P*):* {currency} {target_price}\n"
                f"<{url}|Open Listing in Store>"
            )
        elif alert_type == "buybox_won":
            winner_price = alert_data.get("winner_price", 0.0)
            header_text = f"🏆 Buy Box Recaptured on {store}"
            body_text = (
                f"*{name}*\n"
                f"• *Winning Price:* {currency} {winner_price}\n"
                f"• *Status:* Buy Box Active\n"
                f"<{url}|Open Listing in Store>"
            )
        elif alert_type == "serp_shift":
            kw = alert_data.get("keyword", "Keyword")
            old_r = alert_data.get("old_rank", "?")
            new_r = alert_data.get("new_rank", "?")
            header_text = f"🔍 SERP Position Shift on {store}"
            body_text = (
                f"*{name}*\n"
                f"• *Keyword:* `{kw}`\n"
                f"• *Rank Movement:* `#{old_r}` ➔ `#{new_r}`\n"
                f"<{url}|Inspect Keyword Position>"
            )
        else:
            header_text = f"⚠️ Inventory Alert: {alert_type.replace('_', ' ').title()}"
            body_text = f"*{name}*\nStatus changed on `{store}`: <{url}|View Product>"

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
        img = alert_data.get("image_url")
        store = alert_data.get("store_domain", "Store")

        if alert_type == "price_drop":
            new_price = alert_data.get("new_price")
            old_price = alert_data.get("old_price")
            drop_pct = alert_data.get("drop_pct", 0.0)
            color = 0x10B981  # Emerald
            title = f"🚨 Price Drop Alert (-{drop_pct:.1f}%)"
            description = f"**[{name}]({url})**\nPrice lowered on competitor store!"
            fields = [
                {"name": "New Price", "value": f"{currency} {new_price}", "inline": True},
                {"name": "Previous Price", "value": f"{currency} {old_price}", "inline": True},
                {"name": "Discount", "value": f"-{drop_pct:.1f}%", "inline": True},
                {"name": "Store", "value": store, "inline": True},
            ]
        elif alert_type == "buybox_lost":
            winner = alert_data.get("current_winner", "Competitor")
            winner_price = alert_data.get("winner_price", 0.0)
            target_price = alert_data.get("target_winning_price", 0.0)
            color = 0xEF4444  # Rose
            title = "⚠️ Buy Box Lost to Competitor"
            description = f"**[{name}]({url})**\nBuy Box has transitioned to competitor."
            fields = [
                {"name": "New Owner", "value": str(winner), "inline": True},
                {"name": "Competitor Price", "value": f"{currency} {winner_price}", "inline": True},
                {"name": "Target Price (P*)", "value": f"{currency} {target_price}", "inline": True},
                {"name": "Marketplace", "value": store, "inline": True},
            ]
        elif alert_type == "buybox_won":
            winner_price = alert_data.get("winner_price", 0.0)
            color = 0xF59E0B  # Amber
            title = "🏆 Buy Box Recaptured"
            description = f"**[{name}]({url})**\nYour store is now the active Buy Box winner."
            fields = [
                {"name": "Winning Price", "value": f"{currency} {winner_price}", "inline": True},
                {"name": "Marketplace", "value": store, "inline": True},
            ]
        elif alert_type == "serp_shift":
            kw = alert_data.get("keyword", "Keyword")
            old_r = alert_data.get("old_rank", "?")
            new_r = alert_data.get("new_rank", "?")
            color = 0x6366F1  # Indigo
            title = "🔍 Search Ranking Shift"
            description = f"**[{name}]({url})**\nSearch position moved on {store}."
            fields = [
                {"name": "Keyword", "value": kw, "inline": True},
                {"name": "Old Rank", "value": f"#{old_r}", "inline": True},
                {"name": "New Rank", "value": f"#{new_r}", "inline": True},
            ]
        elif alert_type == "out_of_stock":
            color = 0xDC2626
            title = "⚠️ Out of Stock Alert"
            description = f"**[{name}]({url})** is now Sold Out."
            fields = [{"name": "Store", "value": store, "inline": True}]
        else:
            color = 0x10B981
            title = "✅ Back in Stock Alert"
            description = f"**[{name}]({url})** is back in stock!"
            fields = [{"name": "Store", "value": store, "inline": True}]

        payload = {
            "embeds": [
                {
                    "title": title,
                    "description": description,
                    "url": url,
                    "color": color,
                    "fields": fields,
                    "footer": {"text": f"E-Commerce Scraper • {store}"},
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
    # 4. Custom Outbound Webhook with HMAC Signature
    # ---------------------------------------------------------
    async def send_generic_webhook_alert(
        self,
        webhook_url: str,
        alert_data: Dict[str, Any],
        hmac_secret: Optional[str] = None,
        custom_headers: Optional[Dict[str, str]] = None,
    ) -> Tuple[bool, str]:
        """Send authenticated JSON webhook payload with HMAC-SHA256 signature."""
        if not webhook_url:
            return False, "Webhook requires a webhook_url"

        event_type = alert_data.get("alert_type", "ecommerce_alert")
        now_iso = datetime.now(timezone.utc).isoformat()

        payload = {
            "event": alert_data.get("event") or "ecommerce_alert",
            "timestamp": now_iso,
            **alert_data
        }
        payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")

        headers = {
            "Content-Type": "application/json",
            "X-Scraper-Event": event_type,
            "X-Scraper-Timestamp": now_iso,
            "User-Agent": "EcommerceScraper-Webhook/2.0",
        }

        if hmac_secret:
            sig = self.compute_hmac_signature(payload_bytes, hmac_secret)
            headers["X-Scraper-Signature"] = sig

        if custom_headers:
            headers.update(custom_headers)

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(webhook_url.strip(), json=payload, headers=headers)
                if res.status_code in (200, 201, 202, 204):
                    return True, f"Webhook delivered successfully (HTTP {res.status_code})"
                return False, f"HTTP {res.status_code}: {res.text[:150]}"
        except Exception as e:
            return False, f"Webhook connection error: {str(e)}"

    # ---------------------------------------------------------
    # 5. Channel Test Trigger
    # ---------------------------------------------------------
    async def test_channel(self, channel: str, credentials: Dict[str, Any]) -> Tuple[bool, str]:
        """Send a sample test notification to verify channel credentials."""
        sample_data = {
            "alert_type": "price_drop",
            "product_name": "Sony WH-1000XM5 Wireless Headphones",
            "product_url": "https://example.com/products/sony-headphones",
            "store_domain": "amazon.com",
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
            secret = credentials.get("hmac_secret")
            return await self.send_generic_webhook_alert(url, sample_data, hmac_secret=secret)
        else:
            return False, f"Unsupported channel: {channel}"

    # ---------------------------------------------------------
    # 6. Core Dispatch Orchestrator & Event Subscriptions
    # ---------------------------------------------------------
    def _is_config_eligible(
        self,
        cfg: AlertConfig,
        event_type: str,
        store_domain: Optional[str] = None
    ) -> bool:
        """Determines if an AlertConfig subscribes to this event and store domain."""
        if not cfg.is_active:
            return False

        # 1. Event subscription check
        subscribed_events: List[str] = []
        if cfg.events_subscribed:
            try:
                parsed = json.loads(cfg.events_subscribed)
                subscribed_events = parsed if isinstance(parsed, list) else [str(parsed)]
            except Exception:
                subscribed_events = [e.strip() for e in cfg.events_subscribed.split(",")]
        else:
            subscribed_events = ["price_drop"]

        # Backward compatibility for out_of_stock flags
        if event_type == "out_of_stock" and cfg.alert_on_out_of_stock:
            subscribed_events.append("out_of_stock")
        if event_type == "back_in_stock" and cfg.alert_on_back_in_stock:
            subscribed_events.append("back_in_stock")

        if "*" not in subscribed_events and event_type not in subscribed_events:
            return False

        # 2. Store domain filter check
        if store_domain and cfg.store_domains:
            try:
                parsed_stores = json.loads(cfg.store_domains)
                store_list = parsed_stores if isinstance(parsed_stores, list) else [str(parsed_stores)]
            except Exception:
                store_list = [s.strip().lower() for s in cfg.store_domains.split(",")]

            clean_store = store_domain.strip().lower()
            if "*" not in store_list and clean_store not in store_list and not any(s in clean_store for s in store_list):
                return False

        return True

    async def dispatch_event(
        self,
        db: AsyncSession,
        event_type: str,
        alert_data: Dict[str, Any],
        store_domain: Optional[str] = None,
        product_id: Optional[int] = None,
        product_name: str = "Unknown",
        product_url: Optional[str] = None,
    ):
        """
        Dispatches an event across all matching AlertConfig channels and writes audit logs.
        """
        stmt = select(AlertConfig).where(AlertConfig.is_active == True)
        res = await db.execute(stmt)
        configs = res.scalars().all()

        alert_data["alert_type"] = event_type
        if store_domain:
            alert_data["store_domain"] = store_domain

        for cfg in configs:
            if not self._is_config_eligible(cfg, event_type, store_domain):
                continue

            # Additional event-specific threshold checks
            if event_type == "price_drop":
                drop_pct = alert_data.get("drop_pct", 0.0)
                if drop_pct < (cfg.min_drop_percentage or 0.0):
                    continue
            elif event_type == "serp_shift":
                rank_diff = abs(int(alert_data.get("new_rank", 0)) - int(alert_data.get("old_rank", 0)))
                if rank_diff < (cfg.min_rank_shift or 3):
                    continue

            creds = {}
            if cfg.credentials:
                try:
                    creds = json.loads(cfg.credentials)
                except Exception:
                    pass

            ch = (cfg.channel or "").lower()
            success = False
            msg = ""

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
                custom_hdr = None
                if cfg.custom_headers:
                    try:
                        custom_hdr = json.loads(cfg.custom_headers)
                    except Exception:
                        pass
                success, msg = await self.send_generic_webhook_alert(
                    creds.get("webhook_url", ""),
                    alert_data,
                    hmac_secret=cfg.hmac_secret,
                    custom_headers=custom_hdr,
                )

            # Record audit log
            log = AlertNotificationLog(
                product_id=product_id,
                product_name=product_name,
                product_url=product_url,
                store_domain=store_domain,
                alert_type=event_type,
                channel=ch,
                old_price=alert_data.get("old_price"),
                new_price=alert_data.get("new_price") or alert_data.get("winner_price"),
                price_change_percentage=alert_data.get("drop_pct"),
                currency=alert_data.get("currency", "USD"),
                status="sent" if success else "failed",
                error_message=None if success else msg,
                payload_snapshot=json.dumps(alert_data),
            )
            db.add(log)
            cfg.last_triggered_at = datetime.now(timezone.utc)

        await db.commit()

    # ---------------------------------------------------------
    # 7. Specialized High-Level Event Handlers
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
        image_url: Optional[str] = None,
        store_domain: Optional[str] = None
    ):
        """Evaluate and dispatch price drop alerts."""
        if old_price <= 0 or new_price >= old_price:
            return

        drop_pct = round(((old_price - new_price) / old_price) * 100, 2)
        alert_data = {
            "product_id": product_id,
            "product_name": product_name,
            "product_url": product_url,
            "currency": currency,
            "old_price": old_price,
            "new_price": new_price,
            "drop_pct": drop_pct,
            "image_url": image_url,
            "store_domain": store_domain,
        }
        await self.dispatch_event(
            db=db,
            event_type="price_drop",
            alert_data=alert_data,
            store_domain=store_domain,
            product_id=product_id,
            product_name=product_name,
            product_url=product_url
        )

    async def process_buybox_change(
        self,
        db: AsyncSession,
        product_id: int,
        product_name: str,
        product_url: str,
        event_type: str,  # 'lost', 'won', 'suppressed'
        current_winner: str,
        winner_price: float,
        target_winning_price: float,
        store_domain: Optional[str] = None,
        currency: str = "USD",
        image_url: Optional[str] = None
    ):
        """Dispatch Buy Box state change alerts (won, lost, suppressed)."""
        normalized_event = f"buybox_{event_type}" if not event_type.startswith("buybox_") else event_type
        alert_data = {
            "product_id": product_id,
            "product_name": product_name,
            "product_url": product_url,
            "current_winner": current_winner,
            "winner_price": winner_price,
            "target_winning_price": target_winning_price,
            "store_domain": store_domain,
            "currency": currency,
            "image_url": image_url,
        }
        await self.dispatch_event(
            db=db,
            event_type=normalized_event,
            alert_data=alert_data,
            store_domain=store_domain,
            product_id=product_id,
            product_name=product_name,
            product_url=product_url
        )

    async def process_stock_change(
        self,
        db: AsyncSession,
        product_id: int,
        product_name: str,
        product_url: str,
        is_in_stock: bool,
        store_domain: Optional[str] = None,
        currency: str = "USD",
        new_price: Optional[float] = None
    ):
        """Dispatch stockout or back-in-stock alerts."""
        event_type = "back_in_stock" if is_in_stock else "out_of_stock"
        alert_data = {
            "product_id": product_id,
            "product_name": product_name,
            "product_url": product_url,
            "is_in_stock": is_in_stock,
            "store_domain": store_domain,
            "currency": currency,
            "new_price": new_price,
        }
        await self.dispatch_event(
            db=db,
            event_type=event_type,
            alert_data=alert_data,
            store_domain=store_domain,
            product_id=product_id,
            product_name=product_name,
            product_url=product_url
        )

    async def process_serp_change(
        self,
        db: AsyncSession,
        product_id: Optional[int],
        product_name: str,
        product_url: str,
        keyword: str,
        old_rank: int,
        new_rank: int,
        store_domain: Optional[str] = None
    ):
        """Dispatch SERP rank movement alerts."""
        alert_data = {
            "product_id": product_id,
            "product_name": product_name,
            "product_url": product_url,
            "keyword": keyword,
            "old_rank": old_rank,
            "new_rank": new_rank,
            "store_domain": store_domain,
        }
        await self.dispatch_event(
            db=db,
            event_type="serp_shift",
            alert_data=alert_data,
            store_domain=store_domain,
            product_id=product_id,
            product_name=product_name,
            product_url=product_url
        )


alert_service = AlertService()
