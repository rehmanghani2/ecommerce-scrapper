"""
Competitor Product Matching and Catalog Deduplication API Routes.
Provides endpoints for:
- Ad-hoc pairwise title/product comparison (with confidence and method breakdown)
- Automated batch clustering by scraping job or across full catalog
- Querying cross-store price clusters with savings and competitor spread analytics
- Disbanding/unclustering clusters
"""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.services.product_matching_service import product_matching_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/matching", tags=["Product Matching & Deduplication"])


class CompareRequest(BaseModel):
    product_a: Dict[str, Any] = Field(..., description="Product A data containing 'name', optional 'sku', 'brand'")
    product_b: Dict[str, Any] = Field(..., description="Product B data containing 'name', optional 'sku', 'brand'")
    threshold: Optional[float] = Field(0.75, ge=0.0, le=1.0, description="Similarity threshold for heuristic matching")
    use_ai: Optional[bool] = Field(True, description="Enable Gemini AI semantic fallback for borderline matches")
    api_key: Optional[str] = Field(None, description="Optional custom Gemini API key")


class ClusterJobRequest(BaseModel):
    threshold: Optional[float] = Field(0.75, ge=0.0, le=1.0, description="Similarity threshold")
    use_ai: Optional[bool] = Field(False, description="Enable Gemini AI fallback during batch clustering")
    api_key: Optional[str] = Field(None, description="Optional custom Gemini API key")


@router.post("/compare")
async def compare_products(payload: CompareRequest):
    """
    Perform a multi-tier similarity comparison between two products or titles.
    Evaluates SKU equivalence, heuristic token Jaccard & string similarity,
    and zero-shot Gemini semantic reasoning for ambiguous pairs.
    """
    try:
        result = await product_matching_service.evaluate_pair(
            p1=payload.product_a,
            p2=payload.product_b,
            threshold=payload.threshold or 0.75,
            allow_ai=payload.use_ai if payload.use_ai is not None else True,
            api_key=payload.api_key
        )
        return {"success": True, "result": result}
    except Exception as e:
        logger.error(f"Error in compare_products endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cluster-job/{job_id}")
async def cluster_job_products(
    job_id: int,
    payload: Optional[ClusterJobRequest] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Run deduplication clustering across products scraped in a specific scraping job.
    Groups identical items and assigns match_cluster_id.
    """
    threshold = payload.threshold if payload and payload.threshold is not None else 0.75
    use_ai = payload.use_ai if payload and payload.use_ai is not None else False
    api_key = payload.api_key if payload else None

    try:
        result = await product_matching_service.cluster_products_batch(
            db=db,
            job_id=job_id,
            threshold=threshold,
            use_ai=use_ai,
            api_key=api_key
        )
        return result
    except Exception as e:
        logger.error(f"Error clustering job products: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cluster-all")
async def cluster_all_products(
    payload: Optional[ClusterJobRequest] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Run deduplication clustering across ALL scraped products in the database.
    Identifies identical items across all competitor domains.
    """
    threshold = payload.threshold if payload and payload.threshold is not None else 0.75
    use_ai = payload.use_ai if payload and payload.use_ai is not None else False
    api_key = payload.api_key if payload else None

    try:
        result = await product_matching_service.cluster_products_batch(
            db=db,
            job_id=None,
            threshold=threshold,
            use_ai=use_ai,
            api_key=api_key
        )
        return result
    except Exception as e:
        logger.error(f"Error clustering all products: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/clusters")
async def list_clusters(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """
    List all matched product clusters with cross-store competitor pricing,
    savings percentage, and price spread statistics.
    """
    try:
        summary = await product_matching_service.get_clusters_summary(
            db=db,
            limit=limit,
            offset=offset,
            search=search
        )
        return summary
    except Exception as e:
        logger.error(f"Error listing clusters: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/clusters/{cluster_id}")
async def get_cluster(
    cluster_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed breakdown of a single cross-catalog product cluster,
    including sorted prices across competing stores.
    """
    try:
        cluster = await product_matching_service.get_cluster_details(db=db, cluster_id=cluster_id)
        if not cluster:
            raise HTTPException(status_code=404, detail="Cluster not found")
        return {"success": True, "cluster": cluster}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting cluster details: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/clusters/{cluster_id}")
async def uncluster_items(
    cluster_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Dissolve a cluster, unlinking all matched products.
    """
    try:
        unlinked = await product_matching_service.uncluster_products(db=db, cluster_id=cluster_id)
        return {
            "success": True,
            "message": f"Successfully unlinked {unlinked} products from cluster {cluster_id}",
            "unlinked_count": unlinked
        }
    except Exception as e:
        logger.error(f"Error unclustering items: {e}")
        raise HTTPException(status_code=500, detail=str(e))
