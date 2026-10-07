"""
API routes for Competitor Search Ranking & SERP Visibility Tracking.
"""
import logging
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.services.serp_service import serp_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/serp", tags=["serp"])


class SerpKeywordCreateRequest(BaseModel):
    keyword: str = Field(..., description="Target search query (e.g. 'wireless headphones')")
    domain: Optional[str] = Field("amazon.com", description="Competitor marketplace domain")
    marketplace: Optional[str] = Field("amazon", description="amazon, ebay, walmart, google_shopping, general")
    check_frequency: Optional[str] = Field("daily", description="hourly, daily, weekly, manual")


class SerpSnapshotItemInput(BaseModel):
    title: str = Field(..., description="Product title on search result page")
    url: Optional[str] = Field(None, description="Listing URL")
    brand: Optional[str] = Field(None, description="Brand name if detected")
    price: Optional[float] = Field(None, description="Listing price")
    currency: Optional[str] = Field("USD", description="Currency symbol/code")
    image_url: Optional[str] = Field(None, description="Image thumbnail")
    rank_position: Optional[int] = Field(None, description="Position index (1, 2, 3...)")
    page_number: Optional[int] = Field(1, description="Page number")
    ranking_type: Optional[str] = Field("organic", description="organic, sponsored, best_seller, amazon_choice")
    is_sponsored: Optional[bool] = Field(False, description="Is this a paid / sponsored placement")
    badge: Optional[str] = Field(None, description="e.g. 'Best Seller', 'Amazon Choice'")
    rating: Optional[float] = Field(None, description="Star rating")
    review_count: Optional[int] = Field(None, description="Review count")
    product_id: Optional[int] = Field(None, description="Linked catalog product ID if known")


class SerpSnapshotRequest(BaseModel):
    items: List[SerpSnapshotItemInput] = Field(..., description="Ordered ranking items on the search results page")


@router.get("/keywords", response_model=List[Dict[str, Any]])
async def list_serp_keywords(
    active_only: bool = Query(False, description="Only active keywords"),
    domain: Optional[str] = Query(None, description="Filter by marketplace domain"),
    db: AsyncSession = Depends(get_db)
):
    """
    List monitored search keywords with latest ranking summaries and Share of Voice leaders.
    """
    try:
        return await serp_service.get_keywords(db=db, active_only=active_only, domain=domain)
    except Exception as e:
        logger.error(f"Error fetching SERP keywords: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/keywords", status_code=status.HTTP_201_CREATED)
async def create_serp_keyword(
    payload: SerpKeywordCreateRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new keyword to track search engine result page (SERP) positions.
    """
    try:
        kw = await serp_service.create_keyword(
            db=db,
            keyword=payload.keyword,
            domain=payload.domain or "amazon.com",
            marketplace=payload.marketplace or "amazon",
            check_frequency=payload.check_frequency or "daily",
        )
        return kw.to_dict()
    except Exception as e:
        logger.error(f"Error registering SERP keyword: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/keywords/{keyword_id}", response_model=Dict[str, Any])
async def get_keyword_detail(
    keyword_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve full SERP ranking positions, rank changes, and brand Share of Voice for a keyword.
    """
    try:
        data = await serp_service.get_keyword_detail(db=db, keyword_id=keyword_id)
        if not data:
            raise HTTPException(status_code=404, detail=f"Keyword {keyword_id} not found.")
        return data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting keyword {keyword_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/keywords/{keyword_id}/snapshot", status_code=status.HTTP_200_OK)
async def record_keyword_snapshot(
    keyword_id: int,
    payload: SerpSnapshotRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Record or ingest a newly crawled SERP snapshot and compute position deltas.
    """
    try:
        raw_items = [i.model_dump() for i in payload.items]
        return await serp_service.record_serp_snapshot(db=db, keyword_id=keyword_id, items=raw_items)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        logger.error(f"Error recording SERP snapshot for keyword {keyword_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/keywords/{keyword_id}", status_code=status.HTTP_200_OK)
async def delete_keyword(
    keyword_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a tracked keyword and its SERP historical ranking items.
    """
    try:
        success = await serp_service.delete_keyword(db=db, keyword_id=keyword_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Keyword {keyword_id} not found.")
        return {"success": True, "message": f"Keyword {keyword_id} deleted."}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting keyword {keyword_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/product/{product_id}", response_model=List[Dict[str, Any]])
async def get_product_serp_rankings(
    product_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all search query positions where a specific product appears in competitor search results.
    """
    try:
        return await serp_service.get_product_rankings(db=db, product_id=product_id)
    except Exception as e:
        logger.error(f"Error fetching product SERP rankings for {product_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/insights", response_model=Dict[str, Any])
async def get_serp_insights(
    db: AsyncSession = Depends(get_db)
):
    """
    Get catalog-wide search visibility metrics across all monitored keywords.
    """
    try:
        return await serp_service.get_serp_insights(db=db)
    except Exception as e:
        logger.error(f"Error calculating SERP insights: {e}")
        raise HTTPException(status_code=500, detail=str(e))
