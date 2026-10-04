"""
Pydantic schemas for scheduled scraping jobs.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class ScheduleCreate(BaseModel):
    """Schema for creating a new scheduled job."""
    name: str = Field(..., min_length=1, max_length=255, description="Human-readable name")
    description: Optional[str] = None
    url: str = Field(..., description="Target website or catalog URL")
    cron_expression: str = Field(default="0 9 * * *", description="Standard 5-part cron expression (e.g. '0 9 * * *' for 9 AM daily)")
    frequency_label: Optional[str] = Field(default="Daily at 09:00 AM", description="Friendly frequency label")
    config: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Scraper configuration (max_pages, proxy, etc.)")


class ScheduleUpdate(BaseModel):
    """Schema for updating an existing scheduled job."""
    name: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None
    cron_expression: Optional[str] = None
    frequency_label: Optional[str] = None
    is_active: Optional[bool] = None
    config: Optional[Dict[str, Any]] = None


class ScheduleResponse(BaseModel):
    """Schema for scheduled job response."""
    id: int
    name: str
    description: Optional[str] = None
    url: str
    domain: str
    cron_expression: str
    frequency_label: Optional[str] = None
    is_active: bool
    config: Dict[str, Any] = {}
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    last_job_id: Optional[int] = None
    total_runs: int = 0
    failed_runs: int = 0
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ScheduleListResponse(BaseModel):
    """Schema for list of scheduled jobs."""
    schedules: List[ScheduleResponse]
    total: int
