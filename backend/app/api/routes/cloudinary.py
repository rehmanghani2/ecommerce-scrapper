"""
Cloudinary Image CDN API Routes.
Enables testing credentials, checking usage/storage statistics,
uploading images, and batch-syncing scraped product photos to Cloudinary CDN.
"""

from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.database import get_db, get_db_context
from app.models.product import Product
from app.services.cloudinary_service import cloudinary_service
from app.config import settings

router = APIRouter(prefix="/cloudinary", tags=["Cloudinary"])


@router.get("/status")
async def get_cloudinary_status():
    """Check Cloudinary configuration status and return public metadata."""
    is_cfg = cloudinary_service.is_configured()
    cloud_name = getattr(settings, "CLOUDINARY_CLOUD_NAME", None)
    auto_upload = getattr(settings, "CLOUDINARY_AUTO_UPLOAD", False)
    folder = getattr(settings, "CLOUDINARY_FOLDER", "ecommerce_scraper")

    return {
        "configured": is_cfg,
        "cloud_name": cloud_name or "Not Configured",
        "folder": folder,
        "auto_upload": auto_upload,
    }


@router.post("/test")
async def test_cloudinary_connection(payload: Optional[Dict[str, Any]] = None):
    """
    Test Cloudinary credentials (optionally passing runtime credentials).
    Returns account plan, storage, and transformation usage.
    """
    if payload:
        cloud_name = payload.get("cloud_name")
        api_key = payload.get("api_key")
        api_secret = payload.get("api_secret")
        cloudinary_url = payload.get("cloudinary_url")
        if cloud_name or cloudinary_url:
            cloudinary_service.configure_runtime(
                cloud_name=cloud_name,
                api_key=api_key,
                api_secret=api_secret,
                cloudinary_url=cloudinary_url,
            )

    result = await cloudinary_service.test_connection()
    return result


@router.post("/upload")
async def upload_single_image(payload: Dict[str, Any]):
    """Upload a single image URL directly to Cloudinary."""
    image_url = payload.get("image_url")
    folder = payload.get("folder")
    public_id = payload.get("public_id")

    if not image_url:
        raise HTTPException(status_code=400, detail="image_url is required")

    result = await cloudinary_service.upload_image_url(
        image_url=image_url,
        folder=folder,
        public_id=public_id,
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Upload failed"))

    return result


@router.post("/sync-job-images/{job_id}")
async def sync_job_images_to_cloudinary(
    job_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Batch-upload all scraped product images for a specific job to Cloudinary CDN in the background.
    """
    if not cloudinary_service.is_configured():
        raise HTTPException(status_code=400, detail="Cloudinary credentials not configured in Settings.")

    stmt = select(Product).where(Product.job_id == job_id, Product.image_url.isnot(None))
    res = await db.execute(stmt)
    products = res.scalars().all()

    if not products:
        return {"success": True, "message": "No products with images found for this job", "synced": 0}

    # Asynchronously process in background task
    async def _process_sync():
        async with get_db_context() as sync_db:
            q = select(Product).where(Product.job_id == job_id, Product.image_url.isnot(None))
            r = await sync_db.execute(q)
            prods = r.scalars().all()
            for p in prods:
                if p.image_url and not p.cloudinary_url:
                    upload_res = await cloudinary_service.upload_image_url(p.image_url)
                    if upload_res.get("success"):
                        p.cloudinary_url = upload_res.get("secure_url")
                        p.cloudinary_public_id = upload_res.get("public_id")
                        if upload_res.get("thumbnail_url"):
                            p.thumbnail_url = upload_res.get("thumbnail_url")
            await sync_db.commit()

    background_tasks.add_task(_process_sync)

    return {
        "success": True,
        "message": f"Started background Cloudinary sync for {len(products)} products in job {job_id}.",
        "total_products": len(products),
    }
