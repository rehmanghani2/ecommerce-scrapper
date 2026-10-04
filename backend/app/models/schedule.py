"""
ScheduledJob model for recurring automated scraper jobs.
"""

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean,
    ForeignKey, JSON
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from typing import Dict, Any

from .database import Base


class ScheduledJob(Base):
    """Model representing a recurring scheduled scraping job."""
    
    __tablename__ = "scheduled_jobs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    url = Column(Text, nullable=False)
    domain = Column(String(255), index=True, nullable=False)

    cron_expression = Column(String(100), nullable=False, default="0 9 * * *")
    frequency_label = Column(String(100), default="Daily at 09:00 AM")

    is_active = Column(Boolean, default=True, index=True)
    config = Column(JSON, default=dict)

    last_run_at = Column(DateTime(timezone=True), nullable=True)
    next_run_at = Column(DateTime(timezone=True), nullable=True, index=True)
    last_job_id = Column(Integer, ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True)

    total_runs = Column(Integer, default=0)
    failed_runs = Column(Integer, default=0)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    user = relationship("User")
    last_job = relationship("Job")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<ScheduledJob(id={self.id}, name='{self.name}', cron='{self.cron_expression}', active={self.is_active})>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert scheduled job to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "url": self.url,
            "domain": self.domain,
            "cron_expression": self.cron_expression,
            "frequency_label": self.frequency_label,
            "is_active": self.is_active,
            "config": self.config or {},
            "last_run_at": self.last_run_at.isoformat() if self.last_run_at else None,
            "next_run_at": self.next_run_at.isoformat() if self.next_run_at else None,
            "last_job_id": self.last_job_id,
            "total_runs": self.total_runs,
            "failed_runs": self.failed_runs,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
