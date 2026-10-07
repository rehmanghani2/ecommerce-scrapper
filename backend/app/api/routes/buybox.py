"""
API routes for Marketplace Buy Box Win/Loss Tracking & Predictive Pricing.
"""
import logging
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.services.buybox_service import buybox_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/buybox", tags=["buybox"])


class BuyBoxEvaluateRequest(BaseModel):
    winner_price: float = Field(..., description="Current Buy Box winning price")
    winner_fulfillment: Optional[str] = Field("fba", description="fba, fbm, retail")
    seller_price: Optional[float] = Field(None, description="Your offer price")
    seller_fulfillment: Optional[str] = Field("fba", description="Your fulfillment type: fba, fbm")
    seller_rating_pct: Optional[float] = Field(98.0, description="Your merchant feedback score percentage")
    is_suppressed: Optional[bool] = Field(False, description="Is Buy Box currently suppressed")
    is_amazon_sold: Optional[bool] = Field(False, description="Is current winner Amazon Direct")


class BuyBoxObservationRequest(BaseModel):
    current_winner: str = Field(..., description="Name of the seller currently owning the Buy Box")
    winner_price: float = Field(..., description="Listing price of the winning offer")
    winner_shipping_price: Optional[float] = Field(0.0, description="Shipping price")
    fulfillment_type: Optional[str] = Field("fba", description="fba, fbm, wfs, retail")
    is_suppressed: Optional[bool] = Field(False, description="Is the Buy Box suppressed")
    competing_sellers_count: Optional[int] = Field(1, description="Total count of competing sellers on the listing")
    lowest_competing_price: Optional[float] = Field(None, description="Lowest price among all offers")
    tracked_seller_name: Optional[str] = Field(None, description="Your merchant store name")
    tracked_seller_price: Optional[float] = Field(None, description="Your merchant offer price")
    tracked_seller_fulfillment: Optional[str] = Field("fba", description="Your fulfillment method: fba, fbm")


@router.get("/product/{product_id}", response_model=Dict[str, Any])
async def get_product_buybox_state(
    product_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get current Buy Box state, rotation statistics, and recent transition history for a product.
    """
    try:
        return await buybox_service.get_buybox_detail(db=db, product_id=product_id)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        logger.error(f"Error fetching Buy Box state for product {product_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/product/{product_id}/evaluate", response_model=Dict[str, Any])
async def evaluate_buybox_prediction(
    product_id: int,
    payload: BuyBoxEvaluateRequest
):
    """
    Simulate Buy Box win probability and compute optimal target winning price.
    """
    try:
        return buybox_service.calculate_win_probability(
            winner_price=payload.winner_price,
            winner_fulfillment=payload.winner_fulfillment or "fba",
            seller_price=payload.seller_price,
            seller_fulfillment=payload.seller_fulfillment or "fba",
            seller_rating_pct=payload.seller_rating_pct or 98.0,
            is_suppressed=payload.is_suppressed or False,
            is_amazon_sold=payload.is_amazon_sold or False,
        )
    except Exception as e:
        logger.error(f"Error evaluating Buy Box simulation for product {product_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/product/{product_id}/observation", response_model=Dict[str, Any])
async def record_buybox_observation(
    product_id: int,
    payload: BuyBoxObservationRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Record a new Buy Box crawl snapshot, detect transition handoffs, and update predictions.
    """
    try:
        return await buybox_service.record_buybox_observation(
            db=db, product_id=product_id, obs=payload.model_dump()
        )
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        logger.error(f"Error recording Buy Box observation for product {product_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts", response_model=Dict[str, Any])
async def get_buybox_catalog_alerts(
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve catalog-wide Buy Box losses, suppressions, and priority recapture targets.
    """
    try:
        return await buybox_service.get_catalog_buybox_alerts(db=db)
    except Exception as e:
        logger.error(f"Error fetching catalog Buy Box alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))
