"""
Intelligent Scraping Rate-Limiter & Auto-Throttling API routes.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from app.models.database import get_db
from app.services.rate_limiter_service import rate_limiter_service

router = APIRouter(prefix="/throttling", tags=["Scraping Rate-Limiter & Auto-Throttling"])


class DomainPolicyRequest(BaseModel):
    domain: str = Field(..., description="Target domain, e.g. 'amazon.com' or 'walmart.com'")
    requests_per_second: float = Field(2.0, ge=0.1, le=50.0, description="Max allowed requests per second")
    burst_capacity: int = Field(5, ge=1, le=100, description="Token bucket burst capacity")
    max_concurrency: int = Field(2, ge=1, le=50, description="Max simultaneous requests to this domain")
    min_delay_seconds: float = Field(0.5, ge=0.0, le=60.0, description="Baseline polite inter-request delay")
    max_delay_seconds: float = Field(30.0, ge=1.0, le=300.0, description="Ceiling backoff delay upon repeated 429s")
    backoff_multiplier: float = Field(2.0, ge=1.1, le=5.0, description="Exponential backoff power multiplier")
    jitter_type: str = Field("full", description="Jitter strategy: 'full', 'decorrelated', 'equal', 'none'")
    is_adaptive: bool = Field(True, description="Enable automatic backoff on 429/503 and recovery on 200s")


class SimulateBackoffRequest(BaseModel):
    min_delay_seconds: float = Field(0.5, ge=0.1)
    max_delay_seconds: float = Field(30.0, ge=1.0)
    backoff_multiplier: float = Field(2.0, ge=1.1)
    consecutive_errors: int = Field(5, ge=1, le=15)
    jitter_type: str = Field("full")


@router.get("/domains", response_model=List[Dict[str, Any]])
async def list_domain_policies(db: AsyncSession = Depends(get_db)):
    """
    Returns all registered domain rate-limiting policies merged with live runtime telemetry.
    """
    try:
        return await rate_limiter_service.list_domain_policies(db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch rate limiting policies: {str(e)}")


@router.post("/domains")
async def upsert_domain_policy(
    payload: DomainPolicyRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Creates or updates a custom rate limit and backoff policy for a specific target domain.
    """
    try:
        return await rate_limiter_service.upsert_domain_policy(db, payload.model_dump())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save policy: {str(e)}")


@router.get("/domains/{domain}")
async def get_domain_detail(
    domain: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Returns detailed policy settings and real-time backoff telemetry for a specific domain.
    """
    try:
        return await rate_limiter_service.get_domain_detail(db, domain)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch domain detail: {str(e)}")


@router.post("/domains/{domain}/reset")
async def reset_domain_backoff(
    domain: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Immediately clears any active cooldown and resets backoff penalties for the domain back to healthy baseline.
    """
    try:
        return await rate_limiter_service.reset_domain_backoff(db, domain)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reset domain backoff: {str(e)}")


@router.delete("/domains/{domain}")
async def delete_domain_policy(
    domain: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Deletes custom policy override for a domain and restores standard defaults.
    """
    try:
        return await rate_limiter_service.delete_domain_policy(db, domain)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete policy: {str(e)}")


@router.post("/simulate")
async def simulate_backoff_curve(payload: SimulateBackoffRequest):
    """
    Simulates consecutive 429 errors and generates the exponential backoff curve with jitter.
    """
    try:
        return rate_limiter_service.simulate_backoff_curve(payload.model_dump())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Simulation error: {str(e)}")
