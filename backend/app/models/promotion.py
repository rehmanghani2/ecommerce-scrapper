"""
Promotion and coupon models for competitor promotion & bundle tracking.
"""
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Float, Boolean,
    ForeignKey, Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from typing import Dict, Any

from .database import Base


class ProductPromotion(Base):
    """
    Model representing competitor promotions, coupons, vouchers, BOGO deals, and volume tiers.
    """
    __tablename__ = "product_promotions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), index=True, nullable=False)

    # Promo classification: "coupon_code", "percentage_discount", "fixed_amount_discount", "bogo", "volume_tier", "bundle_deal", "flash_sale", "free_shipping"
    promo_type = Column(String(50), index=True, nullable=False)
    title = Column(String(255), nullable=False)
    coupon_code = Column(String(100), nullable=True, index=True)
    discount_type = Column(String(50), default="percentage")  # "percentage", "fixed_amount", "bogo", "free_shipping", "custom"
    discount_value = Column(Float, nullable=True)  # e.g., 20.0 for 20% or 10.0 for $10
    
    # Financial metrics
    original_price = Column(Float, nullable=True)
    effective_price = Column(Float, nullable=True)  # Calculated net price after applying promo
    savings_amount = Column(Float, nullable=True)   # Dollar amount saved
    minimum_spend = Column(Float, nullable=True)    # Minimum cart order threshold
    
    # BOGO / Volume Tier specifics
    bogo_buy_qty = Column(Integer, nullable=True)       # e.g., Buy 1
    bogo_get_qty = Column(Integer, nullable=True)       # e.g., Get 1
    bogo_discount_pct = Column(Float, nullable=True)    # e.g., 100.0 (free) or 50.0 (half off)
    volume_min_qty = Column(Integer, nullable=True)     # e.g., Buy 3 or more
    
    # Context & Terms
    banner_text = Column(String(500), nullable=True)
    description = Column(Text, nullable=True)
    terms = Column(Text, nullable=True)
    
    # Lifecycle
    is_active = Column(Boolean, default=True, index=True)
    start_date = Column(DateTime(timezone=True), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=True)
    detected_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationship
    product = relationship("Product", back_populates="promotions")

    __table_args__ = (
        Index("ix_product_promotions_active_type", "is_active", "promo_type"),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "product_id": self.product_id,
            "promo_type": self.promo_type,
            "title": self.title,
            "coupon_code": self.coupon_code,
            "discount_type": self.discount_type,
            "discount_value": round(self.discount_value, 2) if self.discount_value is not None else None,
            "original_price": round(self.original_price, 2) if self.original_price is not None else None,
            "effective_price": round(self.effective_price, 2) if self.effective_price is not None else None,
            "savings_amount": round(self.savings_amount, 2) if self.savings_amount is not None else None,
            "minimum_spend": round(self.minimum_spend, 2) if self.minimum_spend is not None else None,
            "bogo_buy_qty": self.bogo_buy_qty,
            "bogo_get_qty": self.bogo_get_qty,
            "bogo_discount_pct": self.bogo_discount_pct,
            "volume_min_qty": self.volume_min_qty,
            "banner_text": self.banner_text,
            "description": self.description,
            "terms": self.terms,
            "is_active": self.is_active,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "detected_at": self.detected_at.isoformat() if self.detected_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
