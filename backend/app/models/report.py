"""
Database models for Scheduled Competitor Intelligence Reports via Email and PDF.
Supports periodic automated digests (price changes, catalog diffs, stockout opportunities, sentiment insights).
"""

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean,
    ForeignKey, JSON
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .database import Base


class ReportSchedule(Base):
    """Model representing an automated scheduled competitor intelligence digest."""
    __tablename__ = "report_schedules"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Recipients list: ["exec@company.com", "analyst@company.com"]
    recipient_emails = Column(JSON, default=list, nullable=False)

    # "daily", "weekly", "monthly", "custom"
    frequency = Column(String(50), default="weekly")
    cron_expression = Column(String(100), default="0 9 * * 1")  # Mondays at 9am UTC
    frequency_label = Column(String(100), default="Every Monday at 09:00 AM")

    # "both", "pdf", "email_html"
    format = Column(String(50), default="both")

    # Scope and filters
    domain_filter = Column(String(255), nullable=True)  # Specific competitor domain or null for all
    include_price_drops = Column(Boolean, default=True)
    include_catalog_diffs = Column(Boolean, default=True)
    include_stockouts = Column(Boolean, default=True)
    include_sentiment = Column(Boolean, default=True)

    is_active = Column(Boolean, default=True, index=True)

    last_sent_at = Column(DateTime(timezone=True), nullable=True)
    next_run_at = Column(DateTime(timezone=True), nullable=True, index=True)

    total_sent = Column(Integer, default=0)
    last_status = Column(String(50), default="pending")  # "success", "failed", "pending"
    last_error = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    reports = relationship("GeneratedReport", back_populates="schedule", cascade="all, delete-orphan")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "recipient_emails": self.recipient_emails or [],
            "frequency": self.frequency,
            "cron_expression": self.cron_expression,
            "frequency_label": self.frequency_label,
            "format": self.format,
            "domain_filter": self.domain_filter,
            "include_price_drops": self.include_price_drops,
            "include_catalog_diffs": self.include_catalog_diffs,
            "include_stockouts": self.include_stockouts,
            "include_sentiment": self.include_sentiment,
            "is_active": self.is_active,
            "last_sent_at": self.last_sent_at.isoformat() if self.last_sent_at else None,
            "next_run_at": self.next_run_at.isoformat() if self.next_run_at else None,
            "total_sent": self.total_sent,
            "last_status": self.last_status,
            "last_error": self.last_error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class GeneratedReport(Base):
    """Model storing historical generated intelligence reports and download references."""
    __tablename__ = "generated_reports"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    schedule_id = Column(Integer, ForeignKey("report_schedules.id", ondelete="SET NULL"), nullable=True, index=True)

    title = Column(String(255), nullable=False)
    domain = Column(String(255), nullable=True)

    # Executive metrics snapshot JSON
    metrics_summary = Column(JSON, default=dict)

    html_content = Column(Text, nullable=True)
    pdf_filename = Column(String(255), nullable=True)

    status = Column(String(50), default="ready")  # "ready", "sent", "error"
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    schedule = relationship("ReportSchedule", back_populates="reports")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "schedule_id": self.schedule_id,
            "title": self.title,
            "domain": self.domain,
            "metrics_summary": self.metrics_summary or {},
            "pdf_filename": self.pdf_filename,
            "status": self.status,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
