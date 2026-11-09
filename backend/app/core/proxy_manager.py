"""
Proxy Pool Manager with Automated Failover & Rotation.
Handles round-robin proxy rotation, health checks, cooldown on 403/429 blocks,
and automated switching for both HTTPX and Playwright scrapers.
"""

import time
import logging
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import urlparse
import httpx

logger = logging.getLogger(__name__)


class ProxyNode:
    """Represents a single proxy endpoint with health and rotation metrics."""

    def __init__(self, raw_url: str):
        self.raw_url = raw_url.strip()
        self.success_count: int = 0
        self.failure_count: int = 0
        self.consecutive_failures: int = 0
        self.cooldown_until: float = 0.0
        self.last_status_code: Optional[int] = None
        self.last_error: Optional[str] = None
        self.latency_ms: Optional[float] = None
        self.is_active: bool = True

        self.scheme, self.host_port, self.username, self.password = self._parse()

    def _parse(self) -> Tuple[str, str, Optional[str], Optional[str]]:
        clean = self.raw_url
        if "://" not in clean:
            clean = f"http://{clean}"
        
        parsed = urlparse(clean)
        scheme = parsed.scheme or "http"
        host_port = f"{parsed.hostname}:{parsed.port}" if parsed.port else parsed.hostname
        username = parsed.username
        password = parsed.password
        return scheme, host_port or "", username, password

    @property
    def is_cooling(self) -> bool:
        """Returns True if the proxy is currently in temporary cooldown."""
        return time.time() < self.cooldown_until

    def to_httpx_proxy(self) -> str:
        """Return formatted string proxy for httpx.AsyncClient."""
        return self.raw_url

    def to_playwright_proxy(self) -> Dict[str, str]:
        """Return formatted proxy dict for Playwright browser context."""
        pw_dict = {"server": f"{self.scheme}://{self.host_port}"}
        if self.username:
            pw_dict["username"] = self.username
        if self.password:
            pw_dict["password"] = self.password
        return pw_dict

    def masked(self) -> str:
        """Safe masked representation without exposing secret password."""
        if self.username and self.password:
            return f"{self.scheme}://{self.username}:****@{self.host_port}"
        return f"{self.scheme}://{self.host_port}"

    def safe_log_label(self) -> str:
        """Safe representation for public job logs masking both credentials and internal IP."""
        parts = self.host_port.split(":")
        ip = parts[0]
        port = f":{parts[1]}" if len(parts) > 1 else ""
        ip_octets = ip.split(".")
        if len(ip_octets) == 4:
            masked_ip = f"{ip_octets[0]}.***.***.{ip_octets[-1]}"
        else:
            masked_ip = f"{ip[:3]}***" if len(ip) > 3 else "***"
        return f"Proxy({masked_ip}{port})"


class ProxyPoolManager:
    """
    Manages a pool of proxies, rotating between them and automatically
    failing over when encountering 403 Forbidden, 429 Too Many Requests,
    or network/tunnel connection timeouts.
    """

    def __init__(
        self,
        proxies: Optional[List[str]] = None,
        failover_enabled: bool = True,
        max_retries: int = 3,
        cooldown_seconds: int = 45,
        max_consecutive_failures: int = 3,
    ):
        self.failover_enabled = failover_enabled
        self.max_retries = max_retries
        self.cooldown_seconds = cooldown_seconds
        self.max_consecutive_failures = max_consecutive_failures

        self.pool: List[ProxyNode] = []
        self._index: int = 0
        self._lock = asyncio.Lock()

        if proxies:
            for p in proxies:
                self.add_proxy(p)

    def add_proxy(self, proxy_str: str) -> bool:
        """Add a proxy to the pool if valid and not a duplicate."""
        if not proxy_str or not proxy_str.strip():
            return False
        clean = proxy_str.strip()
        # Avoid duplicate URLs
        for existing in self.pool:
            if existing.raw_url == clean:
                return False
        try:
            node = ProxyNode(clean)
            if node.host_port:
                self.pool.append(node)
                return True
        except Exception as e:
            logger.warning(f"Failed to parse proxy '{clean}': {e}")
        return False

    def load_from_config(self, proxy_source: Any):
        """Parse proxy list from string, comma-separated, newline-separated, or list."""
        if not proxy_source:
            return
        if isinstance(proxy_source, str):
            lines = [l.strip() for l in proxy_source.replace(",", "\n").splitlines() if l.strip()]
            for line in lines:
                self.add_proxy(line)
        elif isinstance(proxy_source, (list, tuple)):
            for item in proxy_source:
                if isinstance(item, str):
                    self.add_proxy(item)
                elif isinstance(item, dict) and "server" in item:
                    srv = item["server"]
                    usr = item.get("username")
                    pwd = item.get("password")
                    if usr and pwd:
                        if "://" in srv:
                            sch, rest = srv.split("://", 1)
                            self.add_proxy(f"{sch}://{usr}:{pwd}@{rest}")
                        else:
                            self.add_proxy(f"http://{usr}:{pwd}@{srv}")
                    else:
                        self.add_proxy(srv)

    def add_db_records(self, records: List[Any]):
        """Load proxies from database ProxyRecord models, skipping banned and inactive ones."""
        if not records:
            return
        for r in records:
            if not getattr(r, "is_active", True) or getattr(r, "is_banned", False):
                continue
            server = getattr(r, "server", "")
            proto = getattr(r, "protocol", "http")
            user = getattr(r, "username", None)
            pwd = getattr(r, "password", None)
            if user and pwd:
                url = f"{proto}://{user}:{pwd}@{server}"
            else:
                url = f"{proto}://{server}"
            self.add_proxy(url)

    @property
    def total_proxies(self) -> int:
        return len(self.pool)

    @property
    def has_proxies(self) -> bool:
        return len(self.pool) > 0

    def get_next_proxy(self) -> Optional[ProxyNode]:
        """
        Round-robin selection of the next available healthy proxy.
        If all proxies are cooling down, returns the one whose cooldown expires soonest.
        """
        if not self.pool:
            return None

        now = time.time()
        # 1. Search for an available proxy not cooling down
        for _ in range(len(self.pool)):
            node = self.pool[self._index % len(self.pool)]
            self._index = (self._index + 1) % len(self.pool)
            if node.is_active and not node.is_cooling:
                return node

        # 2. All active proxies are cooling down; fallback to least-cooling one
        active_nodes = [p for p in self.pool if p.is_active]
        if active_nodes:
            active_nodes.sort(key=lambda p: p.cooldown_until)
            return active_nodes[0]

        return None

    def report_success(self, proxy: Optional[ProxyNode]):
        """Record successful request using this proxy."""
        if not proxy:
            return
        proxy.success_count += 1
        proxy.consecutive_failures = 0
        proxy.last_status_code = 200
        proxy.last_error = None

    def report_failure(
        self,
        proxy: Optional[ProxyNode],
        status_code: Optional[int] = None,
        error_msg: Optional[str] = None
    ) -> bool:
        """
        Record failed request (403, 429, 503, connection error).
        Returns True if the proxy triggered failover cooldown.
        """
        if not proxy:
            return False

        proxy.failure_count += 1
        proxy.consecutive_failures += 1
        proxy.last_status_code = status_code
        proxy.last_error = error_msg

        # Cooldown trigger on anti-bot/rate-limit blocks or repeated connection drops
        trigger_cooldown = False
        if status_code in (403, 429, 503):
            trigger_cooldown = True
        elif proxy.consecutive_failures >= self.max_consecutive_failures:
            trigger_cooldown = True

        if trigger_cooldown:
            proxy.cooldown_until = time.time() + self.cooldown_seconds
            logger.warning(
                f"[Proxy Failover] Cooldown triggered for proxy {proxy.masked()} "
                f"(Status: {status_code}, Failures: {proxy.consecutive_failures}). "
                f"Cooling down for {self.cooldown_seconds}s."
            )
            return True
        return False

    def get_status_summary(self) -> Dict[str, Any]:
        """Return health metrics and list of proxies in the pool."""
        now = time.time()
        healthy = 0
        cooling = 0
        dead = 0

        details = []
        for p in self.pool:
            is_cool = p.is_cooling
            if not p.is_active or p.consecutive_failures >= (self.max_consecutive_failures * 2):
                dead += 1
                state = "dead"
            elif is_cool:
                cooling += 1
                state = "cooling"
            else:
                healthy += 1
                state = "healthy"

            details.append({
                "proxy": p.masked(),
                "state": state,
                "success_count": p.success_count,
                "failure_count": p.failure_count,
                "consecutive_failures": p.consecutive_failures,
                "last_status": p.last_status_code,
                "last_error": p.last_error,
                "cooldown_remaining_sec": max(0, int(p.cooldown_until - now)) if is_cool else 0,
            })

        return {
            "total": len(self.pool),
            "healthy": healthy,
            "cooling": cooling,
            "dead": dead,
            "failover_enabled": self.failover_enabled,
            "max_retries": self.max_retries,
            "cooldown_seconds": self.cooldown_seconds,
            "proxies": details,
        }

    async def test_proxy(self, proxy: ProxyNode, test_url: str = "https://httpbin.org/ip") -> Dict[str, Any]:
        """Test proxy connectivity, measuring latency and verifying exit IP."""
        t0 = time.time()
        try:
            async with httpx.AsyncClient(
                proxy=proxy.to_httpx_proxy(),
                timeout=12.0,
                verify=False
            ) as client:
                res = await client.get(test_url)
                latency = round((time.time() - t0) * 1000, 1)
                proxy.latency_ms = latency
                if res.status_code == 200:
                    self.report_success(proxy)
                    data = {}
                    try:
                        data = res.json()
                    except Exception:
                        pass
                    return {
                        "proxy": proxy.masked(),
                        "success": True,
                        "status_code": res.status_code,
                        "latency_ms": latency,
                        "origin_ip": data.get("origin", "Verified"),
                    }
                else:
                    self.report_failure(proxy, res.status_code)
                    return {
                        "proxy": proxy.masked(),
                        "success": False,
                        "status_code": res.status_code,
                        "latency_ms": latency,
                        "error": f"HTTP {res.status_code}",
                    }
        except Exception as e:
            latency = round((time.time() - t0) * 1000, 1)
            self.report_failure(proxy, error_msg=str(e))
            return {
                "proxy": proxy.masked(),
                "success": False,
                "latency_ms": latency,
                "error": str(e),
            }

    async def test_all(self, test_url: str = "https://httpbin.org/ip") -> List[Dict[str, Any]]:
        """Test all proxies in the pool concurrently."""
        tasks = [self.test_proxy(p, test_url) for p in self.pool]
        return await asyncio.gather(*tasks)


def build_proxy_pool(
    explicit_proxies: Optional[Any] = None,
    failover_enabled: bool = True,
    max_retries: int = 3,
    db_records: Optional[List[Any]] = None,
) -> ProxyPoolManager:
    """Helper factory to build a configured ProxyPoolManager from app settings, DB, and overrides."""
    from app.config import settings
    import os

    manager = ProxyPoolManager(failover_enabled=failover_enabled, max_retries=max_retries)

    # 1. Explicit request proxies (highest priority)
    if explicit_proxies:
        manager.load_from_config(explicit_proxies)

    # 2. Database managed proxies
    if db_records:
        manager.add_db_records(db_records)

    # 2. Config / Environment PROXY_LIST or PROXY_POOL_LIST
    env_pool = getattr(settings, "PROXY_POOL_LIST", None) or os.environ.get("PROXY_POOL_LIST") or getattr(settings, "PROXY_LIST", None)
    if env_pool:
        manager.load_from_config(env_pool)

    # 3. Default single SCRAPER_PROXY fallback
    single_proxy = getattr(settings, "SCRAPER_PROXY", None) or os.environ.get("SCRAPER_PROXY")
    if single_proxy and not manager.has_proxies:
        manager.load_from_config(single_proxy)

    return manager
