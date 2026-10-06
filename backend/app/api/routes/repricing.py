"""
Repricing API Routes.
Provides endpoints for creating, editing, testing, and toggling automated repricing rules,
running manual repricing simulations, and inspecting repricing audit logs.
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.models.database import get_db
from app.models.repricing import RepricingRule, RepricingLog
from app.models.product import Product
from app.services.repricing_service import repricing_service

router = APIRouter(prefix="/repricing", tags=["Automated Repricing"])


@router.get("/rules")
async def get_repricing_rules(db: AsyncSession = Depends(get_db)):
    """Fetch all configured automated repricing rules."""
    query = select(RepricingRule).order_by(desc(RepricingRule.created_at))
    res = await db.execute(query)
    rules = res.scalars().all()
    return [
        {
            "id": r.id,
            "name": r.name,
            "is_active": r.is_active,
            "strategy": r.strategy,
            "adjustment_value": r.adjustment_value,
            "min_floor_price": float(r.min_floor_price) if r.min_floor_price else None,
            "max_ceiling_price": float(r.max_ceiling_price) if r.max_ceiling_price else None,
            "target_platform": r.target_platform,
            "target_domain": r.target_domain,
            "integration_config_id": r.integration_config_id,
            "webhook_url": r.webhook_url,
            "total_repriced": r.total_repriced,
            "last_triggered_at": r.last_triggered_at.isoformat() if r.last_triggered_at else None,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rules
    ]


@router.post("/rules")
async def create_repricing_rule(payload: Dict[str, Any], db: AsyncSession = Depends(get_db)):
    """Create a new automated repricing rule."""
    name = payload.get("name")
    if not name:
        raise HTTPException(status_code=400, detail="Rule name is required")

    rule = RepricingRule(
        name=name,
        strategy=payload.get("strategy", "beat_by_percentage"),
        adjustment_value=float(payload.get("adjustment_value", 2.0)),
        min_floor_price=payload.get("min_floor_price"),
        max_ceiling_price=payload.get("max_ceiling_price"),
        target_platform=payload.get("target_platform", "shopify"),
        target_domain=payload.get("target_domain"),
        integration_config_id=payload.get("integration_config_id"),
        webhook_url=payload.get("webhook_url"),
        webhook_secret=payload.get("webhook_secret"),
        is_active=payload.get("is_active", True),
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)

    return {
        "success": True,
        "message": f"Repricing rule '{rule.name}' created successfully",
        "rule_id": rule.id,
    }


@router.put("/rules/{rule_id}")
async def update_repricing_rule(rule_id: int, payload: Dict[str, Any], db: AsyncSession = Depends(get_db)):
    """Update an existing repricing rule."""
    rule = await db.get(RepricingRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    for field in [
        "name", "strategy", "adjustment_value", "min_floor_price", "max_ceiling_price",
        "target_platform", "target_domain", "integration_config_id", "webhook_url",
        "webhook_secret", "is_active"
    ]:
        if field in payload:
            setattr(rule, field, payload[field])

    await db.commit()
    return {"success": True, "message": f"Repricing rule {rule_id} updated"}


@router.delete("/rules/{rule_id}")
async def delete_repricing_rule(rule_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a repricing rule."""
    rule = await db.get(RepricingRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    await db.delete(rule)
    await db.commit()
    return {"success": True, "message": f"Rule {rule_id} deleted"}


@router.post("/simulate")
async def simulate_repricing(payload: Dict[str, Any]):
    """
    Simulate a repricing rule calculation without modifying any live stores.
    """
    competitor_price = payload.get("competitor_price")
    strategy = payload.get("strategy", "beat_by_percentage")
    adjustment_value = float(payload.get("adjustment_value", 2.0))
    floor_price = payload.get("min_floor_price")
    ceiling_price = payload.get("max_ceiling_price")

    if competitor_price is None:
        raise HTTPException(status_code=400, detail="competitor_price is required")

    new_price, guardrail_status = repricing_service.calculate_new_price(
        competitor_price=float(competitor_price),
        strategy=strategy,
        adjustment_value=adjustment_value,
        min_floor_price=float(floor_price) if floor_price else None,
        max_ceiling_price=float(ceiling_price) if ceiling_price else None,
    )

    diff = round(new_price - float(competitor_price), 2)
    diff_pct = round((diff / float(competitor_price)) * 100, 2) if float(competitor_price) > 0 else 0

    return {
        "competitor_price": float(competitor_price),
        "calculated_new_price": new_price,
        "difference": diff,
        "difference_percentage": diff_pct,
        "strategy": strategy,
        "adjustment_value": adjustment_value,
        "guardrail_status": guardrail_status,
        "summary": (
            f"Set price to ${new_price:.2f} ({diff_pct:+.1f}% vs competitor)"
            if guardrail_status == "applied" else
            f"Price bounded to ${new_price:.2f} by {guardrail_status}"
        )
    }


@router.get("/logs")
async def get_repricing_logs(
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """Fetch recent automated repricing execution audit logs."""
    query = select(RepricingLog).order_by(desc(RepricingLog.created_at)).limit(limit)
    res = await db.execute(query)
    logs = res.scalars().all()
    return [
        {
            "id": l.id,
            "rule_id": l.rule_id,
            "product_id": l.product_id,
            "product_name": l.product_name,
            "product_sku": l.product_sku,
            "competitor_domain": l.competitor_domain,
            "competitor_price": float(l.competitor_price) if l.competitor_price else None,
            "original_store_price": float(l.original_store_price) if l.original_store_price else None,
            "calculated_new_price": float(l.calculated_new_price) if l.calculated_new_price else None,
            "currency": l.currency,
            "target_platform": l.target_platform,
            "status": l.status,
            "reason": l.reason,
            "created_at": l.created_at.isoformat() if l.created_at else None,
        }
        for l in logs
    ]
