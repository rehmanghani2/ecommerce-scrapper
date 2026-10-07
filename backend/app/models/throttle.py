"""
Domain Throttling & Rate Limiting Policy Model.
Stores persistent per-domain rate limits, token-bucket parameters, and adaptive backoff configuration.
"""
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime
from app.models.database import Base


class DomainThrottlePolicy(Base):
    __tablename__ = "domain_throttle_policies"

    id = Column(Integer, primary_key=True, index=True)
    domain = Column(String(255), unique=True, nullable=False, index=True)  # e.g., 'amazon.com', 'walmart.com', 'default'
    requests_per_second = Column(Float, default=2.0, nullable=False)
    burst_capacity = Column(Integer, default=5, nullable=False)
    max_concurrency = Column(Integer, default=2, nullable=False)
    min_delay_seconds = Column(Float, default=0.5, nullable=False)
    max_delay_seconds = Column(Float, default=30.0, nullable=False)
    backoff_multiplier = Column(Float, default=2.0, nullable=False)
    jitter_type = Column(String(50), default="full", nullable=False)  # 'full', 'decorrelated', 'none'
    is_adaptive = Column(Boolean, default=True, nullable=False)
    status = Column(String(50), default="healthy", nullable=False)  # 'healthy', 'degraded', 'throttled', 'cooldown', 'paused'
    consecutive_throttles = Column(Integer, default=0, nullable=False)
    total_requests = Column(Integer, default=0, nullable=False)
    total_throttled_429 = Column(Integer, default=0, nullable=False)
    total_errors_503 = Column(Integer, default=0, nullable=False)
    last_throttled_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "domain": self.domain,
            "requests_per_second": self.requests_per_second,
            "burst_capacity": self.burst_capacity,
            "max_concurrency": self.max_concurrency,
            "min_delay_seconds": self.min_delay_seconds,
            "max_delay_seconds": self.max_delay_seconds,
            "backoff_multiplier": self.backoff_multiplier,
            "jitter_type": self.jitter_type,
            "is_adaptive": self.is_adaptive,
            "status": self.status,
            "consecutive_throttles": self.consecutive_throttles,
            "total_requests": self.total_requests,
            "total_throttled_429": self.total_throttled_429,
            "total_errors_503": self.total_errors_503,
            "last_throttled_at": self.last_throttled_at.isoformat() if self.last_throttled_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
