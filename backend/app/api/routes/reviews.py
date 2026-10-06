"""
Product Reviews & Competitor Sentiment Mining API Routes.
Provides endpoints for:
- Listing and filtering product customer reviews
- Ingesting scraped customer reviews
- Running AI sentiment mining and competitor product weakness analysis
- Querying store-wide competitor flaws and buyer pain point intelligence
"""

import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.models.database import get_db
from app.models.product import Product, ProductReview, ProductSentimentSummary
from app.services.review_sentiment_service import review_sentiment_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Reviews & Sentiment Mining"])


class ReviewItem(BaseModel):
    author: Optional[str] = Field("Anonymous", description="Reviewer name")
    rating: Optional[float] = Field(None, ge=1.0, le=5.0, description="Star rating 1.0-5.0")
    title: Optional[str] = Field(None, description="Review title/headline")
    content: str = Field(..., description="Review body text")
    verified_purchase: Optional[bool] = Field(False, description="Verified buyer status")
    helpful_votes: Optional[int] = Field(0, description="Helpful upvotes count")


class IngestReviewsRequest(BaseModel):
    reviews: List[ReviewItem] = Field(..., description="List of review records")
    run_ai_analysis: Optional[bool] = Field(False, description="Trigger deep Gemini sentiment mining")
    api_key: Optional[str] = Field(None, description="Optional custom Gemini API key")


class AnalyzeSentimentRequest(BaseModel):
    use_ai: Optional[bool] = Field(True, description="Enable Gemini AI deep weakness mining")
    api_key: Optional[str] = Field(None, description="Optional custom Gemini API key")


@router.get("/products/{product_id}/reviews")
async def list_product_reviews(
    product_id: int,
    sentiment: Optional[str] = Query(None, description="Filter by sentiment: positive, neutral, negative"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """
    List extracted customer reviews for a product with optional sentiment filtering.
    """
    query = select(ProductReview).where(ProductReview.product_id == product_id)
    if sentiment:
        query = query.where(ProductReview.sentiment == sentiment.lower())

    query = query.order_by(desc(ProductReview.created_at)).limit(limit).offset(offset)
    res = await db.execute(query)
    reviews = res.scalars().all()

    return {
        "product_id": product_id,
        "total": len(reviews),
        "reviews": [r.to_dict() for r in reviews],
    }


@router.post("/products/{product_id}/reviews")
async def ingest_reviews(
    product_id: int,
    payload: IngestReviewsRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Ingest a batch of scraped reviews for a product.
    Automatically computes heuristic sentiment scores and updates the summary.
    """
    try:
        raw_list = [r.model_dump() if hasattr(r, 'model_dump') else r.dict() for r in payload.reviews]
        result = await review_sentiment_service.ingest_reviews(
            db=db,
            product_id=product_id,
            reviews_data=raw_list,
            run_ai=payload.run_ai_analysis or False,
            api_key=payload.api_key
        )
        return result
    except Exception as e:
        logger.error(f"Error ingesting reviews: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/products/{product_id}/sentiment/analyze")
async def analyze_product_sentiment(
    product_id: int,
    payload: Optional[AnalyzeSentimentRequest] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Trigger deep AI review sentiment analysis and competitor weakness mining.
    Extracts recurring buyer flaws, competitor vulnerabilities, and executive summary verdict.
    """
    try:
        use_ai = payload.use_ai if payload and payload.use_ai is not None else True
        api_key = payload.api_key if payload else None

        summary = await review_sentiment_service.recalculate_sentiment_summary(
            db=db,
            product_id=product_id,
            run_ai=use_ai,
            api_key=api_key
        )
        if not summary:
            raise HTTPException(
                status_code=404,
                detail="No reviews found for this product to analyze. Add reviews first."
            )

        await db.commit()
        return {"success": True, "sentiment_summary": summary.to_dict()}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing sentiment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/products/{product_id}/sentiment")
async def get_product_sentiment(
    product_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Fetch existing sentiment summary, key strengths, competitor weaknesses, and pain points for a product.
    """
    stmt = select(ProductSentimentSummary).where(ProductSentimentSummary.product_id == product_id)
    res = await db.execute(stmt)
    summary = res.scalar_one_or_none()

    if not summary:
        raise HTTPException(
            status_code=404,
            detail="Sentiment analysis has not been run for this product yet."
        )

    return {"success": True, "sentiment_summary": summary.to_dict()}


@router.get("/reviews/domain/{domain}/weaknesses")
async def get_domain_weakness_intelligence(
    domain: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Aggregate top recurring product weaknesses and buyer pain points across an entire competitor store domain.
    """
    try:
        result = await review_sentiment_service.get_domain_weakness_intelligence(db=db, domain=domain)
        return {"success": True, "intelligence": result}
    except Exception as e:
        logger.error(f"Error fetching domain weaknesses: {e}")
        raise HTTPException(status_code=500, detail=str(e))
