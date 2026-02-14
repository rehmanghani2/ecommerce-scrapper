"""
Rate Limiting Module
Controls request rates to avoid overwhelming target servers.
"""

import asyncio
import time
from typing import Dict, Optional, Callable, Any
from dataclasses import dataclass
from collections import defaultdict
import logging
from functools import wraps

logger = logging.getLogger(__name__)


@dataclass
class RateLimitState:
    """State for a rate limit bucket."""
    tokens: float
    last_update: float
    request_count: int = 0
    blocked_until: float = 0.0


class RateLimiter:
    """
    Token bucket rate limiter for controlling request rates.
    
    Features:
    - Per-domain rate limiting
    - Configurable burst capacity
    - Async-friendly
    - Automatic token refill
    """
    
    def __init__(
        self,
        requests_per_second: float = 1.0,
        burst_size: int = 5,
        default_delay: float = 1.0
    ):
        """
        Initialize the rate limiter.
        
        Args:
            requests_per_second: Maximum sustained request rate
            burst_size: Maximum burst capacity
            default_delay: Default delay between requests in seconds
        """
        self.requests_per_second = requests_per_second
        self.burst_size = burst_size
        self.default_delay = default_delay
        self._buckets: Dict[str, RateLimitState] = {}
        self._lock = asyncio.Lock()
    
    def _get_bucket(self, key: str) -> RateLimitState:
        """Get or create a rate limit bucket."""
        if key not in self._buckets:
            self._buckets[key] = RateLimitState(
                tokens=float(self.burst_size),
                last_update=time.time()
            )
        return self._buckets[key]
    
    def _refill_tokens(self, bucket: RateLimitState) -> None:
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - bucket.last_update
        
        # Add tokens based on elapsed time
        new_tokens = elapsed * self.requests_per_second
        bucket.tokens = min(self.burst_size, bucket.tokens + new_tokens)
        bucket.last_update = now
    
    async def acquire(self, key: str = "default") -> float:
        """
        Acquire permission to make a request.
        
        Args:
            key: Rate limit bucket key (usually domain)
        
        Returns:
            Time waited in seconds
        """
        async with self._lock:
            bucket = self._get_bucket(key)
            
            # Check if we're blocked
            now = time.time()
            if bucket.blocked_until > now:
                wait_time = bucket.blocked_until - now
                await asyncio.sleep(wait_time)
                return wait_time
            
            # Refill tokens
            self._refill_tokens(bucket)
            
            # Check if we have tokens
            if bucket.tokens >= 1.0:
                bucket.tokens -= 1.0
                bucket.request_count += 1
                return 0.0
            
            # Calculate wait time for next token
            wait_time = (1.0 - bucket.tokens) / self.requests_per_second
            
            # Wait and then take the token
            await asyncio.sleep(wait_time)
            bucket.tokens = 0.0
            bucket.request_count += 1
            
            return wait_time
    
    async def wait(self, key: str = "default"):
        """
        Wait according to rate limit before proceeding.
        Alias for acquire() for simpler usage.
        """
        await self.acquire(key)
    
    def block(self, key: str, duration: float):
        """
        Block a bucket for a specified duration.
        Useful when receiving rate limit responses.
        
        Args:
            key: Rate limit bucket key
            duration: Block duration in seconds
        """
        bucket = self._get_bucket(key)
        bucket.blocked_until = time.time() + duration
        bucket.tokens = 0.0
        logger.warning(f"Rate limit bucket '{key}' blocked for {duration}s")
    
    def get_stats(self, key: str = "default") -> Dict:
        """Get statistics for a rate limit bucket."""
        bucket = self._get_bucket(key)
        return {
            "key": key,
            "tokens": bucket.tokens,
            "request_count": bucket.request_count,
            "is_blocked": bucket.blocked_until > time.time(),
            "blocked_until": bucket.blocked_until if bucket.blocked_until > time.time() else None
        }


class AdaptiveRateLimiter(RateLimiter):
    """
    Adaptive rate limiter that adjusts based on server responses.
    
    Automatically slows down when detecting rate limiting or errors,
    and speeds up when requests are successful.
    """
    
    def __init__(
        self,
        initial_rate: float = 2.0,
        min_rate: float = 0.1,
        max_rate: float = 10.0,
        increase_factor: float = 1.1,
        decrease_factor: float = 0.5,
        **kwargs
    ):
        """
        Initialize the adaptive rate limiter.
        
        Args:
            initial_rate: Starting requests per second
            min_rate: Minimum requests per second
            max_rate: Maximum requests per second
            increase_factor: Factor to increase rate on success
            decrease_factor: Factor to decrease rate on errors
        """
        super().__init__(requests_per_second=initial_rate, **kwargs)
        
        self.initial_rate = initial_rate
        self.min_rate = min_rate
        self.max_rate = max_rate
        self.increase_factor = increase_factor
        self.decrease_factor = decrease_factor
        
        self._domain_rates: Dict[str, float] = defaultdict(lambda: initial_rate)
        self._success_streak: Dict[str, int] = defaultdict(int)
    
    def _get_current_rate(self, key: str) -> float:
        """Get current rate for a key."""
        return self._domain_rates.get(key, self.initial_rate)
    
    async def acquire(self, key: str = "default") -> float:
        """Acquire with adaptive rate."""
        # Update rate limiter with current domain rate
        self.requests_per_second = self._get_current_rate(key)
        return await super().acquire(key)
    
    def report_success(self, key: str = "default"):
        """
        Report a successful request.
        Gradually increases the rate limit.
        """
        self._success_streak[key] += 1
        
        # Increase rate after several successes
        if self._success_streak[key] >= 10:
            current_rate = self._domain_rates[key]
            new_rate = min(self.max_rate, current_rate * self.increase_factor)
            
            if new_rate != current_rate:
                self._domain_rates[key] = new_rate
                logger.debug(f"Increased rate for '{key}' to {new_rate:.2f} req/s")
            
            self._success_streak[key] = 0
    
    def report_error(self, key: str = "default", is_rate_limit: bool = False):
        """
        Report an error or rate limit response.
        Decreases the rate limit.
        """
        self._success_streak[key] = 0
        
        current_rate = self._domain_rates[key]
        
        if is_rate_limit:
            # Aggressive decrease for rate limit errors
            new_rate = max(self.min_rate, current_rate * self.decrease_factor)
            # Also block temporarily
            self.block(key, 30)  # 30 second cooldown
        else:
            # Moderate decrease for other errors
            new_rate = max(self.min_rate, current_rate * (self.decrease_factor + 0.3))
        
        if new_rate != current_rate:
            self._domain_rates[key] = new_rate
            logger.warning(f"Decreased rate for '{key}' to {new_rate:.2f} req/s")
    
    def reset(self, key: str = "default"):
        """Reset rate limit for a key to initial values."""
        self._domain_rates[key] = self.initial_rate
        self._success_streak[key] = 0
        if key in self._buckets:
            del self._buckets[key]


def rate_limited(
    key: Optional[str] = None,
    limiter: Optional[RateLimiter] = None
) -> Callable:
    """
    Decorator for rate-limiting async functions.
    
    Args:
        key: Rate limit key (defaults to function name)
        limiter: RateLimiter instance to use
    
    Usage:
        @rate_limited("api_calls")
        async def make_api_call():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            nonlocal limiter
            if limiter is None:
                limiter = RateLimiter()
            
            limit_key = key or func.__name__
            await limiter.acquire(limit_key)
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


# Global rate limiter instances
_global_limiter: Optional[RateLimiter] = None
_adaptive_limiter: Optional[AdaptiveRateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Get the global rate limiter instance."""
    global _global_limiter
    if _global_limiter is None:
        _global_limiter = RateLimiter()
    return _global_limiter


def get_adaptive_rate_limiter() -> AdaptiveRateLimiter:
    """Get the global adaptive rate limiter instance."""
    global _adaptive_limiter
    if _adaptive_limiter is None:
        _adaptive_limiter = AdaptiveRateLimiter()
    return _adaptive_limiter