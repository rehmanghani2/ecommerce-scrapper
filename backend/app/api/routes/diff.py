"""
Catalog Change Detection and Differential Intelligence API Routes.
Provides endpoints for:
- Comparing any two jobs by ID
- Comparing a job with its immediately preceding crawl of the same domain
- Comparing the latest two crawls of a domain
- Exporting catalog difference reports to CSV
"""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.services.catalog_diff_service import catalog_diff_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/diff", tags=["Catalog Diff & Change Intelligence"])


class CompareJobsRequest(BaseModel):
    job_id_1: int = Field(..., description="First job database ID")
    job_id_2: int = Field(..., description="Second job database ID")


@router.post("/compare")
async def compare_two_jobs(
    payload: CompareJobsRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Compare any two scraping jobs to detect newly added items, delisted products,
    price increases/drops, and inventory stock changes.
    """
    try:
        diff = await catalog_diff_service.compare_two_jobs(
            db=db,
            job_id_1=payload.job_id_1,
            job_id_2=payload.job_id_2
        )
        if not diff:
            raise HTTPException(status_code=404, detail="One or both jobs not found")
        return {"success": True, "diff": diff}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in compare_two_jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/job/{job_id}/previous")
async def compare_job_with_previous(
    job_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Compare a specific job with the immediately prior crawl of the same domain.
    """
    try:
        diff = await catalog_diff_service.compare_job_with_previous(db=db, job_id=job_id)
        if not diff:
            raise HTTPException(
                status_code=404,
                detail="No previous crawl found for this domain to compare against."
            )
        return {"success": True, "diff": diff}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error comparing job with previous: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/domain/{domain}")
async def compare_domain_latest(
    domain: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Compare the two latest crawls of a target competitor domain.
    """
    try:
        diff = await catalog_diff_service.compare_domain_latest(db=db, domain=domain)
        if not diff:
            raise HTTPException(
                status_code=404,
                detail=f"Need at least 2 scraping jobs for '{domain}' to compute catalog diff."
            )
        return {"success": True, "diff": diff}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error comparing domain latest: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export/{job_id_1}/{job_id_2}")
async def export_diff_csv(
    job_id_1: int,
    job_id_2: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Export catalog differential intelligence between two jobs as a downloadable CSV.
    """
    try:
        diff = await catalog_diff_service.compare_two_jobs(
            db=db,
            job_id_1=job_id_1,
            job_id_2=job_id_2
        )
        if not diff:
            raise HTTPException(status_code=404, detail="Jobs not found")

        csv_content = catalog_diff_service.export_diff_to_csv(diff)
        filename = f"catalog_diff_job_{job_id_1}_vs_{job_id_2}.csv"

        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting diff CSV: {e}")
        raise HTTPException(status_code=500, detail=str(e))
