"""
Database models for Automated Competitor Price Matching and Repricing Webhooks.
Allows users to configure repricing strategies (match price, beat by %, beat by fixed amount, min floor price)
and syncs updated prices back to their Shopify, WooCommerce, or custom Webhook endpoints.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Float, ForeignKey, Numeric
from sqlalchemy.sql import func
from .database import Base


class RepricingRule(Base):
    """Configuration rule for automated competitor price matching."""
    __tablename__ = "repricing_rules"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    name = Column(String(150), nullable=False)
    is_active = Column(Boolean, default=True)

    # Strategy: "beat_by_percentage", "beat_by_fixed", "match_price", "markup_percentage"
    strategy = Column(String(50), default="beat_by_percentage")
    adjustment_value = Column(Float, default=2.0)  # e.g., 2% cheaper or $2.00 cheaper

    # Guardrails / safety limits
    min_floor_price = Column(Numeric(12, 2), nullable=True)  # Never sell below this price (protects profit margin)
    max_ceiling_price = Column(Numeric(12, 2), nullable=True)  # Never reprice above this price
    
    # Target Store / Webhook Action
    # "shopify", "woocommerce", "custom_webhook"
    target_platform = Column(String(50), default="shopify", index=True)
    integration_config_id = Column(Integer, ForeignKey("integration_configs.id", ondelete="SET NULL"), nullable=True)
    
    # Matching Criteria
    # e.g., match by SKU, match by product name similarity, or specific domain filter
    target_domain = Column(String(255), nullable=True)  # e.g. "amazon.com", "walmart.com", or None for all competitors
    webhook_url = Column(Text, nullable=True)  # For custom_webhook target
    webhook_secret = Column(String(255), nullable=True)  # HMAC signature or bearer token

    total_repriced = Column(Integer, default=0)
    last_triggered_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<RepricingRule(id={self.id}, name='{self.name}', strategy='{self.strategy}', active={self.is_active})>"


class RepricingLog(Base):
    """Audit log of automated repricing calculations and store updates."""
    __tablename__ = "repricing_logs"

    id = Column(Integer, primary_key=True, index=True)
    rule_id = Column(Integer, ForeignKey("repricing_rules.id", ondelete="SET NULL"), nullable=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="SET NULL"), nullable=True, index=True)
    
    product_name = Column(String(500), nullable=False)
    product_sku = Column(String(100), nullable=True)
    competitor_domain = Column(String(255), nullable=True)
    
    competitor_price = Column(Numeric(12, 2), nullable=False)
    original_store_price = Column(Numeric(12, 2), nullable=True)
    calculated_new_price = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(10), default="USD")
    
    target_platform = Column(String(50), nullable=False)  # shopify, woocommerce, webhook
    status = Column(String(20), default="applied")  # applied, skipped_floor, failed
    reason = Column(Text, nullable=True)  # e.g. "Hit floor price ($15.00)" or "Updated Shopify SKU PROD-1"
    response_payload = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<RepricingLog(product='{self.product_name[:30]}', new_price={self.calculated_new_price}, status='{self.status}')>"
