"""
Proxy Pool Service:
Provides full CRUD, live testing, round-robin rotation queries, automated blacklisting,
cooldown management, and per-domain telemetry for headless browser and HTTP scraping.
"""

import time
import logging
import asyncio
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Tuple, Union
from urllib.parse import urlparse
import httpx
from sqlalchemy import select, func, delete, or_
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.proxy import ProxyRecord
from app.config import settings

logger = logging.getLogger(__name__)


def parse_proxy_string(raw: str, default_protocol: str = "http") -> Optional[Dict[str, Any]]:
    """
    Parses various proxy formats:
    - http://user:pass@1.2.3.4:8080
    - socks5://1.2.3.4:1080
    - user:pass@1.2.3.4:8080
    - 1.2.3.4:8080:user:pass (IP:PORT:USER:PASS format)
    - 1.2.3.4:8080
    """
    clean = raw.strip()
    if not clean or clean.startswith("#"):
        return None

    protocol = default_protocol
    server = ""
    username = None
    password = None

    # Handle IP:PORT:USER:PASS format
    parts = clean.split(":")
    if len(parts) == 4 and "@" not in clean and "://" not in clean:
        server = f"{parts[0]}:{parts[1]}"
        username = parts[2]
        password = parts[3]
        protocol = default_protocol
    else:
        if "://" in clean:
            protocol_part, rest = clean.split("://", 1)
            protocol = protocol_part.lower()
            clean_url = clean
        else:
            clean_url = f"{protocol}://{clean}"

        try:
            parsed = urlparse(clean_url)
            protocol = parsed.scheme or default_protocol
            server = f"{parsed.hostname}:{parsed.port}" if parsed.port else (parsed.hostname or "")
            username = parsed.username
            password = parsed.password
        except Exception as e:
            logger.warning(f"Failed to parse proxy string '{clean}': {e}")
            return None

    if not server:
        return None

    # Construct standard raw_url
    if username and password:
        raw_url = f"{protocol}://{username}:{password}@{server}"
    else:
        raw_url = f"{protocol}://{server}"

    return {
        "raw_url": raw_url,
        "server": server,
        "protocol": protocol,
        "username": username,
        "password": password,
    }


def extract_domain(url: str) -> str:
    """Extract registered domain or hostname from URL."""
    try:
        if "://" not in url:
            url = f"https://{url}"
        parsed = urlparse(url)
        host = parsed.netloc or parsed.path
        if ":" in host:
            host = host.split(":")[0]
        # Remove leading www.
        if host.startswith("www."):
            host = host[4:]
        return host.lower() or "default"
    except Exception:
        return "default"


class ProxyService:
    """Service for managing the database proxy pool and health telemetry."""

    async def seed_from_config(self, db: AsyncSession):
        """Seed proxy table from environment variables or settings if empty."""
        try:
            # Check if any proxy records exist
            stmt = select(func.count(ProxyRecord.id))
            res = await db.execute(stmt)
            count = res.scalar() or 0
            if count > 0:
                return

            candidates = []
            env_pool = getattr(settings, "PROXY_POOL_LIST", None) or getattr(settings, "PROXY_LIST", None)
            if env_pool:
                if isinstance(env_pool, str):
                    candidates.extend(env_pool.replace(",", "\n").splitlines())
                elif isinstance(env_pool, (list, tuple)):
                    candidates.extend([str(x) for x in env_pool])

            single_proxy = getattr(settings, "SCRAPER_PROXY", None)
            if single_proxy:
                candidates.append(single_proxy)

            if candidates:
                await self.import_proxies(db, candidates)
        except Exception as e:
            logger.warning(f"Error seeding proxies from config: {e}")

    async def get_all_proxies(
        self,
        db: AsyncSession,
        status: Optional[str] = None,
        protocol: Optional[str] = None,
        search: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Fetch proxies with filters and calculate comprehensive health summary."""
        stmt = select(ProxyRecord).order_by(ProxyRecord.id.desc())

        if protocol:
            stmt = stmt.where(ProxyRecord.protocol == protocol.lower())

        result = await db.execute(stmt)
        records = result.scalars().all()

        proxies_data = []
        healthy_count = 0
        cooling_count = 0
        banned_count = 0
        inactive_count = 0
        total_latencies = []
        total_success = 0
        total_failures = 0

        for r in records:
            d = r.to_dict()
            state = d["state"]

            # Filter by dynamic state if requested
            if status and status != "all" and state != status:
                continue

            if search:
                query = search.lower()
                if (
                    query not in (r.server or "").lower()
                    and query not in (r.country_code or "").lower()
                    and query not in (r.protocol or "").lower()
                    and query not in (r.ban_reason or "").lower()
                ):
                    continue

            proxies_data.append(d)

        # Pool-wide summary across all records in DB
        for r in records:
            st = r.state
            if st == "healthy":
                healthy_count += 1
            elif st == "cooling":
                cooling_count += 1
            elif st == "banned":
                banned_count += 1
            elif st == "inactive":
                inactive_count += 1

            if r.latency_ms and r.latency_ms > 0:
                total_latencies.append(r.latency_ms)

            total_success += (r.success_count or 0)
            total_failures += (r.failure_count or 0)

        avg_latency = round(sum(total_latencies) / len(total_latencies), 1) if total_latencies else 0.0
        total_reqs = total_success + total_failures
        pool_success_rate = round((total_success / total_reqs * 100), 1) if total_reqs > 0 else 0.0

        return {
            "total": len(records),
            "healthy": healthy_count,
            "cooling": cooling_count,
            "banned": banned_count,
            "inactive": inactive_count,
            "avg_latency_ms": avg_latency,
            "pool_success_rate": pool_success_rate,
            "total_success": total_success,
            "total_failures": total_failures,
            "proxies": proxies_data,
        }

    async def get_proxy_by_id(self, db: AsyncSession, proxy_id: int) -> Optional[ProxyRecord]:
        """Retrieve proxy by ID."""
        return await db.get(ProxyRecord, proxy_id)

    async def import_proxies(
        self,
        db: AsyncSession,
        raw_input: Union[str, List[str]],
        default_protocol: str = "http",
        country_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """Bulk parse and insert proxies, ignoring existing duplicates."""
        if isinstance(raw_input, str):
            lines = [l.strip() for l in raw_input.replace(",", "\n").splitlines() if l.strip()]
        else:
            lines = [str(l).strip() for l in raw_input if str(l).strip()]

        added = 0
        skipped = 0
        errors = 0
        added_records = []

        # Get existing URLs
        stmt = select(ProxyRecord.raw_url)
        res = await db.execute(stmt)
        existing_urls = set(res.scalars().all())

        for line in lines:
            parsed = parse_proxy_string(line, default_protocol=default_protocol)
            if not parsed:
                errors += 1
                continue

            raw_url = parsed["raw_url"]
            if raw_url in existing_urls:
                skipped += 1
                continue

            record = ProxyRecord(
                raw_url=raw_url,
                server=parsed["server"],
                protocol=parsed["protocol"],
                username=parsed["username"],
                password=parsed["password"],
                country_code=country_code,
                is_active=True,
                is_banned=False,
                domain_metrics={},
            )
            db.add(record)
            existing_urls.add(raw_url)
            added_records.append(record)
            added += 1

        if added > 0:
            await db.commit()
            for r in added_records:
                await db.refresh(r)

        return {
            "success": True,
            "added": added,
            "skipped": skipped,
            "errors": errors,
            "total_processed": len(lines),
            "proxies": [r.to_dict() for r in added_records],
        }

    async def update_proxy(
        self,
        db: AsyncSession,
        proxy_id: int,
        updates: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update proxy attributes (is_active, country_code, ban_reason)."""
        record = await db.get(ProxyRecord, proxy_id)
        if not record:
            return None

        for field in ("is_active", "country_code", "ban_reason"):
            if field in updates and updates[field] is not None:
                setattr(record, field, updates[field])

        if "is_banned" in updates:
            record.is_banned = bool(updates["is_banned"])
            if not record.is_banned:
                record.ban_reason = None
                record.consecutive_failures = 0

        await db.commit()
        await db.refresh(record)
        return record.to_dict()

    async def delete_proxy(self, db: AsyncSession, proxy_id: int) -> bool:
        """Delete proxy by ID."""
        record = await db.get(ProxyRecord, proxy_id)
        if not record:
            return False
        await db.delete(record)
        await db.commit()
        return True

    async def test_proxy(
        self,
        db: AsyncSession,
        proxy_id: int,
        target_url: str = "https://httpbin.org/ip",
        timeout: float = 12.0
    ) -> Dict[str, Any]:
        """
        Perform a live test against target_url using the specified proxy.
        Records latency, exit IP, status code, and automatically handles cooldown/bans on 403/429.
        """
        record = await db.get(ProxyRecord, proxy_id)
        if not record:
            return {"success": False, "error": "Proxy not found"}

        now = datetime.now(timezone.utc)
        record.last_checked_at = now
        t0 = time.time()

        try:
            proxy_url = record.to_httpx_proxy()
            async with httpx.AsyncClient(
                proxy=proxy_url,
                timeout=timeout,
                verify=False
            ) as client:
                res = await client.get(target_url)
                latency = round((time.time() - t0) * 1000, 1)
                record.latency_ms = latency
                record.last_status_code = res.status_code

                if res.status_code == 200:
                    record.success_count = (record.success_count or 0) + 1
                    record.consecutive_failures = 0
                    record.last_error = None
                    record.cooldown_until = None

                    # Extract exit IP
                    exit_ip = None
                    try:
                        data = res.json()
                        exit_ip = data.get("origin")
                    except Exception:
                        pass
                    if exit_ip:
                        record.last_exit_ip = exit_ip.split(",")[0].strip()

                    await db.commit()
                    await db.refresh(record)
                    return {
                        "success": True,
                        "proxy_id": record.id,
                        "proxy": record.masked_url(),
                        "status_code": res.status_code,
                        "latency_ms": latency,
                        "exit_ip": record.last_exit_ip,
                        "state": record.state,
                    }
                else:
                    record.failure_count = (record.failure_count or 0) + 1
                    record.consecutive_failures = (record.consecutive_failures or 0) + 1
                    record.last_error = f"HTTP {res.status_code}"

                    # Trigger cooldown on 403 or 429
                    if res.status_code in (403, 429, 503):
                        record.cooldown_until = now + timedelta(seconds=60)

                    # Auto-blacklist if persistent failures
                    if record.consecutive_failures >= 5:
                        record.is_banned = True
                        record.ban_reason = f"Automated ban: {record.consecutive_failures} consecutive HTTP failures ({res.status_code})"

                    await db.commit()
                    await db.refresh(record)
                    return {
                        "success": False,
                        "proxy_id": record.id,
                        "proxy": record.masked_url(),
                        "status_code": res.status_code,
                        "latency_ms": latency,
                        "error": record.last_error,
                        "state": record.state,
                    }

        except Exception as e:
            latency = round((time.time() - t0) * 1000, 1)
            record.latency_ms = latency
            record.failure_count = (record.failure_count or 0) + 1
            record.consecutive_failures = (record.consecutive_failures or 0) + 1
            record.last_error = str(e)
            record.last_status_code = None

            if record.consecutive_failures >= 5:
                record.is_banned = True
                record.ban_reason = f"Automated ban: Connection refused / timeout ({str(e)[:100]})"

            await db.commit()
            await db.refresh(record)
            return {
                "success": False,
                "proxy_id": record.id,
                "proxy": record.masked_url(),
                "latency_ms": latency,
                "error": str(e),
                "state": record.state,
            }

    async def test_all_proxies(
        self,
        db: AsyncSession,
        target_url: str = "https://httpbin.org/ip"
    ) -> Dict[str, Any]:
        """Test all active and unbanned proxies concurrently."""
        stmt = select(ProxyRecord.id).where(ProxyRecord.is_active == True, ProxyRecord.is_banned == False)
        res = await db.execute(stmt)
        ids = res.scalars().all()

        if not ids:
            return {
                "total": 0,
                "successful": 0,
                "failed": 0,
                "results": [],
            }

        tasks = [self.test_proxy(db, pid, target_url=target_url) for pid in ids]
        results = await asyncio.gather(*tasks, return_exceptions=False)

        successful = sum(1 for r in results if r.get("success"))
        failed = len(results) - successful

        return {
            "total": len(results),
            "successful": successful,
            "failed": failed,
            "results": results,
        }

    async def toggle_blacklist(
        self,
        db: AsyncSession,
        proxy_id: int,
        is_banned: bool,
        reason: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Blacklist or unban a proxy manually."""
        record = await db.get(ProxyRecord, proxy_id)
        if not record:
            return None

        record.is_banned = is_banned
        record.ban_reason = reason if is_banned else None
        if not is_banned:
            record.consecutive_failures = 0
            record.cooldown_until = None

        await db.commit()
        await db.refresh(record)
        return record.to_dict()

    async def reset_metrics(
        self,
        db: AsyncSession,
        proxy_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Reset success, failure, latency, and domain metrics."""
        stmt = select(ProxyRecord)
        if proxy_id:
            stmt = stmt.where(ProxyRecord.id == proxy_id)

        res = await db.execute(stmt)
        records = res.scalars().all()

        for r in records:
            r.success_count = 0
            r.failure_count = 0
            r.consecutive_failures = 0
            r.last_error = None
            r.last_status_code = None
            r.domain_metrics = {}

        await db.commit()
        return {"success": True, "reset_count": len(records)}

    async def record_scrape_telemetry(
        self,
        db: AsyncSession,
        proxy_server_or_url: str,
        target_url: str,
        success: bool,
        status_code: Optional[int] = None,
        latency_ms: Optional[float] = None,
        error: Optional[str] = None
    ):
        """
        Record telemetry from live scrapers:
        Updates global counters and per-domain metrics inside ProxyRecord.domain_metrics.
        Auto-blacklists if domain returns repeated 403/CAPTCHA blocks.
        """
        try:
            domain = extract_domain(target_url)

            # Match proxy by server or raw_url
            stmt = select(ProxyRecord).where(
                or_(
                    ProxyRecord.server == proxy_server_or_url,
                    ProxyRecord.raw_url.contains(proxy_server_or_url)
                )
            )
            res = await db.execute(stmt)
            record = res.scalars().first()
            if not record:
                return

            now = datetime.now(timezone.utc)
            metrics = dict(record.domain_metrics or {})
            dom_data = metrics.get(domain, {
                "success": 0,
                "failure": 0,
                "consecutive_blocks": 0,
                "avg_latency_ms": 0.0,
                "last_code": None,
                "is_banned": False,
            })

            if success:
                record.success_count = (record.success_count or 0) + 1
                record.consecutive_failures = 0
                dom_data["success"] = dom_data.get("success", 0) + 1
                dom_data["consecutive_blocks"] = 0
                dom_data["last_code"] = status_code or 200
            else:
                record.failure_count = (record.failure_count or 0) + 1
                record.consecutive_failures = (record.consecutive_failures or 0) + 1
                dom_data["failure"] = dom_data.get("failure", 0) + 1
                dom_data["last_code"] = status_code

                if status_code in (403, 429, 503):
                    dom_data["consecutive_blocks"] = dom_data.get("consecutive_blocks", 0) + 1
                    # Auto domain-level ban if 3 blocks
                    if dom_data["consecutive_blocks"] >= 3:
                        dom_data["is_banned"] = True

                    # Global cooldown
                    record.cooldown_until = now + timedelta(seconds=60)

                if record.consecutive_failures >= 5:
                    record.is_banned = True
                    record.ban_reason = f"Automated ban: Blocked by {domain} (Status {status_code})"

            if latency_ms and latency_ms > 0:
                record.latency_ms = latency_ms
                prev_lat = dom_data.get("avg_latency_ms", 0.0)
                tot_req = dom_data.get("success", 0) + dom_data.get("failure", 0)
                if tot_req > 1 and prev_lat:
                    dom_data["avg_latency_ms"] = round((prev_lat * (tot_req - 1) + latency_ms) / tot_req, 1)
                else:
                    dom_data["avg_latency_ms"] = latency_ms

            metrics[domain] = dom_data
            record.domain_metrics = dict(metrics)
            flag_modified(record, "domain_metrics")
            record.last_checked_at = now
            if status_code:
                record.last_status_code = status_code
            if error:
                record.last_error = error

            await db.commit()
        except Exception as e:
            logger.warning(f"Failed to record scrape telemetry for proxy: {e}")

    async def get_domain_metrics_summary(self, db: AsyncSession) -> List[Dict[str, Any]]:
        """
        Aggregate domain-level metrics across the entire proxy pool.
        Returns statistics for Amazon, Walmart, Target, eBay, Shopify, etc.
        """
        stmt = select(ProxyRecord)
        res = await db.execute(stmt)
        records = res.scalars().all()

        domain_aggregates: Dict[str, Dict[str, Any]] = {}

        for r in records:
            d_metrics = r.domain_metrics or {}
            for domain, data in d_metrics.items():
                if domain not in domain_aggregates:
                    domain_aggregates[domain] = {
                        "domain": domain,
                        "total_requests": 0,
                        "success_count": 0,
                        "failure_count": 0,
                        "healthy_proxies": 0,
                        "banned_proxies": 0,
                        "latencies": [],
                    }

                agg = domain_aggregates[domain]
                succ = data.get("success", 0)
                fail = data.get("failure", 0)
                agg["total_requests"] += (succ + fail)
                agg["success_count"] += succ
                agg["failure_count"] += fail

                if data.get("is_banned"):
                    agg["banned_proxies"] += 1
                else:
                    agg["healthy_proxies"] += 1

                lat = data.get("avg_latency_ms")
                if lat and lat > 0:
                    agg["latencies"].append(lat)

        summary_list = []
        for domain, agg in domain_aggregates.items():
            tot = agg["total_requests"]
            rate = round((agg["success_count"] / tot * 100), 1) if tot > 0 else 0.0
            avg_lat = round(sum(agg["latencies"]) / len(agg["latencies"]), 1) if agg["latencies"] else 0.0

            summary_list.append({
                "domain": domain,
                "total_requests": tot,
                "success_count": agg["success_count"],
                "failure_count": agg["failure_count"],
                "success_rate": rate,
                "avg_latency_ms": avg_lat,
                "healthy_proxies": agg["healthy_proxies"],
                "banned_proxies": agg["banned_proxies"],
            })

        summary_list.sort(key=lambda x: x["total_requests"], reverse=True)
        return summary_list


proxy_service = ProxyService()
