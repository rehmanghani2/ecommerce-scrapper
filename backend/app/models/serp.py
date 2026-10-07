"""
Models for tracking competitor search engine results page (SERP) rankings and visibility.
"""
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Float, Boolean,
    ForeignKey, Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from typing import Dict, Any

from .database import Base


class SerpKeyword(Base):
    """Monitored search query / keyword across e-commerce marketplaces."""
    __tablename__ = "serp_keywords"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    keyword = Column(String(255), index=True, nullable=False)
    domain = Column(String(100), default="amazon.com", index=True, nullable=False)
    marketplace = Column(String(50), default="amazon", nullable=False)  # amazon, ebay, walmart, google_shopping, general
    check_frequency = Column(String(50), default="daily")  # hourly, daily, weekly, manual
    is_active = Column(Boolean, default=True, index=True)
    total_results_count = Column(Integer, default=0)
    last_checked_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    rankings = relationship("SerpRankingItem", back_populates="keyword_ref", cascade="all, delete-orphan", order_by="asc(SerpRankingItem.rank_position)")

    __table_args__ = (
        Index("ix_serp_keywords_kw_domain", "keyword", "domain", unique=True),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "keyword": self.keyword,
            "domain": self.domain,
            "marketplace": self.marketplace,
            "check_frequency": self.check_frequency,
            "is_active": self.is_active,
            "total_results_count": self.total_results_count,
            "last_checked_at": self.last_checked_at.isoformat() if self.last_checked_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class SerpRankingItem(Base):
    """Individual product ranking position in a SERP crawl snapshot."""
    __tablename__ = "serp_ranking_items"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    keyword_id = Column(Integer, ForeignKey("serp_keywords.id", ondelete="CASCADE"), index=True, nullable=False)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="SET NULL"), index=True, nullable=True)

    title = Column(String(500), nullable=False)
    url = Column(Text, nullable=True)
    brand = Column(String(100), nullable=True, index=True)
    price = Column(Float, nullable=True)
    currency = Column(String(10), default="USD")
    image_url = Column(Text, nullable=True)

    rank_position = Column(Integer, index=True, nullable=False)  # 1, 2, 3...
    page_number = Column(Integer, default=1)
    ranking_type = Column(String(50), default="organic", index=True)  # organic, sponsored, amazon_choice, best_seller, editorial
    is_sponsored = Column(Boolean, default=False, index=True)
    badge = Column(String(100), nullable=True)  # e.g. "Best Seller", "Amazon's Choice", "Overall Pick"
    rating = Column(Float, nullable=True)
    review_count = Column(Integer, nullable=True)

    previous_rank = Column(Integer, nullable=True)
    rank_change = Column(Integer, default=0)  # positive = improved, negative = dropped

    recorded_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    keyword_ref = relationship("SerpKeyword", back_populates="rankings")
    product_ref = relationship("Product")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "keyword_id": self.keyword_id,
            "product_id": self.product_id,
            "title": self.title,
            "url": self.url,
            "brand": self.brand,
            "price": self.price,
            "currency": self.currency,
            "image_url": self.image_url,
            "rank_position": self.rank_position,
            "page_number": self.page_number,
            "ranking_type": self.ranking_type,
            "is_sponsored": self.is_sponsored,
            "badge": self.badge,
            "rating": self.rating,
            "review_count": self.review_count,
            "previous_rank": self.previous_rank,
            "rank_change": self.rank_change,
            "recorded_at": self.recorded_at.isoformat() if self.recorded_at else None,
        }
