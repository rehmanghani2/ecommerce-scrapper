"""
Database models for store and cloud integrations (Shopify, WooCommerce, Google Sheets).
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from .database import Base


class IntegrationConfig(Base):
    """Configuration and credentials for third-party store/cloud sync."""
    __tablename__ = "integration_configs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    platform = Column(String(50), nullable=False, index=True)  # shopify, woocommerce, google_sheets
    name = Column(String(100), nullable=False)
    credentials = Column(Text, nullable=True)  # JSON-encoded credentials
    is_active = Column(Boolean, default=True)
    last_tested_at = Column(DateTime(timezone=True), nullable=True)
    last_sync_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<IntegrationConfig(platform='{self.platform}', name='{self.name}')>"


class SyncLog(Base):
    """Audit log of sync operations to external platforms."""
    __tablename__ = "sync_logs"

    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String(50), nullable=False, index=True)
    target_name = Column(String(100), nullable=True)
    items_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    status = Column(String(20), default="success")  # success, partial, failed
    error_message = Column(Text, nullable=True)
    details = Column(Text, nullable=True)  # JSON details of synced items
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<SyncLog(platform='{self.platform}', status='{self.status}', items={self.items_count})>"
