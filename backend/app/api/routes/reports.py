"""
API Routes for Scheduled Competitor Intelligence Reports via Email and PDF.
Provides endpoints for scheduling reports, generating PDF downloads, previewing HTML digests,
and executing manual report dispatches.
"""

import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.services.report_service import report_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reports", tags=["Competitor Intelligence Reports"])


class CreateScheduleRequest(BaseModel):
    name: str = Field(..., description="Schedule title, e.g. 'Weekly Executive Market Digest'")
    recipient_emails: List[str] = Field(..., description="Recipient email addresses")
    frequency: str = Field("weekly", description="daily, weekly, monthly, custom")
    cron_expression: str = Field("0 9 * * 1", description="Cron schedule expression")
    frequency_label: Optional[str] = Field("Every Monday at 09:00 AM", description="Friendly frequency label")
    format: str = Field("both", description="both, pdf, email_html")
    domain_filter: Optional[str] = Field(None, description="Optional domain filter")
    include_price_drops: bool = True
    include_catalog_diffs: bool = True
    include_stockouts: bool = True
    include_sentiment: bool = True


class SendTestReportRequest(BaseModel):
    recipient_email: str = Field(..., description="Email address to receive test digest")
    domain_filter: Optional[str] = Field(None, description="Optional domain filter")
    format: str = Field("both", description="both, pdf, email_html")


@router.get("/schedules")
async def get_schedules(db: AsyncSession = Depends(get_db)):
    """List all scheduled competitor intelligence reports."""
    try:
        return await report_service.get_all_schedules(db)
    except Exception as e:
        logger.error(f"Error fetching report schedules: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/schedules")
async def create_schedule(
    payload: CreateScheduleRequest,
    db: AsyncSession = Depends(get_db)
):
    """Create a new recurring competitor intelligence report schedule."""
    try:
        data = payload.model_dump() if hasattr(payload, 'model_dump') else payload.dict()
        return await report_service.create_schedule(db=db, **data)
    except Exception as e:
        logger.error(f"Error creating report schedule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/schedules/{schedule_id}")
async def delete_schedule(
    schedule_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete a report schedule."""
    try:
        deleted = await report_service.delete_schedule(db, schedule_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Schedule not found")
        return {"success": True, "message": f"Schedule {schedule_id} deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting schedule {schedule_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/schedules/{schedule_id}/trigger")
async def trigger_schedule(
    schedule_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Manually generate and dispatch a scheduled report immediately."""
    try:
        return await report_service.trigger_schedule_report(db, schedule_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error triggering report {schedule_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/preview")
async def preview_html_report(
    domain: Optional[str] = Query(None, description="Optional domain filter"),
    days: int = Query(7, ge=1, le=90),
    db: AsyncSession = Depends(get_db)
):
    """Preview the responsive executive HTML report directly in browser."""
    try:
        data = await report_service.compile_intelligence_data(db, domain=domain, days=days)
        html = report_service.generate_html_report(data)
        return Response(content=html, media_type="text/html")
    except Exception as e:
        logger.error(f"Error previewing report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/download-pdf")
async def download_pdf_report(
    domain: Optional[str] = Query(None, description="Optional domain filter"),
    days: int = Query(7, ge=1, le=90),
    db: AsyncSession = Depends(get_db)
):
    """Generate and download a high-fidelity PDF report."""
    try:
        data = await report_service.compile_intelligence_data(db, domain=domain, days=days)
        pdf_bytes = report_service.generate_pdf_report(data)
        filename = f"competitor_intelligence_{domain or 'catalog'}_{days}d.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        logger.error(f"Error generating PDF report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/send-test")
async def send_test_report(
    payload: SendTestReportRequest,
    db: AsyncSession = Depends(get_db)
):
    """Generate and dispatch an instant test report to a designated email."""
    try:
        data = await report_service.compile_intelligence_data(db, domain=payload.domain_filter)
        html = report_service.generate_html_report(data)
        pdf_bytes = report_service.generate_pdf_report(data) if payload.format in ("both", "pdf") else None

        subject = f"📊 Test Competitor Intelligence Digest ({data['domain_scope']})"
        success, msg = await report_service.send_email_report(
            to_emails=[payload.recipient_email],
            subject=subject,
            html_content=html,
            pdf_bytes=pdf_bytes,
            pdf_filename="test_competitor_report.pdf"
        )
        return {"success": success, "message": msg}
    except Exception as e:
        logger.error(f"Error sending test report: {e}")
        raise HTTPException(status_code=500, detail=str(e))
