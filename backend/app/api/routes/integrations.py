"""
Integration API routes for 1-Click Sync to Shopify, WooCommerce, and Google Sheets.
"""

import json
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from datetime import datetime

from app.models.database import get_db
from app.models.product import Product
from app.models.job import Job
from app.models.integration import IntegrationConfig, SyncLog
from app.schemas.integration_schema import (
    IntegrationConfigCreate,
    IntegrationConfigUpdate,
    IntegrationConfigResponse,
    IntegrationTestRequest,
    IntegrationTestResponse,
    ProductSyncRequest,
    ProductSyncResponse,
    SyncLogResponse,
)
from app.services.store_integration_service import store_integration_service

router = APIRouter(prefix="/integrations", tags=["Integrations"])


def _mask_credentials(platform: str, creds: Dict[str, Any]) -> Dict[str, Any]:
    """Helper to safely mask API tokens and secrets."""
    masked = dict(creds)
    if "access_token" in masked and masked["access_token"]:
        token = str(masked["access_token"])
        masked["access_token"] = f"{token[:4]}****{token[-4:]}" if len(token) > 8 else "****"
    if "consumer_secret" in masked and masked["consumer_secret"]:
        secret = str(masked["consumer_secret"])
        masked["consumer_secret"] = f"{secret[:4]}****{secret[-4:]}" if len(secret) > 8 else "****"
    return masked


@router.get("/configs", response_model=List[IntegrationConfigResponse])
async def list_configs(db: AsyncSession = Depends(get_db)):
    """List all saved store & cloud integration configurations."""
    query = select(IntegrationConfig).order_by(IntegrationConfig.id)
    result = await db.execute(query)
    configs = result.scalars().all()

    response = []
    for cfg in configs:
        creds = {}
        if cfg.credentials:
            try:
                creds = json.loads(cfg.credentials)
            except Exception:
                pass
        
        response.append(
            IntegrationConfigResponse(
                id=cfg.id,
                platform=cfg.platform,
                name=cfg.name,
                is_active=cfg.is_active,
                masked_credentials=_mask_credentials(cfg.platform, creds),
                last_tested_at=cfg.last_tested_at,
                last_sync_at=cfg.last_sync_at,
                created_at=cfg.created_at,
                updated_at=cfg.updated_at,
            )
        )
    return response


@router.post("/configs", response_model=IntegrationConfigResponse)
async def create_or_update_config(
    payload: IntegrationConfigCreate,
    db: AsyncSession = Depends(get_db)
):
    """Save or update an integration configuration."""
    query = select(IntegrationConfig).where(
        IntegrationConfig.platform == payload.platform,
        IntegrationConfig.name == payload.name
    )
    result = await db.execute(query)
    existing = result.scalar_one_or_none()

    creds_json = json.dumps(payload.credentials)

    if existing:
        existing.credentials = creds_json
        existing.is_active = payload.is_active
        await db.commit()
        await db.refresh(existing)
        cfg = existing
    else:
        cfg = IntegrationConfig(
            platform=payload.platform,
            name=payload.name,
            credentials=creds_json,
            is_active=payload.is_active,
        )
        db.add(cfg)
        await db.commit()
        await db.refresh(cfg)

    return IntegrationConfigResponse(
        id=cfg.id,
        platform=cfg.platform,
        name=cfg.name,
        is_active=cfg.is_active,
        masked_credentials=_mask_credentials(cfg.platform, payload.credentials),
        last_tested_at=cfg.last_tested_at,
        last_sync_at=cfg.last_sync_at,
        created_at=cfg.created_at,
        updated_at=cfg.updated_at,
    )


@router.delete("/configs/{config_id}")
async def delete_config(config_id: int, db: AsyncSession = Depends(get_db)):
    """Delete an integration configuration."""
    cfg = await db.get(IntegrationConfig, config_id)
    if not cfg:
        raise HTTPException(status_code=404, detail="Integration config not found")
    await db.delete(cfg)
    await db.commit()
    return {"success": True, "message": "Integration config deleted"}


@router.post("/test", response_model=IntegrationTestResponse)
async def test_integration(payload: IntegrationTestRequest, db: AsyncSession = Depends(get_db)):
    """Test connection credentials to Shopify, WooCommerce, or Google Sheets."""
    platform = payload.platform.lower()
    creds = payload.credentials

    if platform == "shopify":
        shop_url = creds.get("shop_url") or creds.get("store_url", "")
        access_token = creds.get("access_token", "")
        if not shop_url or not access_token:
            return IntegrationTestResponse(
                success=False,
                message="Shopify requires both 'shop_url' (e.g. your-store.myshopify.com) and 'access_token'."
            )
        success, msg, details = await store_integration_service.test_shopify(shop_url, access_token)
        return IntegrationTestResponse(success=success, message=msg, details=details)

    elif platform == "woocommerce":
        store_url = creds.get("store_url", "")
        ck = creds.get("consumer_key", "")
        cs = creds.get("consumer_secret", "")
        if not store_url or not ck or not cs:
            return IntegrationTestResponse(
                success=False,
                message="WooCommerce requires 'store_url', 'consumer_key', and 'consumer_secret'."
            )
        success, msg, details = await store_integration_service.test_woocommerce(store_url, ck, cs)
        return IntegrationTestResponse(success=success, message=msg, details=details)

    elif platform == "google_sheets":
        webhook_url = creds.get("webhook_url", "")
        if not webhook_url:
            return IntegrationTestResponse(
                success=False,
                message="Google Sheets requires a valid 'webhook_url'."
            )
        success, msg, details = await store_integration_service.test_google_sheets(webhook_url)
        return IntegrationTestResponse(success=success, message=msg, details=details)

    else:
        raise HTTPException(status_code=400, detail=f"Unsupported platform: {platform}")


@router.post("/sync", response_model=ProductSyncResponse)
async def sync_products(
    payload: ProductSyncRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    1-Click Push scraped products into Shopify, WooCommerce, or Google Sheets.
    """
    platform = payload.platform.lower()

    # 1. Fetch products
    products: List[Product] = []
    if payload.product_ids:
        query = select(Product).where(Product.id.in_(payload.product_ids))
        res = await db.execute(query)
        products = res.scalars().all()
    elif payload.job_id:
        job_query = select(Job).where(Job.job_id == payload.job_id)
        job_res = await db.execute(job_query)
        job = job_res.scalar_one_or_none()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        p_query = select(Product).where(Product.job_id == job.id)
        p_res = await db.execute(p_query)
        products = p_res.scalars().all()
    else:
        raise HTTPException(status_code=400, detail="Must provide either product_ids or job_id")

    if not products:
        raise HTTPException(status_code=400, detail="No products found to sync")

    # 2. Resolve credentials (override vs saved config)
    creds = payload.config_override or {}
    config_record = None

    if not creds:
        cfg_query = select(IntegrationConfig).where(
            IntegrationConfig.platform == platform,
            IntegrationConfig.is_active == True
        )
        cfg_res = await db.execute(cfg_query)
        config_record = cfg_res.scalars().first()

        if not config_record or not config_record.credentials:
            raise HTTPException(
                status_code=400,
                detail=f"No saved active configuration found for {platform}. Please configure credentials in Settings or provide config_override."
            )
        try:
            creds = json.loads(config_record.credentials)
        except Exception:
            raise HTTPException(status_code=500, detail="Malformed saved credentials")

    # 3. Execute sync
    sync_result: Dict[str, Any] = {}
    if platform == "shopify":
        shop_url = creds.get("shop_url") or creds.get("store_url", "")
        access_token = creds.get("access_token", "")
        sync_result = await store_integration_service.push_to_shopify(
            products=products,
            shop_url=shop_url,
            access_token=access_token,
            publish_status=payload.publish_status or "draft",
        )
    elif platform == "woocommerce":
        store_url = creds.get("store_url", "")
        ck = creds.get("consumer_key", "")
        cs = creds.get("consumer_secret", "")
        sync_result = await store_integration_service.push_to_woocommerce(
            products=products,
            store_url=store_url,
            consumer_key=ck,
            consumer_secret=cs,
            publish_status=payload.publish_status or "publish",
        )
    elif platform == "google_sheets":
        webhook_url = creds.get("webhook_url", "")
        sync_result = await store_integration_service.push_to_google_sheets(
            products=products,
            webhook_url=webhook_url,
        )
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported sync platform: {platform}")

    # 4. Save audit log and update last_sync_at
    now = datetime.utcnow()
    log_status = "success" if sync_result.get("failed", 0) == 0 else ("partial" if sync_result.get("synced", 0) > 0 else "failed")

    sync_log = SyncLog(
        platform=platform,
        target_name=creds.get("shop_url") or creds.get("store_url") or "Google Sheets",
        items_count=sync_result.get("total", len(products)),
        success_count=sync_result.get("synced", 0),
        failed_count=sync_result.get("failed", 0),
        status=log_status,
        error_message=sync_result.get("message") if log_status != "success" else None,
        details=json.dumps(sync_result.get("items", [])),
    )
    db.add(sync_log)

    if config_record:
        config_record.last_sync_at = now

    await db.commit()

    return ProductSyncResponse(
        success=sync_result.get("success", False),
        platform=platform,
        total=sync_result.get("total", len(products)),
        synced=sync_result.get("synced", 0),
        failed=sync_result.get("failed", 0),
        items=sync_result.get("items", []),
        message=sync_result.get("message", "Sync completed"),
    )


@router.get("/logs", response_model=List[SyncLogResponse])
async def list_sync_logs(
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve history of recent sync operations."""
    query = select(SyncLog).order_by(desc(SyncLog.created_at)).limit(limit)
    res = await db.execute(query)
    logs = res.scalars().all()

    output = []
    for l in logs:
        parsed_details = None
        if l.details:
            try:
                parsed_details = json.loads(l.details)
            except Exception:
                parsed_details = l.details

        output.append(
            SyncLogResponse(
                id=l.id,
                platform=l.platform,
                target_name=l.target_name,
                items_count=l.items_count,
                success_count=l.success_count,
                failed_count=l.failed_count,
                status=l.status,
                error_message=l.error_message,
                details=parsed_details,
                created_at=l.created_at,
            )
        )
    return output


@router.get("/export-csv")
async def export_store_csv(
    platform: str = Query(..., description="shopify, woocommerce, google_sheets"),
    job_id: Optional[str] = Query(None),
    product_ids: Optional[str] = Query(None, description="Comma-separated IDs"),
    db: AsyncSession = Depends(get_db)
):
    """
    Download products formatted for direct store import (Shopify, WooCommerce, or Google Sheets).
    """
    products: List[Product] = []

    if product_ids:
        ids = [int(i.strip()) for i in product_ids.split(",") if i.strip().isdigit()]
        if ids:
            res = await db.execute(select(Product).where(Product.id.in_(ids)))
            products = res.scalars().all()
    elif job_id:
        job_res = await db.execute(select(Job).where(Job.job_id == job_id))
        job = job_res.scalar_one_or_none()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        res = await db.execute(select(Product).where(Product.job_id == job.id))
        products = res.scalars().all()

    if not products:
        # Fallback to latest 50 products
        res = await db.execute(select(Product).order_by(desc(Product.created_at)).limit(50))
        products = res.scalars().all()

    if not products:
        raise HTTPException(status_code=400, detail="No products to export")

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    platform = platform.lower()

    if platform == "shopify":
        csv_content = store_integration_service.generate_shopify_csv(products)
        filename = f"shopify_import_{timestamp}.csv"
    elif platform == "woocommerce":
        csv_content = store_integration_service.generate_woocommerce_csv(products)
        filename = f"woocommerce_import_{timestamp}.csv"
    elif platform in ("google_sheets", "sheets"):
        csv_content = store_integration_service.generate_google_sheets_csv(products)
        filename = f"google_sheets_{timestamp}.csv"
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {platform}")

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )
