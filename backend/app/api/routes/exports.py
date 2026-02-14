"""
Export API routes for exporting scraped data.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from enum import Enum
import os

from app.models.database import get_db
from app.models.job import Job
from app.services.export_service import ExportService
from app.config import settings


router = APIRouter()


class ExportFormat(str, Enum):
    CSV = "csv"
    EXCEL = "excel"
    JSON = "json"


@router.post("/{job_id}")
async def create_export(
    job_id: str,
    format: ExportFormat = Query(ExportFormat.CSV),
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Create an export of scraped products for a job.
    """
    # Verify job exists
    query = select(Job).where(Job.job_id == job_id)
    result = await db.execute(query)
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Create export
    export_service = ExportService(db)
    
    try:
        file_path = await export_service.export_job_products(
            job_id=job.id,
            format=format.value
        )
        
        return {
            "success": True,
            "message": "Export created successfully",
            "file_path": file_path,
            "download_url": f"/api/v1/exports/download/{os.path.basename(file_path)}"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create export: {str(e)}"
        )


@router.get("/download/{filename}")
async def download_export(filename: str):
    """
    Download an exported file.
    """
    file_path = os.path.join(settings.EXPORT_PATH, filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Export file not found")
    
    # Determine media type
    if filename.endswith('.csv'):
        media_type = "text/csv"
    elif filename.endswith('.xlsx'):
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    elif filename.endswith('.json'):
        media_type = "application/json"
    else:
        media_type = "application/octet-stream"
    
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type=media_type
    )


@router.get("/list")
async def list_exports():
    """
    List all available export files.
    """
    exports = []
    
    if os.path.exists(settings.EXPORT_PATH):
        for filename in os.listdir(settings.EXPORT_PATH):
            file_path = os.path.join(settings.EXPORT_PATH, filename)
            if os.path.isfile(file_path):
                stat = os.stat(file_path)
                exports.append({
                    "filename": filename,
                    "size": stat.st_size,
                    "created_at": stat.st_ctime,
                    "download_url": f"/api/v1/exports/download/{filename}"
                })
    
    return {"exports": exports}


@router.delete("/{filename}")
async def delete_export(filename: str):
    """
    Delete an export file.
    """
    file_path = os.path.join(settings.EXPORT_PATH, filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Export file not found")
    
    os.remove(file_path)
    
    return {"success": True, "message": "Export deleted"}