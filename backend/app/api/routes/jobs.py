"""
Jobs API routes for managing scraping jobs.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from typing import Optional
from datetime import datetime

from app.models.database import get_db
from app.models.job import Job, JobStatus
from app.schemas.job_schema import (
    JobResponse, JobListResponse, JobStatistics
)


router = APIRouter()


@router.get("/", response_model=JobListResponse)
async def list_jobs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    domain: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """
    List all scraping jobs with pagination and filtering.
    """
    # Build query
    query = select(Job).order_by(desc(Job.created_at))
    count_query = select(func.count(Job.id))
    
    if status == "":
        status = None
    
    if status:
        query = query.where(Job.status == status)
        count_query = count_query.where(Job.status == status)
    
    if domain:
        query = query.where(Job.domain.ilike(f"%{domain}%"))
        count_query = count_query.where(Job.domain.ilike(f"%{domain}%"))
    
    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    
    # Execute query
    result = await db.execute(query)
    jobs = result.scalars().all()

    # Sync total_products from products table for consistency
    from app.models.product import Product
    job_responses = []
    need_commit = False
    for job in jobs:
        count_q = select(func.count(Product.id)).where(Product.job_id == job.id)
        count_res = await db.execute(count_q)
        real_total = count_res.scalar() or 0
        if job.total_products != real_total:
            job.total_products = real_total
            need_commit = True
        job_responses.append(JobResponse(**job.to_dict()))
    
    if need_commit:
        await db.commit()

    pages = (total + page_size - 1) // page_size if page_size > 0 else 1

    return JobListResponse(
        jobs=job_responses,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages
    )


@router.get("/statistics", response_model=JobStatistics)
async def get_job_statistics(db: AsyncSession = Depends(get_db)):
    """
    Get overall job statistics.
    """
    # Get counts by status
    status_query = select(
        Job.status,
        func.count(Job.id).label('count')
    ).group_by(Job.status)
    
    result = await db.execute(status_query)
    status_counts = {row.status: row.count for row in result}
    
    # Get totals
    totals_query = select(
        func.count(Job.id).label('total'),
        func.sum(Job.total_products).label('products'),
        func.sum(Job.scraped_pages).label('pages'),
        func.avg(
            func.extract('epoch', Job.completed_at) - 
            func.extract('epoch', Job.started_at)
        ).label('avg_duration')
    ).where(Job.completed_at.isnot(None))
    
    totals_result = await db.execute(totals_query)
    totals = totals_result.first()
    
    total_jobs = sum(status_counts.values())
    completed = status_counts.get(JobStatus.COMPLETED, 0)
    
    return JobStatistics(
        total_jobs=total_jobs,
        completed_jobs=completed,
        failed_jobs=status_counts.get(JobStatus.FAILED, 0),
        running_jobs=status_counts.get(JobStatus.RUNNING, 0),
        total_products=int(totals.products or 0),
        total_pages=int(totals.pages or 0),
        average_duration=float(totals.avg_duration) if totals.avg_duration else None,
        success_rate=completed / total_jobs * 100 if total_jobs > 0 else 0
    )


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: str, db: AsyncSession = Depends(get_db)):
    """
    Get details of a specific job.
    """
    query = select(Job).where(Job.job_id == job_id)
    result = await db.execute(query)
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    # Dynamically update total_products from the products table to ensure consistency
    from app.models.product import Product
    from sqlalchemy import func
    count_query = select(func.count(Product.id)).where(Product.job_id == job.id)
    count_result = await db.execute(count_query)
    real_total = count_result.scalar() or 0
    
    if job.total_products != real_total:
        job.total_products = real_total
        await db.commit()
    
    return JobResponse(**job.to_dict())


@router.get("/{job_id}/logs")
async def get_job_logs(
    job_id: str,
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db)
):
    """
    Get logs for a specific job.
    """
    query = select(Job).where(Job.job_id == job_id)
    result = await db.execute(query)
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    logs = job.logs or []
    return {
        "job_id": job_id,
        "logs": logs[-limit:],
        "total": len(logs)
    }


@router.post("/{job_id}/pause")
async def pause_job(job_id: str, db: AsyncSession = Depends(get_db)):
    """
    Pause a running job.
    """
    query = select(Job).where(Job.job_id == job_id)
    result = await db.execute(query)
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status != JobStatus.RUNNING:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot pause job with status: {job.status}"
        )
    
    job.status = JobStatus.PAUSED
    await db.commit()
    
    return {"success": True, "message": "Job paused", "status": "paused"}


@router.post("/{job_id}/resume")
async def resume_job(job_id: str, db: AsyncSession = Depends(get_db)):
    """
    Resume a paused job.
    """
    query = select(Job).where(Job.job_id == job_id)
    result = await db.execute(query)
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status != JobStatus.PAUSED:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot resume job with status: {job.status}"
        )
    
    job.status = JobStatus.RUNNING
    await db.commit()
    
    # TODO: Trigger job resumption in Celery
    
    return {"success": True, "message": "Job resumed", "status": "running"}


@router.post("/{job_id}/cancel")
async def cancel_job(job_id: str, db: AsyncSession = Depends(get_db)):
    """
    Cancel a running or paused job.
    """
    query = select(Job).where(Job.job_id == job_id)
    result = await db.execute(query)
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status not in [JobStatus.RUNNING, JobStatus.PAUSED, JobStatus.PENDING]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel job with status: {job.status}"
        )
    
    job.status = JobStatus.CANCELLED
    job.completed_at = datetime.utcnow()
    await db.commit()
    
    # TODO: Cancel Celery task if running
    
    return {"success": True, "message": "Job cancelled", "status": "cancelled"}


@router.delete("/{job_id}")
async def delete_job(job_id: str, db: AsyncSession = Depends(get_db)):
    """
    Delete a job and all its associated data.
    """
    query = select(Job).where(Job.job_id == job_id)
    result = await db.execute(query)
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status == JobStatus.RUNNING:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete a running job. Cancel it first."
        )
    
    await db.delete(job)
    await db.commit()
    
    return {"success": True, "message": "Job deleted"}

from fastapi import BackgroundTasks
@router.post("/{job_id}/retry")
async def retry_job(
    job_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Retry a failed job.
    """
    from fastapi import BackgroundTasks
    
    query = select(Job).where(Job.job_id == job_id)
    result = await db.execute(query)
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status != JobStatus.FAILED:
        raise HTTPException(
            status_code=400,
            detail="Only failed jobs can be retried"
        )
    
    # Reset job state
    job.status = JobStatus.PENDING
    job.error_message = None
    job.error_trace = None
    job.progress = 0
    job.started_at = None
    job.completed_at = None
    await db.commit()
    
    # TODO: Queue job for retry
    
    return {"success": True, "message": "Job queued for retry", "status": "pending"}


@router.get("/{job_id}/logs")
async def get_job_logs(
    job_id: str,
    limit: int = Query(500, ge=1, le=2000),
    db: AsyncSession = Depends(get_db)
):
    """
    Get scraping logs for a job.
    Returns timestamped log entries written during the crawl.
    """
    query = select(Job).where(Job.job_id == job_id)
    result = await db.execute(query)
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    logs = list(job.logs or [])

    # Apply limit (most recent first if over limit)
    if len(logs) > limit:
        logs = logs[-limit:]

    return {
        "job_id": job_id,
        "total": len(logs),
        "logs": logs,
    }


@router.get("/{job_id}/products")
async def get_job_products(
    job_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all products scraped by a specific job.
    """
    from sqlalchemy import select, func
    from app.models.product import Product

    # Find the job record first
    job_query = select(Job).where(Job.job_id == job_id)
    job_result = await db.execute(job_query)
    job = job_result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Count products
    count_query = select(func.count(Product.id)).where(Product.job_id == job.id)
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    # Paginate
    from sqlalchemy.orm import selectinload
    offset = (page - 1) * page_size
    products_query = (
        select(Product)
        .options(selectinload(Product.images), selectinload(Product.variants))
        .where(Product.job_id == job.id)
        .offset(offset)
        .limit(page_size)
    )
    products_result = await db.execute(products_query)
    products = products_result.scalars().all()

    return {
        "job_id": job_id,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size,
        "products": [p.to_dict() for p in products],
    }