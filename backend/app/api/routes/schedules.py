"""
API endpoints for managing automated scheduled scraping jobs.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List
from urllib.parse import urlparse
from datetime import datetime, timezone
import logging

from app.models.database import get_db
from app.models.schedule import ScheduledJob
from app.schemas.schedule_schema import (
    ScheduleCreate, ScheduleUpdate, ScheduleResponse, ScheduleListResponse
)
from app.services.scheduler_service import calculate_next_run, scheduler_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/schedules", tags=["Schedules"])


@router.get("", response_model=ScheduleListResponse)
@router.get("/", response_model=ScheduleListResponse)
async def list_schedules(db: AsyncSession = Depends(get_db)):
    """List all scheduled recurring scraping jobs."""
    stmt = select(ScheduledJob).order_by(desc(ScheduledJob.created_at))
    result = await db.execute(stmt)
    schedules = result.scalars().all()
    return ScheduleListResponse(
        schedules=[ScheduleResponse.model_validate(s) for s in schedules],
        total=len(schedules)
    )


@router.post("", response_model=ScheduleResponse, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=ScheduleResponse, status_code=status.HTTP_201_CREATED)
async def create_schedule(
    payload: ScheduleCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new recurring scheduled scraper job.
    Calculates initial next_run_at timestamp based on the cron expression.
    """
    # 1. Validate cron expression
    now = datetime.now(timezone.utc)
    try:
        next_run = calculate_next_run(payload.cron_expression, now)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid cron expression '{payload.cron_expression}': {str(e)}"
        )

    # 2. Extract domain
    parsed = urlparse(payload.url)
    domain = parsed.netloc or "unknown"

    # 3. Create schedule record
    schedule = ScheduledJob(
        name=payload.name,
        description=payload.description,
        url=payload.url,
        domain=domain,
        cron_expression=payload.cron_expression,
        frequency_label=payload.frequency_label or "Custom Cron",
        is_active=True,
        config=payload.config or {},
        next_run_at=next_run,
        total_runs=0,
        failed_runs=0,
    )
    db.add(schedule)
    await db.commit()
    await db.refresh(schedule)

    logger.info(f"Created scheduled scraping job '{schedule.name}' (Next run: {next_run.isoformat()})")
    return ScheduleResponse.model_validate(schedule)


@router.get("/{schedule_id}", response_model=ScheduleResponse)
async def get_schedule(schedule_id: int, db: AsyncSession = Depends(get_db)):
    """Get a scheduled job by ID."""
    sched = await db.get(ScheduledJob, schedule_id)
    if not sched:
        raise HTTPException(status_code=404, detail="Scheduled job not found")
    return ScheduleResponse.model_validate(sched)


@router.put("/{schedule_id}", response_model=ScheduleResponse)
async def update_schedule(
    schedule_id: int,
    payload: ScheduleUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a scheduled job (active status, cron expression, URL, config)."""
    sched = await db.get(ScheduledJob, schedule_id)
    if not sched:
        raise HTTPException(status_code=404, detail="Scheduled job not found")

    update_data = payload.model_dump(exclude_unset=True)

    # If cron expression changed, recalculate next_run_at
    if "cron_expression" in update_data and update_data["cron_expression"]:
        try:
            now = datetime.now(timezone.utc)
            sched.next_run_at = calculate_next_run(update_data["cron_expression"], now)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid cron expression: {str(e)}"
            )

    # If URL changed, update domain
    if "url" in update_data and update_data["url"]:
        sched.domain = urlparse(update_data["url"]).netloc

    for field, value in update_data.items():
        setattr(sched, field, value)

    sched.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(sched)

    return ScheduleResponse.model_validate(sched)


@router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_schedule(schedule_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a scheduled job."""
    sched = await db.get(ScheduledJob, schedule_id)
    if not sched:
        raise HTTPException(status_code=404, detail="Scheduled job not found")

    await db.delete(sched)
    await db.commit()
    return None


@router.post("/{schedule_id}/run")
async def run_schedule_now(schedule_id: int, db: AsyncSession = Depends(get_db)):
    """Trigger an immediate run of a scheduled job."""
    sched = await db.get(ScheduledJob, schedule_id)
    if not sched:
        raise HTTPException(status_code=404, detail="Scheduled job not found")

    created_job_id = await scheduler_service.trigger_schedule(schedule_id)
    if not created_job_id:
        raise HTTPException(status_code=500, detail="Failed to trigger scraper job")

    return {
        "success": True,
        "message": f"Successfully triggered scrape job for schedule '{sched.name}'",
        "job_id": created_job_id,
        "schedule_id": schedule_id
    }
