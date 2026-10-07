"""
Alerts API routes for Multi-Store Webhook & Slack/Discord Notification Dispatcher.
"""

import json
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from datetime import datetime

from app.models.database import get_db
from app.models.alert import AlertConfig, AlertNotificationLog
from app.services.alert_service import alert_service

router = APIRouter(prefix="/alerts", tags=["Alerts & Multi-Store Notifications"])


def _mask_alert_credentials(channel: str, creds: Dict[str, Any], secret: Optional[str] = None) -> Dict[str, Any]:
    """Mask bot tokens, webhooks, private chat IDs, and HMAC secrets."""
    masked = dict(creds)
    if "bot_token" in masked and masked["bot_token"]:
        token = str(masked["bot_token"])
        masked["bot_token"] = f"{token[:5]}****{token[-4:]}" if len(token) > 9 else "****"
    if "webhook_url" in masked and masked["webhook_url"]:
        url = str(masked["webhook_url"])
        if len(url) > 20:
            prefix, rest = url[:15], url[-6:]
            masked["webhook_url"] = f"{prefix}****{rest}"
        else:
            masked["webhook_url"] = "****"
    if secret:
        masked["hmac_secret"] = f"{secret[:3]}****{secret[-3:]}" if len(secret) > 6 else "****"
    return masked


@router.get("/configs")
async def list_alert_configs(db: AsyncSession = Depends(get_db)):
    """List all configured alert channels with masked credentials and event subscriptions."""
    stmt = select(AlertConfig).order_by(AlertConfig.id.asc())
    res = await db.execute(stmt)
    configs = res.scalars().all()

    result = []
    for cfg in configs:
        creds = {}
        if cfg.credentials:
            try:
                creds = json.loads(cfg.credentials)
            except Exception:
                pass

        events = []
        if cfg.events_subscribed:
            try:
                events = json.loads(cfg.events_subscribed)
            except Exception:
                events = [e.strip() for e in cfg.events_subscribed.split(",")]

        stores = []
        if cfg.store_domains:
            try:
                stores = json.loads(cfg.store_domains)
            except Exception:
                stores = [s.strip() for s in cfg.store_domains.split(",")]

        custom_hdrs = {}
        if cfg.custom_headers:
            try:
                custom_hdrs = json.loads(cfg.custom_headers)
            except Exception:
                pass

        result.append({
            "id": cfg.id,
            "channel": cfg.channel,
            "name": cfg.name,
            "is_active": cfg.is_active,
            "min_drop_percentage": cfg.min_drop_percentage,
            "alert_on_out_of_stock": cfg.alert_on_out_of_stock,
            "alert_on_back_in_stock": cfg.alert_on_back_in_stock,
            "events_subscribed": events,
            "store_domains": stores,
            "has_hmac_secret": bool(cfg.hmac_secret),
            "min_rank_shift": cfg.min_rank_shift,
            "custom_headers": custom_hdrs,
            "masked_credentials": _mask_alert_credentials(cfg.channel, creds, cfg.hmac_secret),
            "last_triggered_at": cfg.last_triggered_at.isoformat() if cfg.last_triggered_at else None,
            "last_tested_at": cfg.last_tested_at.isoformat() if cfg.last_tested_at else None,
            "created_at": cfg.created_at.isoformat() if cfg.created_at else None,
        })
    return result


@router.post("/configs")
async def save_alert_config(payload: Dict[str, Any], db: AsyncSession = Depends(get_db)):
    """Create or update an alert channel configuration."""
    cfg_id = payload.get("id")
    channel = payload.get("channel", "").lower()
    name = payload.get("name") or f"{channel.title()} Alerts"
    is_active = bool(payload.get("is_active", True))
    min_drop_percentage = float(payload.get("min_drop_percentage", 5.0))
    alert_on_out_of_stock = bool(payload.get("alert_on_out_of_stock", True))
    alert_on_back_in_stock = bool(payload.get("alert_on_back_in_stock", True))
    min_rank_shift = int(payload.get("min_rank_shift", 3))
    credentials = payload.get("credentials", {})
    hmac_secret = payload.get("hmac_secret")
    custom_headers = payload.get("custom_headers")

    raw_events = payload.get("events_subscribed", ["price_drop"])
    events_str = json.dumps(raw_events) if isinstance(raw_events, list) else str(raw_events)

    raw_stores = payload.get("store_domains", ["*"])
    stores_str = json.dumps(raw_stores) if isinstance(raw_stores, list) else str(raw_stores)

    if not channel:
        raise HTTPException(status_code=400, detail="Channel is required")

    target = None
    if cfg_id:
        target = await db.get(AlertConfig, cfg_id)

    if not target:
        # Check if single channel record exists without ID
        stmt = select(AlertConfig).where(AlertConfig.channel == channel, AlertConfig.name == name)
        res = await db.execute(stmt)
        target = res.scalar_one_or_none()

    if target:
        target.name = name
        target.channel = channel
        target.is_active = is_active
        target.min_drop_percentage = min_drop_percentage
        target.alert_on_out_of_stock = alert_on_out_of_stock
        target.alert_on_back_in_stock = alert_on_back_in_stock
        target.min_rank_shift = min_rank_shift
        target.events_subscribed = events_str
        target.store_domains = stores_str
        if credentials:
            target.credentials = json.dumps(credentials)
        if hmac_secret is not None:
            target.hmac_secret = hmac_secret if hmac_secret.strip() else None
        if custom_headers is not None:
            target.custom_headers = json.dumps(custom_headers) if isinstance(custom_headers, dict) else custom_headers
        await db.commit()
        await db.refresh(target)
    else:
        target = AlertConfig(
            channel=channel,
            name=name,
            is_active=is_active,
            min_drop_percentage=min_drop_percentage,
            alert_on_out_of_stock=alert_on_out_of_stock,
            alert_on_back_in_stock=alert_on_back_in_stock,
            min_rank_shift=min_rank_shift,
            events_subscribed=events_str,
            store_domains=stores_str,
            hmac_secret=hmac_secret if hmac_secret and hmac_secret.strip() else None,
            custom_headers=json.dumps(custom_headers) if isinstance(custom_headers, dict) else custom_headers,
            credentials=json.dumps(credentials) if credentials else "{}"
        )
        db.add(target)
        await db.commit()
        await db.refresh(target)

    return {"success": True, "id": target.id, "message": f"{name} configuration saved"}


@router.delete("/configs/{config_id}")
async def delete_alert_config(config_id: int, db: AsyncSession = Depends(get_db)):
    """Delete an alert channel configuration."""
    cfg = await db.get(AlertConfig, config_id)
    if not cfg:
        raise HTTPException(status_code=404, detail="Alert config not found")
    await db.delete(cfg)
    await db.commit()
    return {"success": True, "message": "Alert configuration deleted"}


@router.post("/test")
async def test_alert_channel(payload: Dict[str, Any]):
    """Send a live test notification to verify channel credentials and formatting."""
    channel = payload.get("channel", "").lower()
    credentials = payload.get("credentials", {})
    if payload.get("hmac_secret"):
        credentials["hmac_secret"] = payload.get("hmac_secret")

    if not channel:
        raise HTTPException(status_code=400, detail="Channel is required")

    success, message = await alert_service.test_channel(channel, credentials)
    return {"success": success, "message": message}


@router.post("/simulate-webhook")
async def simulate_webhook_payload(payload: Dict[str, Any]):
    """
    Simulates a webhook delivery payload and computes HMAC signature for developer testing.
    """
    event_type = payload.get("event_type", "price_drop")
    secret = payload.get("hmac_secret", "sample_secret_key_123")
    sample_data = {
        "product_id": 42,
        "product_name": "Premium Wireless Noise-Cancelling Headphones",
        "product_url": "https://example.com/item/headphones",
        "store_domain": payload.get("store_domain", "amazon.com"),
        "currency": "USD",
        "old_price": 299.99,
        "new_price": 249.99,
        "drop_pct": 16.67,
        "target_winning_price": 245.0,
    }
    raw_json = json.dumps({"event": event_type, "timestamp": datetime.utcnow().isoformat(), "data": sample_data}, separators=(",", ":"))
    sig = alert_service.compute_hmac_signature(raw_json.encode("utf-8"), secret)
    return {
        "event": event_type,
        "headers": {
            "Content-Type": "application/json",
            "X-Scraper-Event": event_type,
            "X-Scraper-Signature": sig,
        },
        "payload": json.loads(raw_json),
    }


@router.get("/logs")
async def get_alert_logs(
    limit: int = Query(50, ge=1, le=200),
    channel: Optional[str] = Query(None),
    event_type: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve audit history of triggered price drop, stock, buybox, and SERP alerts."""
    stmt = select(AlertNotificationLog).order_by(desc(AlertNotificationLog.id))
    if channel:
        stmt = stmt.where(AlertNotificationLog.channel == channel.lower())
    if event_type:
        stmt = stmt.where(AlertNotificationLog.alert_type == event_type.lower())
    stmt = stmt.limit(limit)

    res = await db.execute(stmt)
    logs = res.scalars().all()
    return logs
