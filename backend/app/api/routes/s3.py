"""
AWS S3 & Cloud Storage API Routes.
Enables testing S3 credentials/buckets, uploading single images to S3,
and triggering background image archiving from scrapers to AWS S3 / Cloudflare R2 / MinIO.
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.database import get_db, get_db_context
from app.models.product import Product
from app.services.s3_storage_service import s3_storage_service
from app.config import settings

router = APIRouter(prefix="/s3", tags=["AWS S3 Storage"])


@router.get("/status")
async def get_s3_status():
    """Check AWS S3 configuration status."""
    is_cfg = s3_storage_service.is_configured()
    bucket = getattr(settings, "AWS_S3_BUCKET", None)
    region = getattr(settings, "AWS_REGION", "us-east-1")
    endpoint = getattr(settings, "AWS_S3_ENDPOINT_URL", None)
    prefix = getattr(settings, "AWS_S3_PREFIX", "products")
    auto_upload = getattr(settings, "AWS_S3_AUTO_UPLOAD", False)

    return {
        "configured": is_cfg,
        "bucket": bucket or "Not Configured",
        "region": region,
        "endpoint_url": endpoint or "Default AWS",
        "prefix": prefix,
        "auto_upload": auto_upload,
    }


@router.post("/test")
async def test_s3_connection(payload: Optional[Dict[str, Any]] = None):
    """
    Test AWS S3 bucket connectivity.
    Accepts optional runtime credentials.
    """
    if payload:
        access_key = payload.get("access_key_id")
        secret_key = payload.get("secret_access_key")
        bucket = payload.get("bucket_name")
        region = payload.get("region", "us-east-1")
        endpoint = payload.get("endpoint_url")
        custom_domain = payload.get("custom_domain")

        if access_key and secret_key and bucket:
            s3_storage_service.configure_runtime(
                access_key_id=access_key,
                secret_access_key=secret_key,
                bucket_name=bucket,
                region=region,
                endpoint_url=endpoint,
                custom_domain=custom_domain,
            )

    result = await s3_storage_service.test_connection()
    return result


@router.post("/upload")
async def upload_image_to_s3(payload: Dict[str, Any]):
    """Download image from URL and upload directly into S3 bucket."""
    image_url = payload.get("image_url")
    bucket = payload.get("bucket")
    prefix = payload.get("prefix")

    if not image_url:
        raise HTTPException(status_code=400, detail="image_url is required")

    result = await s3_storage_service.download_and_upload_image(
        image_url=image_url,
        bucket=bucket,
        custom_prefix=prefix,
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "S3 upload failed"))

    return result


@router.post("/sync-job-images/{job_id}")
async def sync_job_images_to_s3(
    job_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Batch-download and archive all product images for a scraped job to AWS S3 in the background.
    """
    if not s3_storage_service.is_configured():
        raise HTTPException(status_code=400, detail="AWS S3 credentials or bucket not configured.")

    stmt = select(Product).where(Product.job_id == job_id, Product.image_url.isnot(None))
    res = await db.execute(stmt)
    products = res.scalars().all()

    if not products:
        return {"success": True, "message": "No products with images found for this job", "synced": 0}

    async def _process_s3_sync():
        async with get_db_context() as sync_db:
            q = select(Product).where(Product.job_id == job_id, Product.image_url.isnot(None))
            r = await sync_db.execute(q)
            prods = r.scalars().all()
            for p in prods:
                if p.image_url and not p.s3_url:
                    upload_res = await s3_storage_service.download_and_upload_image(p.image_url)
                    if upload_res.get("success"):
                        p.s3_url = upload_res.get("s3_url")
                        p.s3_key = upload_res.get("s3_key")
            await sync_db.commit()

    background_tasks.add_task(_process_s3_sync)

    return {
        "success": True,
        "message": f"Started background S3 archive sync for {len(products)} products in job {job_id}.",
        "total_products": len(products),
    }
