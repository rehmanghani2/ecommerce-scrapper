"""
Intelligent Scraping Rate-Limiter & Auto-Throttling Engine (Backoff & Jitter).

Provides enterprise-grade per-domain rate limiting, token bucket flow control,
and adaptive exponential backoff with full/decorrelated jitter to eliminate
HTTP 429 (Too Many Requests), 503 (Service Unavailable), and anti-bot bans.
"""

import asyncio
import logging
import random
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Tuple
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


# Built-in strict presets for major marketplaces
DEFAULT_DOMAIN_PRESETS: Dict[str, Dict[str, Any]] = {
    "amazon.com": {
        "requests_per_second": 1.0,
        "burst_capacity": 3,
        "max_concurrency": 2,
        "min_delay_seconds": 1.5,
        "max_delay_seconds": 60.0,
        "backoff_multiplier": 2.0,
        "jitter_type": "full",
        "is_adaptive": True,
    },
    "walmart.com": {
        "requests_per_second": 1.5,
        "burst_capacity": 4,
        "max_concurrency": 2,
        "min_delay_seconds": 1.0,
        "max_delay_seconds": 45.0,
        "backoff_multiplier": 2.0,
        "jitter_type": "full",
        "is_adaptive": True,
    },
    "ebay.com": {
        "requests_per_second": 3.0,
        "burst_capacity": 6,
        "max_concurrency": 3,
        "min_delay_seconds": 0.5,
        "max_delay_seconds": 30.0,
        "backoff_multiplier": 1.8,
        "jitter_type": "decorrelated",
        "is_adaptive": True,
    },
    "target.com": {
        "requests_per_second": 1.2,
        "burst_capacity": 3,
        "max_concurrency": 2,
        "min_delay_seconds": 1.2,
        "max_delay_seconds": 45.0,
        "backoff_multiplier": 2.0,
        "jitter_type": "full",
        "is_adaptive": True,
    },
    "default": {
        "requests_per_second": 3.0,
        "burst_capacity": 8,
        "max_concurrency": 4,
        "min_delay_seconds": 0.5,
        "max_delay_seconds": 30.0,
        "backoff_multiplier": 2.0,
        "jitter_type": "full",
        "is_adaptive": True,
    },
}


class TokenBucket:
    """
    Asynchronous token bucket algorithm for polite rate limiting.
    Replenishes tokens over time at rate = requests_per_second.
    """

    def __init__(self, capacity: float, rate: float):
        self.capacity = float(max(1.0, capacity))
        self.rate = float(max(0.1, rate))  # tokens per second
        self.tokens = self.capacity
        self.last_update = time.monotonic()
        self._lock = asyncio.Lock()

    def update_params(self, capacity: float, rate: float):
        self.capacity = float(max(1.0, capacity))
        self.rate = float(max(0.1, rate))
        self.tokens = min(self.tokens, self.capacity)

    async def acquire(self, tokens_needed: float = 1.0) -> float:
        """
        Consumes tokens from the bucket.
        If insufficient tokens, sleeps asynchronously until replenished.
        Returns actual wait time in seconds.
        """
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self.last_update
            self.last_update = now

            # Replenish
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)

            if self.tokens >= tokens_needed:
                self.tokens -= tokens_needed
                return 0.0

            # Calculate required wait time
            deficit = tokens_needed - self.tokens
            wait_time = deficit / self.rate
            self.tokens = 0.0

        if wait_time > 0:
            await asyncio.sleep(wait_time)
        return wait_time


class DomainThrottleState:
    """
    Encapsulates dynamic rate limiting and adaptive backoff health for a single domain.
    """

    def __init__(self, domain: str, config: Optional[Dict[str, Any]] = None):
        cfg = config or DEFAULT_DOMAIN_PRESETS.get(domain) or DEFAULT_DOMAIN_PRESETS["default"]

        self.domain = domain
        self.requests_per_second = float(cfg.get("requests_per_second", 2.0))
        self.burst_capacity = int(cfg.get("burst_capacity", 5))
        self.max_concurrency = int(cfg.get("max_concurrency", 2))
        self.min_delay_seconds = float(cfg.get("min_delay_seconds", 0.5))
        self.max_delay_seconds = float(cfg.get("max_delay_seconds", 30.0))
        self.backoff_multiplier = float(cfg.get("backoff_multiplier", 2.0))
        self.jitter_type = str(cfg.get("jitter_type", "full")).lower()
        self.is_adaptive = bool(cfg.get("is_adaptive", True))

        self.status = "healthy"  # healthy, degraded, throttled, cooldown, paused
        self.current_delay = self.min_delay_seconds
        self.consecutive_throttles = 0
        self.consecutive_successes = 0
        self.cooldown_until: float = 0.0

        # Telemetry
        self.total_requests = 0
        self.total_throttled_429 = 0
        self.total_errors_503 = 0
        self.last_throttled_at: Optional[datetime] = None
        self.last_request_at: Optional[datetime] = None

        self.token_bucket = TokenBucket(self.burst_capacity, self.requests_per_second)
        self.semaphore = asyncio.Semaphore(self.max_concurrency)
        self._lock = asyncio.Lock()

    def update_config(self, cfg: Dict[str, Any]):
        if "requests_per_second" in cfg:
            self.requests_per_second = float(cfg["requests_per_second"])
        if "burst_capacity" in cfg:
            self.burst_capacity = int(cfg["burst_capacity"])
        if "max_concurrency" in cfg:
            new_conc = int(cfg["max_concurrency"])
            if new_conc != self.max_concurrency:
                self.max_concurrency = new_conc
                self.semaphore = asyncio.Semaphore(new_conc)
        if "min_delay_seconds" in cfg:
            self.min_delay_seconds = float(cfg["min_delay_seconds"])
        if "max_delay_seconds" in cfg:
            self.max_delay_seconds = float(cfg["max_delay_seconds"])
        if "backoff_multiplier" in cfg:
            self.backoff_multiplier = float(cfg["backoff_multiplier"])
        if "jitter_type" in cfg:
            self.jitter_type = str(cfg["jitter_type"]).lower()
        if "is_adaptive" in cfg:
            self.is_adaptive = bool(cfg["is_adaptive"])

        self.token_bucket.update_params(self.burst_capacity, self.requests_per_second)

    def calculate_jitter(self, base_delay: float) -> float:
        """
        Applies AWS-style jitter to prevent client request synchronization storms.
        """
        if self.jitter_type == "full":
            return round(random.uniform(0.1, base_delay), 2)
        elif self.jitter_type == "decorrelated":
            # Decorrelated Jitter: delay = min(max_delay, uniform(min_delay, current_delay * 3))
            return round(random.uniform(self.min_delay_seconds, min(self.max_delay_seconds, self.current_delay * 3.0)), 2)
        elif self.jitter_type == "equal":
            # Half constant, half jitter
            return round((base_delay / 2.0) + random.uniform(0.0, base_delay / 2.0), 2)
        else:
            return round(base_delay, 2)

    def report_error(self, status_code: int, retry_after: Optional[float] = None):
        """
        Registers HTTP 429 or 503/504 backoff event and increases wait time.
        """
        now_dt = datetime.now(timezone.utc)
        self.last_throttled_at = now_dt
        self.consecutive_throttles += 1
        self.consecutive_successes = 0

        if status_code == 429:
            self.total_throttled_429 += 1
        else:
            self.total_errors_503 += 1

        if not self.is_adaptive:
            return

        # 1. Check if server specified explicit Retry-After
        if retry_after and retry_after > 0:
            effective_delay = min(self.max_delay_seconds, max(float(retry_after), self.min_delay_seconds))
            self.current_delay = round(effective_delay, 2)
        else:
            # 2. Exponential Backoff with Jitter: base * (multiplier ^ throttles)
            raw_backoff = self.min_delay_seconds * (self.backoff_multiplier ** self.consecutive_throttles)
            raw_backoff = min(self.max_delay_seconds, raw_backoff)
            effective_delay = self.calculate_jitter(raw_backoff)
            self.current_delay = max(self.min_delay_seconds, min(self.max_delay_seconds, effective_delay))

        self.cooldown_until = time.monotonic() + self.current_delay
        self.status = "throttled" if self.current_delay >= 5.0 else "degraded"

        logger.warning(
            f"[RateLimiter] Domain '{self.domain}' throttled (HTTP {status_code}). "
            f"Backoff applied: {self.current_delay}s delay (Consecutive: {self.consecutive_throttles})."
        )

    def report_success(self):
        """
        Registers HTTP 200/300 response and gradually restores throughput.
        """
        self.consecutive_successes += 1

        if not self.is_adaptive:
            return

        # Gradual recovery: after 5 consecutive successes, step down delay by 25%
        if self.consecutive_throttles > 0 and self.consecutive_successes >= 5:
            self.current_delay = max(self.min_delay_seconds, round(self.current_delay * 0.75, 2))
            self.consecutive_successes = 0

            if self.current_delay <= self.min_delay_seconds * 1.1:
                self.current_delay = self.min_delay_seconds
                self.consecutive_throttles = 0
                self.status = "healthy"
                logger.info(f"[RateLimiter] Domain '{self.domain}' fully recovered to healthy throughput.")

    def reset(self):
        """Resets backoff state back to healthy defaults."""
        self.current_delay = self.min_delay_seconds
        self.consecutive_throttles = 0
        self.consecutive_successes = 0
        self.cooldown_until = 0.0
        self.status = "healthy"

    def to_telemetry_dict(self) -> Dict[str, Any]:
        cooldown_remaining = max(0.0, round(self.cooldown_until - time.monotonic(), 1))
        return {
            "domain": self.domain,
            "status": self.status if cooldown_remaining <= 0 or self.status == "paused" else "cooldown",
            "requests_per_second": self.requests_per_second,
            "burst_capacity": self.burst_capacity,
            "max_concurrency": self.max_concurrency,
            "min_delay_seconds": self.min_delay_seconds,
            "max_delay_seconds": self.max_delay_seconds,
            "current_delay": self.current_delay,
            "backoff_multiplier": self.backoff_multiplier,
            "jitter_type": self.jitter_type,
            "is_adaptive": self.is_adaptive,
            "consecutive_throttles": self.consecutive_throttles,
            "cooldown_remaining_seconds": cooldown_remaining,
            "total_requests": self.total_requests,
            "total_throttled_429": self.total_throttled_429,
            "total_errors_503": self.total_errors_503,
            "last_throttled_at": self.last_throttled_at.isoformat() if self.last_throttled_at else None,
            "last_request_at": self.last_request_at.isoformat() if self.last_request_at else None,
        }


class DomainRateLimiter:
    """
    Centralized Rate-Limiting & Auto-Throttling Engine.
    Coordinates token bucket flow and adaptive backoff across all scraping threads and jobs.
    """

    def __init__(self):
        self._states: Dict[str, DomainThrottleState] = {}
        self._lock = asyncio.Lock()

    def extract_domain(self, domain_or_url: str) -> str:
        """Extract clean hostname/domain from URL or bare domain string."""
        s = (domain_or_url or "").strip().lower()
        if "://" in s:
            try:
                parsed = urlparse(s)
                return parsed.netloc.split(":")[0].lower() or "default"
            except Exception:
                return "default"
        return s.split(":")[0].split("/")[0] or "default"

    def get_domain_state(self, domain_or_url: str) -> DomainThrottleState:
        domain = self.extract_domain(domain_or_url)
        if domain not in self._states:
            # Match against preset or fallback
            cfg = DEFAULT_DOMAIN_PRESETS.get(domain) or DEFAULT_DOMAIN_PRESETS["default"]
            self._states[domain] = DomainThrottleState(domain, cfg)
        return self._states[domain]

    async def acquire(self, domain_or_url: str) -> Dict[str, Any]:
        """
        Coordinates asynchronous request acquisition:
        1. Checks domain cooldown / active backoff.
        2. Consumes token from Token Bucket (sleeps if needed).
        3. Records request timestamp.
        Returns telemetry info about the acquisition.
        """
        state = self.get_domain_state(domain_or_url)
        
        # 1. Respect cooldown / backoff timer
        now_mono = time.monotonic()
        if state.cooldown_until > now_mono:
            wait_cooldown = state.cooldown_until - now_mono
            logger.debug(f"[RateLimiter] Waiting {wait_cooldown:.2f}s cooldown for domain '{state.domain}'")
            await asyncio.sleep(wait_cooldown)

        # 2. Acquire from TokenBucket
        bucket_wait = await state.token_bucket.acquire(1.0)

        # 3. Apply base inter-request polite delay if specified
        if state.current_delay > 0 and bucket_wait <= 0:
            jittered_delay = state.calculate_jitter(state.current_delay)
            # Sleep small baseline
            sleep_time = min(jittered_delay, 2.0)
            if sleep_time > 0.05:
                await asyncio.sleep(sleep_time)

        state.total_requests += 1
        state.last_request_at = datetime.now(timezone.utc)

        return {
            "domain": state.domain,
            "status": state.status,
            "delay_applied": state.current_delay,
            "consecutive_throttles": state.consecutive_throttles,
        }

    def report_response(
        self,
        domain_or_url: str,
        status_code: int,
        retry_after_header: Optional[str] = None
    ):
        """
        Reports HTTP response status to update domain health and trigger adaptive backoff.
        """
        state = self.get_domain_state(domain_or_url)

        # Parse Retry-After header if present
        retry_after_sec: Optional[float] = None
        if retry_after_header:
            try:
                retry_after_sec = float(retry_after_header.strip())
            except ValueError:
                # Could be HTTP-date, fallback to standard backoff
                retry_after_sec = None

        if status_code in (429, 503, 504):
            state.report_error(status_code, retry_after=retry_after_sec)
        elif 200 <= status_code < 400:
            state.report_success()

    def reset_domain(self, domain_or_url: str) -> Dict[str, Any]:
        """Resets a throttled domain immediately back to healthy status."""
        state = self.get_domain_state(domain_or_url)
        state.reset()
        return state.to_telemetry_dict()

    def configure_domain(self, domain: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Updates or registers a custom policy for a domain."""
        dom = self.extract_domain(domain)
        state = self.get_domain_state(dom)
        state.update_config(config)
        return state.to_telemetry_dict()

    def get_all_telemetry(self) -> List[Dict[str, Any]]:
        """Returns list of real-time telemetry for all registered domain limiters."""
        return [state.to_telemetry_dict() for state in self._states.values()]

    def simulate_backoff(
        self,
        min_delay: float = 0.5,
        max_delay: float = 30.0,
        multiplier: float = 2.0,
        consecutive_errors: int = 5,
        jitter_type: str = "full"
    ) -> List[Dict[str, Any]]:
        """
        Simulates backoff curve steps given parameters. Useful for UI testing and visualization.
        """
        steps = []
        current_delay = min_delay
        for i in range(1, consecutive_errors + 1):
            raw = min(max_delay, min_delay * (multiplier ** i))
            if jitter_type == "full":
                jittered = round(random.uniform(0.1, raw), 2)
            elif jitter_type == "decorrelated":
                jittered = round(random.uniform(min_delay, min(max_delay, current_delay * 3.0)), 2)
            elif jitter_type == "equal":
                jittered = round((raw / 2.0) + random.uniform(0.0, raw / 2.0), 2)
            else:
                jittered = round(raw, 2)

            current_delay = jittered
            steps.append({
                "step": i,
                "consecutive_errors": i,
                "raw_backoff_seconds": round(raw, 2),
                "effective_jitter_delay_seconds": jittered,
                "status_preview": "throttled" if jittered >= 5.0 else "degraded",
            })
        return steps


# Global singleton instance
rate_limiter = DomainRateLimiter()
