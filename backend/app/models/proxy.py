"""
Database models for Proxy Pool Management and Domain-Level Health Monitoring.
Tracks individual proxies, protocol, latency, exit IP, cooldowns, automated bans,
and per-domain success/failure telemetry.
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional
from urllib.parse import urlparse
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Float, JSON
from sqlalchemy.sql import func
from .database import Base


class ProxyRecord(Base):
    """Represents a managed proxy node in the database pool."""
    __tablename__ = "proxy_records"

    id = Column(Integer, primary_key=True, index=True)
    raw_url = Column(Text, nullable=False, unique=True, index=True)
    
    server = Column(String(255), nullable=False)  # host:port
    protocol = Column(String(20), default="http")  # http, https, socks5
    username = Column(String(100), nullable=True)
    password = Column(String(100), nullable=True)
    country_code = Column(String(10), nullable=True)  # e.g., US, DE, GB
    
    is_active = Column(Boolean, default=True, index=True)
    is_banned = Column(Boolean, default=False, index=True)
    ban_reason = Column(String(255), nullable=True)
    
    latency_ms = Column(Float, nullable=True)
    success_count = Column(Integer, default=0)
    failure_count = Column(Integer, default=0)
    consecutive_failures = Column(Integer, default=0)
    
    last_status_code = Column(Integer, nullable=True)
    last_error = Column(Text, nullable=True)
    last_exit_ip = Column(String(100), nullable=True)
    last_checked_at = Column(DateTime(timezone=True), nullable=True)
    cooldown_until = Column(DateTime(timezone=True), nullable=True)
    
    # Per-domain metrics dictionary, e.g.:
    # {"amazon.com": {"success": 42, "fail": 2, "last_code": 200, "banned": false, "latency_ms": 340}}
    domain_metrics = Column(JSON, default=dict)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    @property
    def is_cooling(self) -> bool:
        """Check if currently cooling down."""
        if not self.cooldown_until:
            return False
        now = datetime.now(timezone.utc)
        target = self.cooldown_until
        if target.tzinfo is None:
            target = target.replace(tzinfo=timezone.utc)
        return now < target

    @property
    def state(self) -> str:
        """Dynamic health status: banned, inactive, cooling, or healthy."""
        if self.is_banned:
            return "banned"
        if not self.is_active:
            return "inactive"
        if self.is_cooling:
            return "cooling"
        return "healthy"

    def masked_url(self) -> str:
        """Safe representation masking password."""
        if self.username and self.password:
            return f"{self.protocol}://{self.username}:****@{self.server}"
        return f"{self.protocol}://{self.server}"

    def to_httpx_proxy(self) -> str:
        """Formatted URL for httpx client."""
        if self.username and self.password:
            return f"{self.protocol}://{self.username}:{self.password}@{self.server}"
        return f"{self.protocol}://{self.server}"

    def to_playwright_proxy(self) -> Dict[str, str]:
        """Formatted dictionary for Playwright context."""
        pw_dict = {"server": f"{self.protocol}://{self.server}"}
        if self.username:
            pw_dict["username"] = self.username
        if self.password:
            pw_dict["password"] = self.password
        return pw_dict

    def to_dict(self) -> Dict[str, Any]:
        """Serialized dictionary for API responses."""
        now = datetime.now(timezone.utc)
        cooldown_sec = 0
        if self.is_cooling and self.cooldown_until:
            target = self.cooldown_until
            if target.tzinfo is None:
                target = target.replace(tzinfo=timezone.utc)
            cooldown_sec = max(0, int((target - now).total_seconds()))

        total_reqs = (self.success_count or 0) + (self.failure_count or 0)
        success_rate = round((self.success_count / total_reqs * 100), 1) if total_reqs > 0 else 0.0

        return {
            "id": self.id,
            "raw_url": self.masked_url(),
            "server": self.server,
            "protocol": self.protocol,
            "username": self.username,
            "has_auth": bool(self.username and self.password),
            "country_code": self.country_code or "Unknown",
            "is_active": self.is_active,
            "is_banned": self.is_banned,
            "ban_reason": self.ban_reason,
            "state": self.state,
            "latency_ms": self.latency_ms,
            "success_count": self.success_count or 0,
            "failure_count": self.failure_count or 0,
            "consecutive_failures": self.consecutive_failures or 0,
            "success_rate": success_rate,
            "last_status_code": self.last_status_code,
            "last_error": self.last_error,
            "last_exit_ip": self.last_exit_ip,
            "last_checked_at": self.last_checked_at.isoformat() if self.last_checked_at else None,
            "cooldown_remaining_sec": cooldown_sec,
            "domain_metrics": self.domain_metrics or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
