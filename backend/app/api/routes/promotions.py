"""
API endpoints for competitor promotions, coupon codes, and bundle tracking.
"""
import logging
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.services.promotion_service import promotion_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/promotions", tags=["promotions"])


class PromotionCreateRequest(BaseModel):
    promo_type: str = Field(default="coupon_code", description="Type of promo: coupon_code, percentage_discount, fixed_amount_discount, bogo, volume_tier, flash_sale")
    title: str = Field(..., description="Short promotion title")
    coupon_code: Optional[str] = Field(None, description="Alphanumeric coupon code if available")
    discount_type: str = Field(default="percentage", description="percentage, fixed_amount, bogo, volume_tier")
    discount_value: Optional[float] = Field(None, description="Discount magnitude (e.g. 20 for 20% or 10 for $10)")
    bogo_buy_qty: Optional[int] = Field(None, description="Buy quantity for BOGO")
    bogo_get_qty: Optional[int] = Field(None, description="Get quantity for BOGO")
    bogo_discount_pct: Optional[float] = Field(None, description="Discount on BOGO get items (e.g. 100 for free)")
    volume_min_qty: Optional[int] = Field(None, description="Minimum units to unlock volume tier")
    minimum_spend: Optional[float] = Field(None, description="Minimum order spend threshold")
    banner_text: Optional[str] = Field(None, description="Promotional banner quote")
    description: Optional[str] = Field(None, description="Detailed description")
    terms: Optional[str] = Field(None, description="Terms and conditions")
    is_active: bool = Field(default=True, description="Active status")


class PromotionDetectRequest(BaseModel):
    text: str = Field(..., description="Raw text, title, or HTML snippet containing potential promotions")
    product_title: Optional[str] = Field(default="", description="Product title for context")
    original_price: Optional[float] = Field(default=0.0, description="Product base price for effective price calculations")
    use_ai: Optional[bool] = Field(default=False, description="Use Gemini 2.5 Flash for deep extraction")


@router.get("/active", response_model=Dict[str, Any])
async def get_active_promotions(
    domain: Optional[str] = Query(None, description="Filter by competitor domain"),
    promo_type: Optional[str] = Query(None, description="Filter by promo type"),
    min_discount_pct: Optional[float] = Query(None, description="Filter by minimum discount %"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve active competitor promotions across the entire catalog with product context.
    """
    try:
        return await promotion_service.get_active_promotions_catalog(
            db=db,
            domain=domain,
            promo_type=promo_type,
            min_discount_pct=min_discount_pct,
            limit=limit,
            offset=offset,
        )
    except Exception as e:
        logger.error(f"Error fetching active promotions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/insights", response_model=Dict[str, Any])
async def get_promotion_insights(
    domain: Optional[str] = Query(None, description="Filter insights by competitor domain"),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve competitor promotion analytics (type breakdown, average discount depth, top deals).
    """
    try:
        return await promotion_service.get_promotional_insights(db=db, domain=domain)
    except Exception as e:
        logger.error(f"Error calculating promotion insights: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/product/{product_id}", response_model=List[Dict[str, Any]])
async def get_product_promotions(
    product_id: int,
    active_only: bool = Query(False, description="Only return active promotions"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all promotions, coupon codes, and bundle offers for a specific product.
    """
    try:
        return await promotion_service.get_promotions_for_product(
            db=db, product_id=product_id, active_only=active_only
        )
    except Exception as e:
        logger.error(f"Error fetching promotions for product {product_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/product/{product_id}", status_code=status.HTTP_201_CREATED)
async def create_product_promotion(
    product_id: int,
    payload: PromotionCreateRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Manually attach or record a promotion / coupon for a product.
    """
    try:
        promo = await promotion_service.add_or_update_promotion(
            db=db, product_id=product_id, promo_data=payload.model_dump()
        )
        return promo.to_dict()
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        logger.error(f"Error creating promotion for product {product_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/detect", response_model=List[Dict[str, Any]])
async def detect_promotions(
    payload: PromotionDetectRequest
):
    """
    Extract promotions, coupon codes, and volume deals from raw text or HTML snippets.
    """
    try:
        if payload.use_ai:
            return await promotion_service.detect_with_gemini(
                text_or_html=payload.text,
                product_title=payload.product_title or "",
                original_price=payload.original_price or 0.0,
            )
        return promotion_service.detect_promotions_from_text(
            text=payload.text,
            original_price=payload.original_price or 0.0,
        )
    except Exception as e:
        logger.error(f"Error detecting promotions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{promotion_id}/toggle", response_model=Dict[str, Any])
async def toggle_promotion(
    promotion_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Toggle active/inactive status of a promotion.
    """
    try:
        return await promotion_service.toggle_promotion(db=db, promo_id=promotion_id)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        logger.error(f"Error toggling promotion {promotion_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{promotion_id}", status_code=status.HTTP_200_OK)
async def delete_promotion(
    promotion_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a promotion from the database.
    """
    try:
        success = await promotion_service.delete_promotion(db=db, promo_id=promotion_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Promotion {promotion_id} not found.")
        return {"success": True, "message": f"Promotion {promotion_id} deleted."}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting promotion {promotion_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
