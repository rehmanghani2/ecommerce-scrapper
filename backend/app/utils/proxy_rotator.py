"""
Proxy Rotation Module
Manages proxy rotation for avoiding IP-based blocking.
"""

import asyncio
import aiohttp
import random
import time
from typing import List, Optional, Dict, Set
from dataclasses import dataclass, field
from enum import Enum
import logging
from collections import defaultdict

from app.config import settings

logger = logging.getLogger(__name__)


class ProxyType(str, Enum):
    """Types of proxy protocols."""
    HTTP = "http"
    HTTPS = "https"
    SOCKS4 = "socks4"
    SOCKS5 = "socks5"


class ProxyStatus(str, Enum):
    """Status of a proxy."""
    ACTIVE = "active"
    SLOW = "slow"
    FAILED = "failed"
    BANNED = "banned"
    UNKNOWN = "unknown"


@dataclass
class ProxyInfo:
    """Information about a proxy server."""
    host: str
    port: int
    protocol: ProxyType = ProxyType.HTTP
    username: Optional[str] = None
    password: Optional[str] = None
    country: Optional[str] = None
    status: ProxyStatus = ProxyStatus.UNKNOWN
    response_time: float = 0.0
    success_count: int = 0
    fail_count: int = 0
    last_used: float = 0.0
    banned_domains: Set[str] = field(default_factory=set)
    
    @property
    def url(self) -> str:
        """Get the full proxy URL."""
        auth = ""
        if self.username and self.password:
            auth = f"{self.username}:{self.password}@"
        return f"{self.protocol.value}://{auth}{self.host}:{self.port}"
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate of the proxy."""
        total = self.success_count + self.fail_count
        if total == 0:
            return 0.5  # Unknown, assume 50%
        return self.success_count / total
    
    @property
    def score(self) -> float:
        """Calculate overall proxy score for ranking."""
        # Higher is better
        rate_score = self.success_rate * 100
        speed_score = max(0, 100 - self.response_time * 10)  # Penalize slow proxies
        recency_penalty = min(30, (time.time() - self.last_used) / 60)  # Penalty for recently used
        
        return rate_score * 0.5 + speed_score * 0.3 - recency_penalty


class ProxyRotator:
    """
    Manages proxy rotation for web scraping.
    
    Features:
    - Automatic proxy health checking
    - Smart rotation based on success rate
    - Domain-specific proxy banning
    - Proxy pool management
    """
    
    def __init__(
        self,
        proxies: Optional[List[str]] = None,
        check_interval: int = 300,  # 5 minutes
        max_fails: int = 3,
        test_url: str = "https://httpbin.org/ip"
    ):
        """
        Initialize the proxy rotator.
        
        Args:
            proxies: List of proxy URLs
            check_interval: Interval for health checks in seconds
            max_fails: Maximum failures before marking proxy as failed
            test_url: URL to use for proxy testing
        """
        self.proxies: Dict[str, ProxyInfo] = {}
        self.check_interval = check_interval
        self.max_fails = max_fails
        self.test_url = test_url
        self._lock = asyncio.Lock()
        self._domain_proxy_map: Dict[str, str] = {}  # domain -> proxy_url mapping
        
        # Load proxies
        if proxies:
            for proxy_url in proxies:
                self.add_proxy(proxy_url)
        elif settings.PROXY_LIST:
            self._load_proxies_from_config()
    
    def _load_proxies_from_config(self):
        """Load proxies from configuration."""
        proxy_list = settings.PROXY_LIST
        if proxy_list:
            for line in proxy_list.strip().split("\n"):
                line = line.strip()
                if line and not line.startswith("#"):
                    self.add_proxy(line)
    
    def add_proxy(self, proxy_url: str) -> bool:
        """
        Add a proxy to the rotation pool.
        
        Args:
            proxy_url: Proxy URL (e.g., "http://user:pass@host:port")
        
        Returns:
            True if proxy was added successfully
        """
        try:
            # Parse proxy URL
            proxy_info = self._parse_proxy_url(proxy_url)
            if proxy_info:
                self.proxies[proxy_info.url] = proxy_info
                logger.info(f"Added proxy: {proxy_info.host}:{proxy_info.port}")
                return True
        except Exception as e:
            logger.error(f"Failed to add proxy {proxy_url}: {e}")
        return False
    
    def _parse_proxy_url(self, proxy_url: str) -> Optional[ProxyInfo]:
        """Parse a proxy URL into ProxyInfo."""
        from urllib.parse import urlparse
        
        parsed = urlparse(proxy_url)
        if not parsed.hostname or not parsed.port:
            return None
        
        protocol = ProxyType.HTTP
        if parsed.scheme:
            try:
                protocol = ProxyType(parsed.scheme.lower())
            except ValueError:
                protocol = ProxyType.HTTP
        
        return ProxyInfo(
            host=parsed.hostname,
            port=parsed.port,
            protocol=protocol,
            username=parsed.username,
            password=parsed.password
        )
    
    def remove_proxy(self, proxy_url: str):
        """Remove a proxy from the pool."""
        if proxy_url in self.proxies:
            del self.proxies[proxy_url]
            logger.info(f"Removed proxy: {proxy_url}")
    
    async def get_proxy(
        self, 
        domain: Optional[str] = None,
        prefer_fast: bool = True
    ) -> Optional[ProxyInfo]:
        """
        Get a proxy for use.
        
        Args:
            domain: Target domain (for domain-specific selection)
            prefer_fast: Whether to prefer faster proxies
        
        Returns:
            ProxyInfo or None if no proxies available
        """
        async with self._lock:
            if not self.proxies:
                return None
            
            # Filter out failed and banned proxies
            available = [
                p for p in self.proxies.values()
                if p.status not in [ProxyStatus.FAILED, ProxyStatus.BANNED]
                and (domain is None or domain not in p.banned_domains)
            ]
            
            if not available:
                logger.warning("No available proxies")
                return None
            
            if prefer_fast:
                # Sort by score (higher is better)
                available.sort(key=lambda p: p.score, reverse=True)
                # Add some randomness to top choices
                top_count = min(3, len(available))
                proxy = random.choice(available[:top_count])
            else:
                proxy = random.choice(available)
            
            # Update last used time
            proxy.last_used = time.time()
            
            return proxy
    
    async def get_proxy_for_playwright(
        self, 
        domain: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Get proxy configuration for Playwright.
        
        Returns:
            Playwright proxy configuration dict or None
        """
        proxy = await self.get_proxy(domain)
        if not proxy:
            return None
        
        config = {
            "server": f"{proxy.protocol.value}://{proxy.host}:{proxy.port}"
        }
        
        if proxy.username and proxy.password:
            config["username"] = proxy.username
            config["password"] = proxy.password
        
        return config
    
    async def report_success(self, proxy_url: str, response_time: float = 0.0):
        """Report a successful request through a proxy."""
        async with self._lock:
            if proxy_url in self.proxies:
                proxy = self.proxies[proxy_url]
                proxy.success_count += 1
                proxy.response_time = (proxy.response_time + response_time) / 2
                proxy.status = ProxyStatus.ACTIVE
                
                # Reset fail count on success
                if proxy.fail_count > 0:
                    proxy.fail_count = max(0, proxy.fail_count - 1)
    
    async def report_failure(
        self, 
        proxy_url: str, 
        domain: Optional[str] = None,
        is_ban: bool = False
    ):
        """Report a failed request through a proxy."""
        async with self._lock:
            if proxy_url in self.proxies:
                proxy = self.proxies[proxy_url]
                proxy.fail_count += 1
                
                if is_ban and domain:
                    proxy.banned_domains.add(domain)
                    logger.warning(f"Proxy {proxy_url} banned on domain {domain}")
                
                if proxy.fail_count >= self.max_fails:
                    proxy.status = ProxyStatus.FAILED
                    logger.warning(f"Proxy {proxy_url} marked as failed")
                elif proxy.fail_count >= self.max_fails // 2:
                    proxy.status = ProxyStatus.SLOW
    
    async def check_proxy(self, proxy_info: ProxyInfo) -> bool:
        """
        Check if a proxy is working.
        
        Returns:
            True if proxy is working
        """
        try:
            start_time = time.time()
            
            async with aiohttp.ClientSession() as session:
                proxy_url = proxy_info.url
                
                async with session.get(
                    self.test_url,
                    proxy=proxy_url,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        response_time = time.time() - start_time
                        proxy_info.response_time = response_time
                        proxy_info.status = ProxyStatus.ACTIVE
                        logger.debug(f"Proxy {proxy_info.host} is active ({response_time:.2f}s)")
                        return True
            
        except Exception as e:
            logger.debug(f"Proxy check failed for {proxy_info.host}: {e}")
        
        proxy_info.status = ProxyStatus.FAILED
        return False
    
    async def check_all_proxies(self):
        """Check all proxies in the pool."""
        if not self.proxies:
            return
        
        logger.info(f"Checking {len(self.proxies)} proxies...")
        
        tasks = [
            self.check_proxy(proxy)
            for proxy in self.proxies.values()
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        active_count = sum(1 for r in results if r is True)
        logger.info(f"Proxy check complete: {active_count}/{len(self.proxies)} active")
    
    def get_stats(self) -> Dict:
        """Get statistics about the proxy pool."""
        if not self.proxies:
            return {"total": 0, "active": 0, "failed": 0}
        
        status_counts = defaultdict(int)
        for proxy in self.proxies.values():
            status_counts[proxy.status.value] += 1
        
        return {
            "total": len(self.proxies),
            **dict(status_counts),
            "average_response_time": sum(p.response_time for p in self.proxies.values()) / len(self.proxies)
        }


# Singleton instance
_default_rotator: Optional[ProxyRotator] = None


def get_proxy_rotator() -> ProxyRotator:
    """Get the default proxy rotator instance."""
    global _default_rotator
    if _default_rotator is None:
        _default_rotator = ProxyRotator()
    return _default_rotator