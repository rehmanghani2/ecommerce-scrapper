"""
Alerts API routes for Price Drop & Stock Notifications (Telegram, Slack, Discord, Webhook).
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

router = APIRouter(prefix="/alerts", tags=["Alerts"])


def _mask_alert_credentials(channel: str, creds: Dict[str, Any]) -> Dict[str, Any]:
    """Mask bot tokens, webhooks, and private chat IDs."""
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
    return masked


@router.get("/configs")
async def list_alert_configs(db: AsyncSession = Depends(get_db)):
    """List all configured alert channels with masked credentials."""
    stmt = select(AlertConfig).order_by(AlertConfig.id)
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
        result.append({
            "id": cfg.id,
            "channel": cfg.channel,
            "name": cfg.name,
            "is_active": cfg.is_active,
            "min_drop_percentage": cfg.min_drop_percentage,
            "alert_on_out_of_stock": cfg.alert_on_out_of_stock,
            "alert_on_back_in_stock": cfg.alert_on_back_in_stock,
            "masked_credentials": _mask_alert_credentials(cfg.channel, creds),
            "last_triggered_at": cfg.last_triggered_at,
            "last_tested_at": cfg.last_tested_at,
            "created_at": cfg.created_at,
        })
    return result


@router.post("/configs")
async def save_alert_config(payload: Dict[str, Any], db: AsyncSession = Depends(get_db)):
    """Create or update an alert channel configuration."""
    channel = payload.get("channel", "").lower()
    name = payload.get("name") or f"{channel.title()} Alerts"
    is_active = payload.get("is_active", True)
    min_drop_percentage = float(payload.get("min_drop_percentage", 5.0))
    alert_on_out_of_stock = bool(payload.get("alert_on_out_of_stock", True))
    alert_on_back_in_stock = bool(payload.get("alert_on_back_in_stock", True))
    credentials = payload.get("credentials", {})

    if not channel:
        raise HTTPException(status_code=400, detail="Channel is required")

    stmt = select(AlertConfig).where(AlertConfig.channel == channel)
    res = await db.execute(stmt)
    existing = res.scalar_one_or_none()

    if existing:
        existing.name = name
        existing.is_active = is_active
        existing.min_drop_percentage = min_drop_percentage
        existing.alert_on_out_of_stock = alert_on_out_of_stock
        existing.alert_on_back_in_stock = alert_on_back_in_stock
        # If new credentials provided, update them
        if credentials:
            existing.credentials = json.dumps(credentials)
        await db.commit()
        await db.refresh(existing)
        target = existing
    else:
        target = AlertConfig(
            channel=channel,
            name=name,
            is_active=is_active,
            min_drop_percentage=min_drop_percentage,
            alert_on_out_of_stock=alert_on_out_of_stock,
            alert_on_back_in_stock=alert_on_back_in_stock,
            credentials=json.dumps(credentials)
        )
        db.add(target)
        await db.commit()
        await db.refresh(target)

    return {"success": True, "id": target.id, "message": f"{channel.title()} configuration saved"}


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
    """Send a live test notification to verify channel credentials."""
    channel = payload.get("channel", "").lower()
    credentials = payload.get("credentials", {})

    if not channel:
        raise HTTPException(status_code=400, detail="Channel is required")

    success, message = await alert_service.test_channel(channel, credentials)
    return {"success": success, "message": message}


@router.get("/logs")
async def get_alert_logs(
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve audit history of triggered price drop and stock alerts."""
    stmt = select(AlertNotificationLog).order_by(desc(AlertNotificationLog.id)).limit(limit)
    res = await db.execute(stmt)
    logs = res.scalars().all()
    return logs
