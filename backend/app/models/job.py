"""
Job model for tracking scraping jobs.
"""

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Enum, JSON, 
    ForeignKey, Float, Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum
from typing import Optional, Dict, Any

from .database import Base


class JobStatus(str, enum.Enum):
    """Enumeration of possible job statuses."""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobType(str, enum.Enum):
    """Type of scraping job."""
    FULL_SITE = "full_site"
    CATEGORY = "category"
    SEARCH = "search"
    SINGLE_PAGE = "single_page"
    PRODUCT_LIST = "product_list"


class Job(Base):
    """Model representing a scraping job."""
    
    __tablename__ = "jobs"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Job identification
    job_id = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Target configuration
    url = Column(Text, nullable=False)
    domain = Column(String(255), index=True, nullable=False)
    job_type = Column(Enum(JobType), default=JobType.FULL_SITE)
    
    # Status tracking
    status = Column(Enum(JobStatus), default=JobStatus.PENDING, index=True)
    progress = Column(Float, default=0.0)  # 0-100
    
    # Statistics
    total_pages = Column(Integer, default=0)
    scraped_pages = Column(Integer, default=0)
    total_products = Column(Integer, default=0)
    failed_pages = Column(Integer, default=0)
    
    # Configuration
    config = Column(JSON, default=dict)
    """
    Config structure:
    {
        "max_pages": 100,
        "max_depth": 5,
        "include_images": true,
        "include_variants": true,
        "selectors": {...},
        "pagination": {...},
        "filters": {...}
    }
    """
    
    # Timing
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Execution details
    error_message = Column(Text, nullable=True)
    error_trace = Column(Text, nullable=True)
    logs = Column(JSON, default=list)
    
    # Worker info
    celery_task_id = Column(String(100), nullable=True)
    worker_id = Column(String(100), nullable=True)
    
    # User relationship
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    user = relationship("User", back_populates="jobs")
    
    # Products relationship
    products = relationship("Product", back_populates="job", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index("ix_jobs_status_created", "status", "created_at"),
        Index("ix_jobs_domain_status", "domain", "status"),
    )
    
    def __repr__(self):
        return f"<Job(id={self.id}, job_id='{self.job_id}', status='{self.status}')>"
    
    @property
    def duration(self) -> Optional[float]:
        """Calculate job duration in seconds."""
        if self.started_at and self.completed_at:
            start = self.started_at
            end = self.completed_at
            if start.tzinfo is not None and end.tzinfo is None:
                start = start.replace(tzinfo=None)
            elif start.tzinfo is None and end.tzinfo is not None:
                end = end.replace(tzinfo=None)
            return (end - start).total_seconds()
        elif self.started_at:
            start = self.started_at
            if start.tzinfo is not None:
                from datetime import timezone
                now = datetime.now(timezone.utc)
            else:
                now = datetime.utcnow()
            return (now - start).total_seconds()
        return None
    
    @property
    def is_active(self) -> bool:
        """Check if job is currently active."""
        return self.status in [JobStatus.PENDING, JobStatus.QUEUED, JobStatus.RUNNING]
    
    def add_log(self, message: str, level: str = "info"):
        """Add a log entry to the job."""
        if self.logs is None:
            self.logs = []
        self.logs.append({
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,
            "message": message
        })
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert job to dictionary."""
        return {
            "id": self.id,
            "job_id": self.job_id,
            "name": self.name,
            "description": self.description,
            "url": self.url,
            "domain": self.domain,
            "job_type": self.job_type.value if self.job_type else None,
            "status": self.status.value if self.status else None,
            "progress": self.progress,
            "total_pages": self.total_pages,
            "scraped_pages": self.scraped_pages,
            "total_products": self.total_products,
            "failed_pages": self.failed_pages,
            "config": self.config,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration": self.duration,
            "error_message": self.error_message,
        }