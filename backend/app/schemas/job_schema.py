"""
Pydantic schemas for job-related operations.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.models.job import JobStatus, JobType


class JobCreate(BaseModel):
    """Schema for creating a new job."""
    
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    url: str
    job_type: JobType = JobType.FULL_SITE
    config: Optional[Dict[str, Any]] = None


class JobUpdate(BaseModel):
    """Schema for updating a job."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    config: Optional[Dict[str, Any]] = None


class JobStatusUpdate(BaseModel):
    """Schema for updating job status."""
    
    status: JobStatus
    error_message: Optional[str] = None


class JobProgress(BaseModel):
    """Schema for job progress updates."""
    
    progress: float = Field(..., ge=0, le=100)
    scraped_pages: int = 0
    total_pages: int = 0
    total_products: int = 0
    current_url: Optional[str] = None
    message: Optional[str] = None


class JobLog(BaseModel):
    """Schema for a job log entry."""
    
    timestamp: datetime
    level: str
    message: str


class JobResponse(BaseModel):
    """Schema for job response."""
    
    id: int
    job_id: str
    name: str
    description: Optional[str]
    url: str
    domain: str
    job_type: str
    status: str
    progress: float
    total_pages: int
    scraped_pages: int
    total_products: int
    failed_pages: int
    config: Optional[Dict[str, Any]]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    duration: Optional[float]
    error_message: Optional[str]
    
    class Config:
        from_attributes = True


class JobListResponse(BaseModel):
    """Schema for paginated job list response."""
    
    jobs: List[JobResponse]
    total: int
    page: int
    page_size: int
    pages: int


class JobStatistics(BaseModel):
    """Schema for job statistics."""
    
    total_jobs: int
    completed_jobs: int
    failed_jobs: int
    running_jobs: int
    total_products: int
    total_pages: int
    average_duration: Optional[float]
    success_rate: float