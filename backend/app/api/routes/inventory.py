"""
API Routes for Competitor Stock Depletion & Inventory Forecasting.
Provides endpoints for recording stock observations, retrieving sales velocity,
predicting stockout dates, and surfacing merchant market opportunities.
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.services.inventory_depletion_service import inventory_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Competitor Inventory Depletion & Forecasting"])


class RecordStockRequest(BaseModel):
    stock_quantity: Optional[int] = Field(None, description="Current stock units available")
    in_stock: bool = Field(True, description="Whether product is in stock")
    recorded_at: Optional[datetime] = Field(None, description="Optional timestamp of observation")


@router.post("/products/{product_id}/stock")
async def record_stock_observation(
    product_id: int,
    payload: RecordStockRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Record a new inventory observation for a product.
    Automatically detects depletion or restock events and recalculates velocity and stockout dates.
    """
    try:
        result = await inventory_service.record_stock_observation(
            db=db,
            product_id=product_id,
            stock_quantity=payload.stock_quantity,
            in_stock=payload.in_stock,
            recorded_at=payload.recorded_at
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error recording stock for product {product_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/products/{product_id}/inventory-forecast")
async def get_inventory_forecast(
    product_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get sales velocity (units/day), estimated daily revenue, predicted stockout date,
    and opportunity verdict for a competitor product.
    """
    try:
        forecast = await inventory_service.get_forecast(db, product_id)
        if not forecast:
            raise HTTPException(status_code=404, detail="Product or forecast not found")
        return forecast
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching forecast for product {product_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/products/{product_id}/stock-history")
async def get_stock_history(
    product_id: int,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve chronological stock level observation logs with depletion/restock deltas.
    """
    try:
        return await inventory_service.get_stock_history(db, product_id, limit=limit)
    except Exception as e:
        logger.error(f"Error fetching stock history for product {product_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/inventory/opportunities")
async def get_stockout_opportunities(
    domain: Optional[str] = Query(None, description="Filter by competitor domain"),
    risk_level: Optional[str] = Query(None, description="Filter by risk level: high, medium, out_of_stock, all"),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve competitor products with imminent stockout risk across catalog.
    Enables merchants to identify displaced demand and optimize pricing or marketing campaigns.
    """
    try:
        return await inventory_service.get_stockout_opportunities(db, domain=domain, risk_level=risk_level)
    except Exception as e:
        logger.error(f"Error fetching stockout opportunities: {e}")
        raise HTTPException(status_code=500, detail=str(e))
