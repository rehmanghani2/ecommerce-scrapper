"""
API Routes for Proxy Pool Management & Domain Health Telemetry Dashboard.
Provides endpoints for CRUD operations, live connectivity pinging, automated/manual blacklisting,
domain-level success rate analysis, and bulk proxy import.
"""

import logging
from typing import List, Dict, Any, Optional, Union
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.services.proxy_service import proxy_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/proxies", tags=["Proxy Pool Management"])


class ImportProxiesRequest(BaseModel):
    proxies: Union[List[str], str] = Field(..., description="List of proxy strings or newline/comma delimited string")
    default_protocol: Optional[str] = Field("http", description="Fallback protocol: http, https, socks5")
    country_code: Optional[str] = Field(None, description="Optional 2-letter country code tag")


class UpdateProxyRequest(BaseModel):
    is_active: Optional[bool] = None
    country_code: Optional[str] = None
    ban_reason: Optional[str] = None


class TestProxyRequest(BaseModel):
    target_url: Optional[str] = Field("https://httpbin.org/ip", description="Target URL to test latency and exit IP")


class ToggleBlacklistRequest(BaseModel):
    is_banned: bool = Field(..., description="True to ban/blacklist, False to unban")
    reason: Optional[str] = Field(None, description="Reason for blacklisting")


@router.get("")
async def get_proxies(
    status: Optional[str] = Query(None, description="Filter by status: healthy, cooling, banned, inactive, all"),
    protocol: Optional[str] = Query(None, description="Filter by protocol: http, https, socks5"),
    search: Optional[str] = Query(None, description="Search by host, IP, or country"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all proxies in the pool with live status calculations and overall health metrics.
    Automatically seeds from config if the table is currently empty.
    """
    try:
        # Seed on initial access if empty
        await proxy_service.seed_from_config(db)
        return await proxy_service.get_all_proxies(db=db, status=status, protocol=protocol, search=search)
    except Exception as e:
        logger.error(f"Error fetching proxies: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("")
async def import_proxies(
    payload: ImportProxiesRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Bulk import or add proxies into the managed pool.
    Supports standard formats (http://user:pass@host:port, ip:port, socks5://...).
    """
    try:
        result = await proxy_service.import_proxies(
            db=db,
            raw_input=payload.proxies,
            default_protocol=payload.default_protocol or "http",
            country_code=payload.country_code
        )
        return result
    except Exception as e:
        logger.error(f"Error importing proxies: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/domain-metrics")
async def get_domain_metrics(db: AsyncSession = Depends(get_db)):
    """
    Retrieve domain-level performance metrics across the entire proxy pool.
    Shows success rate %, latency, healthy/banned proxies for Amazon, Walmart, Target, etc.
    """
    try:
        return await proxy_service.get_domain_metrics_summary(db)
    except Exception as e:
        logger.error(f"Error fetching domain metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test-all")
async def test_all_proxies(
    payload: Optional[TestProxyRequest] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Concurrently test all active, unbanned proxies against a target URL.
    Returns latency, HTTP status code, and verified exit IP.
    """
    try:
        target_url = payload.target_url if payload and payload.target_url else "https://httpbin.org/ip"
        return await proxy_service.test_all_proxies(db=db, target_url=target_url)
    except Exception as e:
        logger.error(f"Error testing proxy pool: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reset-metrics")
async def reset_pool_metrics(db: AsyncSession = Depends(get_db)):
    """
    Reset all success/failure counters and telemetry for all proxies in the pool.
    """
    try:
        return await proxy_service.reset_metrics(db=db)
    except Exception as e:
        logger.error(f"Error resetting pool metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{proxy_id}")
async def update_proxy(
    proxy_id: int,
    payload: UpdateProxyRequest,
    db: AsyncSession = Depends(get_db)
):
    """Update proxy configuration (active status, country code, ban reason)."""
    try:
        data = payload.model_dump() if hasattr(payload, 'model_dump') else payload.dict()
        updated = await proxy_service.update_proxy(db=db, proxy_id=proxy_id, updates=data)
        if not updated:
            raise HTTPException(status_code=404, detail="Proxy not found")
        return updated
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating proxy {proxy_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{proxy_id}")
async def delete_proxy(
    proxy_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Remove a proxy from the pool."""
    try:
        deleted = await proxy_service.delete_proxy(db=db, proxy_id=proxy_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Proxy not found")
        return {"success": True, "message": f"Proxy {proxy_id} deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting proxy {proxy_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{proxy_id}/test")
async def test_single_proxy(
    proxy_id: int,
    payload: Optional[TestProxyRequest] = None,
    db: AsyncSession = Depends(get_db)
):
    """Test connectivity, latency, and exit IP of a single proxy."""
    try:
        target_url = payload.target_url if payload and payload.target_url else "https://httpbin.org/ip"
        result = await proxy_service.test_proxy(db=db, proxy_id=proxy_id, target_url=target_url)
        return result
    except Exception as e:
        logger.error(f"Error testing proxy {proxy_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{proxy_id}/blacklist")
async def toggle_proxy_blacklist(
    proxy_id: int,
    payload: ToggleBlacklistRequest,
    db: AsyncSession = Depends(get_db)
):
    """Manually blacklist or unban a proxy."""
    try:
        updated = await proxy_service.toggle_blacklist(
            db=db,
            proxy_id=proxy_id,
            is_banned=payload.is_banned,
            reason=payload.reason
        )
        if not updated:
            raise HTTPException(status_code=404, detail="Proxy not found")
        return updated
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating blacklist for proxy {proxy_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
