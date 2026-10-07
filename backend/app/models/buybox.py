"""
Models for Marketplace Buy Box Win/Loss Tracking & Algorithmic Prediction.
"""
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Float, Boolean,
    ForeignKey, Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from typing import Dict, Any

from .database import Base


class ProductBuyBoxState(Base):
    """Current state and prediction metrics of a marketplace Buy Box for a product."""
    __tablename__ = "product_buybox_states"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), unique=True, index=True, nullable=False)

    marketplace = Column(String(50), default="amazon", nullable=False)  # amazon, walmart, ebay
    current_winner = Column(String(255), nullable=True)  # e.g., "Amazon.com", "AnkerDirect"
    is_amazon_sold = Column(Boolean, default=False)
    winner_price = Column(Float, nullable=True)
    winner_shipping_price = Column(Float, default=0.0)
    fulfillment_type = Column(String(50), default="fba")  # fba, fbm, wfs, retail
    is_suppressed = Column(Boolean, default=False, index=True)
    competing_sellers_count = Column(Integer, default=1)
    lowest_competing_price = Column(Float, nullable=True)

    # User's tracked merchant store context
    tracked_seller_name = Column(String(255), nullable=True)
    is_tracked_seller_winner = Column(Boolean, default=False, index=True)
    tracked_seller_price = Column(Float, nullable=True)
    tracked_seller_fulfillment = Column(String(50), default="fba")

    # Predictive Intelligence
    win_probability_pct = Column(Float, default=0.0)  # 0.0 - 100.0%
    target_winning_price = Column(Float, nullable=True)
    status_verdict = Column(Text, nullable=True)

    last_checked_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    product = relationship("Product", back_populates="buybox_state")
    history = relationship("ProductBuyBoxHistory", back_populates="state_ref", cascade="all, delete-orphan", order_by="desc(ProductBuyBoxHistory.recorded_at)")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "product_id": self.product_id,
            "marketplace": self.marketplace,
            "current_winner": self.current_winner,
            "is_amazon_sold": self.is_amazon_sold,
            "winner_price": round(self.winner_price, 2) if self.winner_price is not None else None,
            "winner_shipping_price": round(self.winner_shipping_price, 2) if self.winner_shipping_price is not None else 0.0,
            "fulfillment_type": self.fulfillment_type,
            "is_suppressed": self.is_suppressed,
            "competing_sellers_count": self.competing_sellers_count,
            "lowest_competing_price": round(self.lowest_competing_price, 2) if self.lowest_competing_price is not None else None,
            "tracked_seller_name": self.tracked_seller_name,
            "is_tracked_seller_winner": self.is_tracked_seller_winner,
            "tracked_seller_price": round(self.tracked_seller_price, 2) if self.tracked_seller_price is not None else None,
            "tracked_seller_fulfillment": self.tracked_seller_fulfillment,
            "win_probability_pct": round(self.win_probability_pct, 1) if self.win_probability_pct is not None else 0.0,
            "target_winning_price": round(self.target_winning_price, 2) if self.target_winning_price is not None else None,
            "status_verdict": self.status_verdict,
            "last_checked_at": self.last_checked_at.isoformat() if self.last_checked_at else None,
        }


class ProductBuyBoxHistory(Base):
    """Historical event log of Buy Box transitions, wins, losses, and suppressions."""
    __tablename__ = "product_buybox_history"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    buybox_id = Column(Integer, ForeignKey("product_buybox_states.id", ondelete="CASCADE"), index=True, nullable=False)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), index=True, nullable=False)

    winner_name = Column(String(255), nullable=True)
    winner_price = Column(Float, nullable=True)
    fulfillment_type = Column(String(50), default="fba")
    event_type = Column(String(50), default="observation", index=True)  # won, lost, suppressed, restored, price_change, observation
    lost_to_seller = Column(String(255), nullable=True)
    price_delta_vs_previous = Column(Float, nullable=True)
    recorded_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    state_ref = relationship("ProductBuyBoxState", back_populates="history")
    product = relationship("Product", back_populates="buybox_history")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "buybox_id": self.buybox_id,
            "product_id": self.product_id,
            "winner_name": self.winner_name,
            "winner_price": round(self.winner_price, 2) if self.winner_price is not None else None,
            "fulfillment_type": self.fulfillment_type,
            "event_type": self.event_type,
            "lost_to_seller": self.lost_to_seller,
            "price_delta_vs_previous": round(self.price_delta_vs_previous, 2) if self.price_delta_vs_previous is not None else None,
            "recorded_at": self.recorded_at.isoformat() if self.recorded_at else None,
        }
