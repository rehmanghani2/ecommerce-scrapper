"""
Supabase Storage API Routes.
Enables testing Supabase credentials/bucket, uploading single images to Supabase Storage,
and triggering background image archiving from scrapers to free Supabase Storage buckets.
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.database import get_db, get_db_context
from app.models.product import Product
from app.services.supabase_storage_service import supabase_storage_service
from app.config import settings

router = APIRouter(prefix="/supabase", tags=["Supabase Cloud Storage"])


@router.get("/status")
async def get_supabase_status():
    """Check Supabase Storage configuration status."""
    is_cfg = supabase_storage_service.is_configured()
    url = getattr(settings, "SUPABASE_URL", None)
    bucket = getattr(settings, "SUPABASE_STORAGE_BUCKET", "product-images")
    folder = getattr(settings, "SUPABASE_STORAGE_FOLDER", "products")
    auto_upload = getattr(settings, "SUPABASE_AUTO_UPLOAD", False)

    return {
        "configured": is_cfg,
        "supabase_url": url or "Not Configured",
        "bucket": bucket,
        "folder": folder,
        "auto_upload": auto_upload,
    }


@router.post("/test")
async def test_supabase_connection(payload: Optional[Dict[str, Any]] = None):
    """
    Test Supabase Storage bucket connectivity.
    Accepts optional runtime credentials.
    """
    custom_url = payload.get("supabase_url") if payload else None
    custom_key = payload.get("supabase_key") if payload else None
    custom_bucket = payload.get("bucket_name") if payload else None

    result = await supabase_storage_service.test_connection(
        custom_url=custom_url,
        custom_key=custom_key,
        custom_bucket=custom_bucket,
    )
    return result


@router.post("/upload")
async def upload_image_to_supabase(payload: Dict[str, Any]):
    """Download image from URL and upload directly into Supabase Storage."""
    image_url = payload.get("image_url")
    bucket = payload.get("bucket")
    folder = payload.get("folder")
    supabase_url = payload.get("supabase_url")
    supabase_key = payload.get("supabase_key")

    if not image_url:
        raise HTTPException(status_code=400, detail="image_url is required")

    result = await supabase_storage_service.download_and_upload_image(
        image_url=image_url,
        custom_bucket=bucket,
        custom_folder=folder,
        custom_url=supabase_url,
        custom_key=supabase_key,
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Supabase upload failed"))

    return result


@router.post("/sync-job-images/{job_id}")
async def sync_job_images_to_supabase(
    job_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Batch-download and archive all product images for a scraped job to Supabase Storage in the background.
    """
    if not supabase_storage_service.is_configured():
        raise HTTPException(status_code=400, detail="Supabase Storage credentials or bucket not configured.")

    stmt = select(Product).where(Product.job_id == job_id, Product.image_url.isnot(None))
    res = await db.execute(stmt)
    products = res.scalars().all()

    if not products:
        return {"success": True, "message": "No products with images found for this job", "synced": 0}

    async def _process_supabase_sync():
        async with get_db_context() as sync_db:
            q = select(Product).where(Product.job_id == job_id, Product.image_url.isnot(None))
            r = await sync_db.execute(q)
            prods = r.scalars().all()
            for p in prods:
                if p.image_url and not p.supabase_url:
                    upload_res = await supabase_storage_service.download_and_upload_image(p.image_url)
                    if upload_res.get("success"):
                        p.supabase_url = upload_res.get("supabase_url")
                        p.supabase_path = upload_res.get("supabase_path")
            await sync_db.commit()

    background_tasks.add_task(_process_supabase_sync)

    return {
        "success": True,
        "message": f"Started background Supabase sync for {len(products)} products in job {job_id}.",
        "total_products": len(products),
    }
