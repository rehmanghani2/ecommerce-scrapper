"""
Rate Limiter Service.
Orchestrates database persistence and sync with the core in-memory rate limiter engine.
"""

import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.models.throttle import DomainThrottlePolicy
from app.core.rate_limiter import rate_limiter, DEFAULT_DOMAIN_PRESETS

logger = logging.getLogger(__name__)


class RateLimiterService:
    """
    Manages domain throttling policies, syncs database records with runtime engine,
    and exposes telemetry for API routes and dashboards.
    """

    async def init_default_policies_if_empty(self, db: AsyncSession):
        """Ensures common default domain policies exist in the database."""
        try:
            res = await db.execute(select(DomainThrottlePolicy).limit(1))
            first = res.scalar_one_or_none()
            if not first:
                for dom, cfg in DEFAULT_DOMAIN_PRESETS.items():
                    p = DomainThrottlePolicy(
                        domain=dom,
                        requests_per_second=cfg.get("requests_per_second", 2.0),
                        burst_capacity=cfg.get("burst_capacity", 5),
                        max_concurrency=cfg.get("max_concurrency", 2),
                        min_delay_seconds=cfg.get("min_delay_seconds", 0.5),
                        max_delay_seconds=cfg.get("max_delay_seconds", 30.0),
                        backoff_multiplier=cfg.get("backoff_multiplier", 2.0),
                        jitter_type=cfg.get("jitter_type", "full"),
                        is_adaptive=cfg.get("is_adaptive", True),
                    )
                    db.add(p)
                    # Also configure in-memory engine
                    rate_limiter.configure_domain(dom, cfg)
                await db.commit()
        except Exception as e:
            logger.warning(f"Error initializing default rate limit policies: {e}")

    async def list_domain_policies(self, db: AsyncSession) -> List[Dict[str, Any]]:
        """
        Lists all domain policies combined with live telemetry (current delay, 429 count, cooldown).
        """
        await self.init_default_policies_if_empty(db)

        # Get DB records
        res = await db.execute(select(DomainThrottlePolicy).order_by(DomainThrottlePolicy.domain.asc()))
        db_policies = res.scalars().all()

        results = []
        for p in db_policies:
            telemetry = rate_limiter.get_domain_state(p.domain).to_telemetry_dict()
            # Merge persistent settings with real-time state
            item = p.to_dict()
            item["current_delay"] = telemetry.get("current_delay")
            item["cooldown_remaining_seconds"] = telemetry.get("cooldown_remaining_seconds")
            item["runtime_status"] = telemetry.get("status")
            item["consecutive_throttles"] = telemetry.get("consecutive_throttles")
            item["total_requests"] = telemetry.get("total_requests", 0) + p.total_requests
            item["total_throttled_429"] = telemetry.get("total_throttled_429", 0) + p.total_throttled_429
            item["total_errors_503"] = telemetry.get("total_errors_503", 0) + p.total_errors_503
            results.append(item)

        # Also append any dynamic domains currently in memory not yet in DB
        existing_domains = {p.domain for p in db_policies}
        for telem in rate_limiter.get_all_telemetry():
            if telem["domain"] not in existing_domains:
                results.append({
                    "id": None,
                    **telem,
                    "runtime_status": telem.get("status"),
                })

        return results

    async def get_domain_detail(self, db: AsyncSession, domain: str) -> Dict[str, Any]:
        """Fetches policy and telemetry for a specific domain."""
        dom = rate_limiter.extract_domain(domain)
        res = await db.execute(select(DomainThrottlePolicy).where(DomainThrottlePolicy.domain == dom))
        policy = res.scalar_one_or_none()

        telemetry = rate_limiter.get_domain_state(dom).to_telemetry_dict()
        if policy:
            data = policy.to_dict()
            data.update(telemetry)
            return data
        return telemetry

    async def upsert_domain_policy(self, db: AsyncSession, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Creates or updates a rate-limiting policy for a domain."""
        raw_dom = payload.get("domain", "")
        dom = rate_limiter.extract_domain(raw_dom)

        res = await db.execute(select(DomainThrottlePolicy).where(DomainThrottlePolicy.domain == dom))
        policy = res.scalar_one_or_none()

        if not policy:
            policy = DomainThrottlePolicy(domain=dom)
            db.add(policy)

        if "requests_per_second" in payload:
            policy.requests_per_second = float(payload["requests_per_second"])
        if "burst_capacity" in payload:
            policy.burst_capacity = int(payload["burst_capacity"])
        if "max_concurrency" in payload:
            policy.max_concurrency = int(payload["max_concurrency"])
        if "min_delay_seconds" in payload:
            policy.min_delay_seconds = float(payload["min_delay_seconds"])
        if "max_delay_seconds" in payload:
            policy.max_delay_seconds = float(payload["max_delay_seconds"])
        if "backoff_multiplier" in payload:
            policy.backoff_multiplier = float(payload["backoff_multiplier"])
        if "jitter_type" in payload:
            policy.jitter_type = str(payload["jitter_type"])
        if "is_adaptive" in payload:
            policy.is_adaptive = bool(payload["is_adaptive"])

        await db.commit()
        await db.refresh(policy)

        # Update runtime engine
        rate_limiter.configure_domain(dom, payload)
        return await self.get_domain_detail(db, dom)

    async def reset_domain_backoff(self, db: AsyncSession, domain: str) -> Dict[str, Any]:
        """Resets throttling penalties and restores domain to healthy baseline."""
        dom = rate_limiter.extract_domain(domain)
        rate_limiter.reset_domain(dom)

        res = await db.execute(select(DomainThrottlePolicy).where(DomainThrottlePolicy.domain == dom))
        policy = res.scalar_one_or_none()
        if policy:
            policy.status = "healthy"
            policy.consecutive_throttles = 0
            await db.commit()

        return await self.get_domain_detail(db, dom)

    async def delete_domain_policy(self, db: AsyncSession, domain: str) -> Dict[str, Any]:
        """Deletes a custom policy from DB and restores default presets."""
        dom = rate_limiter.extract_domain(domain)
        await db.execute(delete(DomainThrottlePolicy).where(DomainThrottlePolicy.domain == dom))
        await db.commit()

        # Reset runtime
        preset = DEFAULT_DOMAIN_PRESETS.get(dom) or DEFAULT_DOMAIN_PRESETS["default"]
        rate_limiter.configure_domain(dom, preset)
        rate_limiter.reset_domain(dom)

        return {"success": True, "message": f"Policy for {dom} reverted to defaults"}

    def simulate_backoff_curve(self, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Simulates exponential backoff and jitter curve."""
        return rate_limiter.simulate_backoff(
            min_delay=float(payload.get("min_delay_seconds", 0.5)),
            max_delay=float(payload.get("max_delay_seconds", 30.0)),
            multiplier=float(payload.get("backoff_multiplier", 2.0)),
            consecutive_errors=int(payload.get("consecutive_errors", 5)),
            jitter_type=str(payload.get("jitter_type", "full")),
        )


rate_limiter_service = RateLimiterService()
