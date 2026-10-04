"""
Database models for Price Drop and Stock Alerts (Telegram, Slack, Email, Webhooks).
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Float, ForeignKey, Numeric
from sqlalchemy.sql import func
from .database import Base


class AlertConfig(Base):
    """Configuration for outbound notification channels (Telegram, Slack, Discord, Email)."""
    __tablename__ = "alert_configs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    channel = Column(String(50), nullable=False, index=True)  # telegram, slack, discord, email, webhook
    name = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True)
    min_drop_percentage = Column(Float, default=5.0)  # e.g., trigger alert if price drops >= 5%
    alert_on_out_of_stock = Column(Boolean, default=True)
    alert_on_back_in_stock = Column(Boolean, default=True)
    credentials = Column(Text, nullable=True)  # JSON-encoded tokens, chat IDs, webhook URLs
    last_triggered_at = Column(DateTime(timezone=True), nullable=True)
    last_tested_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<AlertConfig(channel='{self.channel}', name='{self.name}', active={self.is_active})>"


class AlertNotificationLog(Base):
    """Audit log of all triggered price drop and stock alerts."""
    __tablename__ = "alert_notification_logs"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="SET NULL"), nullable=True, index=True)
    product_name = Column(String(500), nullable=False)
    product_url = Column(Text, nullable=True)
    alert_type = Column(String(50), nullable=False, index=True)  # price_drop, out_of_stock, back_in_stock
    channel = Column(String(50), nullable=False, index=True)  # telegram, slack, discord, email, webhook
    old_price = Column(Numeric(12, 2), nullable=True)
    new_price = Column(Numeric(12, 2), nullable=True)
    price_change_percentage = Column(Float, nullable=True)
    currency = Column(String(10), default="USD")
    status = Column(String(20), default="sent")  # sent, failed
    error_message = Column(Text, nullable=True)
    payload_snapshot = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<AlertNotificationLog(product='{self.product_name[:30]}', type='{self.alert_type}', channel='{self.channel}')>"
