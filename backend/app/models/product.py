"""
Product model for storing scraped product data.
"""

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Float, Boolean,
    ForeignKey, JSON, Index, Numeric
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from typing import Dict, Any

from .database import Base


class Product(Base):
    """Model representing a scraped product."""
    
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Product identification
    product_id = Column(String(100), index=True)  # Original product ID from website
    sku = Column(String(100), index=True, nullable=True)
    upc = Column(String(50), nullable=True)
    ean = Column(String(50), nullable=True)
    
    # Basic info
    name = Column(String(500), nullable=False)
    title = Column(Text, nullable=True)  # Full title if different from name
    description = Column(Text, nullable=True)
    short_description = Column(Text, nullable=True)
    
    # Pricing
    price = Column(Numeric(12, 2), nullable=True)
    previous_price = Column(Numeric(12, 2), nullable=True)
    price_change = Column(Numeric(12, 2), nullable=True)
    price_change_percentage = Column(Float, nullable=True)
    lowest_price = Column(Numeric(12, 2), nullable=True)
    highest_price = Column(Numeric(12, 2), nullable=True)
    original_price = Column(Numeric(12, 2), nullable=True)
    sale_price = Column(Numeric(12, 2), nullable=True)
    currency = Column(String(10), default="GBP")
    normalized_price = Column(Numeric(12, 2), nullable=True)  # Price converted to user's target currency
    normalized_currency = Column(String(10), nullable=True)  # Target currency code e.g. USD
    exchange_rate = Column(Float, nullable=True)  # Rate used for conversion
    price_text = Column(String(100), nullable=True)  # Original price string
    discount_percentage = Column(Float, nullable=True)
    
    # Availability
    in_stock = Column(Boolean, default=True)
    stock_quantity = Column(Integer, nullable=True)
    stock_status = Column(String(50), nullable=True)
    
    # URLs
    url = Column(Text, nullable=False)
    image_url = Column(Text, nullable=True)
    thumbnail_url = Column(Text, nullable=True)
    cloudinary_url = Column(Text, nullable=True)
    cloudinary_public_id = Column(String(255), nullable=True)
    s3_url = Column(Text, nullable=True)
    s3_key = Column(String(500), nullable=True)
    supabase_url = Column(Text, nullable=True)
    supabase_path = Column(String(500), nullable=True)
    
    # Categorization
    category = Column(String(255), nullable=True)
    subcategory = Column(String(255), nullable=True)
    category_path = Column(Text, nullable=True)  # Full path: Electronics > Phones > iPhone
    categories = Column(JSON, default=list)  # List of all categories
    
    # Brand & Manufacturer
    brand = Column(String(255), nullable=True)
    manufacturer = Column(String(255), nullable=True)
    vendor = Column(String(255), nullable=True)
    
    # Specifications
    specifications = Column(JSON, default=dict)
    """
    {
        "Weight": "1.5 kg",
        "Dimensions": "10x20x5 cm",
        "Color": "Black",
        ...
    }
    """
    
    # Additional data
    features = Column(JSON, default=list)  # List of product features
    tags = Column(JSON, default=list)  # Product tags
    attributes = Column(JSON, default=dict)  # Any additional attributes
    
    # Reviews
    rating = Column(Float, nullable=True)
    review_count = Column(Integer, default=0)
    
    # Metadata
    meta_title = Column(Text, nullable=True)
    meta_description = Column(Text, nullable=True)
    
    # Scraping info
    source_domain = Column(String(255), index=True)
    scraped_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    raw_data = Column(JSON, default=dict)  # Original raw scraped data
    
    # Cross-Store Competitor Product Matching
    match_cluster_id = Column(String(100), index=True, nullable=True)  # Cluster group ID connecting identical competitor products
    match_confidence = Column(Float, nullable=True)  # Similarity confidence score (0.0 - 1.0)
    
    # Job relationship
    job_id = Column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    job = relationship("Job", back_populates="products")
    
    # Related data
    images = relationship("ProductImage", back_populates="product", cascade="all, delete-orphan")
    variants = relationship("ProductVariant", back_populates="product", cascade="all, delete-orphan")
    price_history = relationship("PriceHistory", back_populates="product", cascade="all, delete-orphan", order_by="desc(PriceHistory.recorded_at)")
    reviews = relationship("ProductReview", back_populates="product", cascade="all, delete-orphan", order_by="desc(ProductReview.created_at)")
    sentiment_summary = relationship("ProductSentimentSummary", back_populates="product", uselist=False, cascade="all, delete-orphan")
    stock_history = relationship("ProductStockHistory", back_populates="product", cascade="all, delete-orphan", order_by="desc(ProductStockHistory.recorded_at)")
    inventory_forecast = relationship("ProductInventoryForecast", back_populates="product", uselist=False, cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index("ix_products_name_domain", "name", "source_domain"),
        Index("ix_products_category_domain", "category", "source_domain"),
        Index("ix_products_brand_domain", "brand", "source_domain"),
    )
    
    def __repr__(self):
        return f"<Product(id={self.id}, name='{self.name[:50]}...', price={self.price})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert product to dictionary."""
        return {
            "id": self.id,
            "product_id": self.product_id,
            "sku": self.sku,
            "name": self.name,
            "description": self.description,
            "price": float(self.price) if self.price else None,
            "previous_price": float(self.previous_price) if self.previous_price else None,
            "price_change": float(self.price_change) if self.price_change else None,
            "price_change_percentage": self.price_change_percentage,
            "lowest_price": float(self.lowest_price) if self.lowest_price else None,
            "highest_price": float(self.highest_price) if self.highest_price else None,
            "original_price": float(self.original_price) if self.original_price else None,
            "sale_price": float(self.sale_price) if self.sale_price else None,
            "currency": self.currency,
            "normalized_price": float(self.normalized_price) if self.normalized_price else None,
            "normalized_currency": self.normalized_currency,
            "exchange_rate": self.exchange_rate,
            "price_text": self.price_text,
            "in_stock": self.in_stock,
            "stock_quantity": self.stock_quantity,
            "url": self.url,
            "image_url": self.image_url,
            "cloudinary_url": self.cloudinary_url,
            "cloudinary_public_id": self.cloudinary_public_id,
            "s3_url": self.s3_url,
            "s3_key": self.s3_key,
            "supabase_url": self.supabase_url,
            "supabase_path": self.supabase_path,
            "category": self.category,
            "subcategory": self.subcategory,
            "category_path": self.category_path,
            "brand": self.brand,
            "manufacturer": self.manufacturer,
            "specifications": self.specifications,
            "features": self.features,
            "rating": self.rating,
            "review_count": self.review_count,
            "source_domain": self.source_domain,
            "match_cluster_id": self.match_cluster_id,
            "match_confidence": self.match_confidence,
            "scraped_at": self.scraped_at.isoformat() if self.scraped_at else None,
            "images": [img.to_dict() for img in self.images] if self.images else [],
            "variants": [var.to_dict() for var in self.variants] if self.variants else [],
            "price_history": [ph.to_dict() for ph in self.price_history] if self.price_history else [],
        }
    
    def to_export_dict(self) -> Dict[str, Any]:
        """Convert to flat dictionary for export."""
        return {
            "Product ID": self.product_id,
            "SKU": self.sku,
            "Name": self.name,
            "Description": self.description,
            "Price": float(self.price) if self.price else "",
            "Original Price": float(self.original_price) if self.original_price else "",
            "Currency": self.currency,
            "Normalized Price": float(self.normalized_price) if self.normalized_price else "",
            "Normalized Currency": self.normalized_currency or "",
            "Exchange Rate": self.exchange_rate or "",
            "In Stock": "Yes" if self.in_stock else "No",
            "Stock Quantity": self.stock_quantity or "",
            "URL": self.url,
            "Image URL": self.image_url,
            "Cloudinary URL": self.cloudinary_url or "",
            "S3 URL": self.s3_url or "",
            "Supabase URL": self.supabase_url or "",
            "Category": self.category,
            "Subcategory": self.subcategory,
            "Category Path": self.category_path,
            "Brand": self.brand,
            "Manufacturer": self.manufacturer,
            "Rating": self.rating,
            "Review Count": self.review_count,
            "Source": self.source_domain,
            "Match Cluster ID": self.match_cluster_id or "",
            "Match Confidence": self.match_confidence or "",
            "Scraped At": self.scraped_at.isoformat() if self.scraped_at else "",
        }


class ProductImage(Base):
    """Model for product images."""
    
    __tablename__ = "product_images"
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), index=True)
    
    url = Column(Text, nullable=False)
    alt_text = Column(String(500), nullable=True)
    position = Column(Integer, default=0)  # Image order
    is_primary = Column(Boolean, default=False)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    
    product = relationship("Product", back_populates="images")
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "url": self.url,
            "alt_text": self.alt_text,
            "position": self.position,
            "is_primary": self.is_primary,
        }


class ProductVariant(Base):
    """Model for product variants (size, color, etc.)."""
    
    __tablename__ = "product_variants"
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), index=True)
    
    variant_id = Column(String(100), nullable=True)
    sku = Column(String(100), nullable=True)
    name = Column(String(255), nullable=False)
    
    # Variant attributes
    attributes = Column(JSON, default=dict)  # {"size": "XL", "color": "Red"}
    
    # Pricing
    price = Column(Numeric(12, 2), nullable=True)
    original_price = Column(Numeric(12, 2), nullable=True)
    
    # Availability
    in_stock = Column(Boolean, default=True)
    stock_quantity = Column(Integer, nullable=True)
    
    # Image
    image_url = Column(Text, nullable=True)
    
    product = relationship("Product", back_populates="variants")
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "variant_id": self.variant_id,
            "sku": self.sku,
            "name": self.name,
            "attributes": self.attributes,
            "price": float(self.price) if self.price else None,
            "in_stock": self.in_stock,
            "stock_quantity": self.stock_quantity,
            "image_url": self.image_url,
        }


class PriceHistory(Base):
    """Model representing historical price points for a product."""
    __tablename__ = "price_history"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), index=True, nullable=False)
    job_id = Column(Integer, ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True)

    price = Column(Numeric(12, 2), nullable=False)
    price_text = Column(String(100), nullable=True)
    currency = Column(String(10), default="USD")
    recorded_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    product = relationship("Product", back_populates="price_history")
    job = relationship("Job")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "product_id": self.product_id,
            "job_id": self.job_id,
            "price": float(self.price) if self.price is not None else None,
            "price_text": self.price_text,
            "currency": self.currency,
            "recorded_at": self.recorded_at.isoformat() if self.recorded_at else None,
        }


class ProductReview(Base):
    """Model representing an extracted customer review for a product."""
    __tablename__ = "product_reviews"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), index=True, nullable=False)

    author = Column(String(255), nullable=True)
    rating = Column(Float, nullable=True)  # e.g. 1.0 to 5.0
    title = Column(String(500), nullable=True)
    content = Column(Text, nullable=False)
    review_date = Column(DateTime(timezone=True), nullable=True)
    verified_purchase = Column(Boolean, default=False)
    helpful_votes = Column(Integer, default=0)

    # Sentiment mining attributes
    sentiment = Column(String(50), default="neutral", index=True)  # positive, neutral, negative
    sentiment_score = Column(Float, nullable=True)  # -1.0 to +1.0
    key_topics = Column(JSON, default=list)  # extracted topics e.g. ["battery life", "fit"]

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    product = relationship("Product", back_populates="reviews")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "product_id": self.product_id,
            "author": self.author,
            "rating": self.rating,
            "title": self.title,
            "content": self.content,
            "review_date": self.review_date.isoformat() if self.review_date else None,
            "verified_purchase": self.verified_purchase,
            "helpful_votes": self.helpful_votes,
            "sentiment": self.sentiment,
            "sentiment_score": self.sentiment_score,
            "key_topics": self.key_topics or [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ProductSentimentSummary(Base):
    """Model representing aggregated AI sentiment intelligence and competitor weakness themes."""
    __tablename__ = "product_sentiment_summaries"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), unique=True, index=True, nullable=False)

    total_reviews_analyzed = Column(Integer, default=0)
    average_rating = Column(Float, nullable=True)
    positive_percentage = Column(Float, default=0.0)
    neutral_percentage = Column(Float, default=0.0)
    negative_percentage = Column(Float, default=0.0)

    # Extracted competitive intelligence
    key_strengths = Column(JSON, default=list)  # e.g. ["Superb sound clarity", "Comfortable memory foam"]
    key_weaknesses = Column(JSON, default=list)  # e.g. ["Battery degrades after 6 months", "Hinge cracks easily"]
    buyer_pain_points = Column(JSON, default=list)  # e.g. ["App disconnects frequently", "Case scratches easily"]
    summary_verdict = Column(Text, nullable=True)  # Executive AI synthesis

    last_analyzed_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    product = relationship("Product", back_populates="sentiment_summary")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "product_id": self.product_id,
            "total_reviews_analyzed": self.total_reviews_analyzed,
            "average_rating": self.average_rating,
            "positive_percentage": self.positive_percentage,
            "neutral_percentage": self.neutral_percentage,
            "negative_percentage": self.negative_percentage,
            "key_strengths": self.key_strengths or [],
            "key_weaknesses": self.key_weaknesses or [],
            "buyer_pain_points": self.buyer_pain_points or [],
            "summary_verdict": self.summary_verdict,
            "last_analyzed_at": self.last_analyzed_at.isoformat() if self.last_analyzed_at else None,
        }


class ProductStockHistory(Base):
    """Model tracking historical stock quantity levels and depletion/restock events over time."""
    __tablename__ = "product_stock_history"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), index=True, nullable=False)

    stock_quantity = Column(Integer, nullable=True)
    in_stock = Column(Boolean, default=True)
    delta = Column(Integer, default=0)
    change_type = Column(String(50), default="initial")  # "depletion", "restock", "out_of_stock", "back_in_stock", "initial"
    recorded_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    product = relationship("Product", back_populates="stock_history")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "product_id": self.product_id,
            "stock_quantity": self.stock_quantity,
            "in_stock": self.in_stock,
            "delta": self.delta,
            "change_type": self.change_type,
            "recorded_at": self.recorded_at.isoformat() if self.recorded_at else None,
        }


class ProductInventoryForecast(Base):
    """Model tracking competitor sales velocity, stockout forecasts, and market opportunity alerts."""
    __tablename__ = "product_inventory_forecasts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), unique=True, index=True, nullable=False)

    current_stock = Column(Integer, nullable=True)
    is_in_stock = Column(Boolean, default=True)
    sales_velocity_per_day = Column(Float, default=0.0)  # Estimated units depleted / day
    estimated_daily_revenue = Column(Float, default=0.0)  # Velocity * unit price
    predicted_stockout_date = Column(DateTime(timezone=True), nullable=True)
    days_until_stockout = Column(Float, nullable=True)
    stockout_risk_level = Column(String(50), default="unknown")  # "high", "medium", "low", "out_of_stock", "unknown"
    total_units_sold = Column(Integer, default=0)
    total_restocks = Column(Integer, default=0)
    last_restock_date = Column(DateTime(timezone=True), nullable=True)
    opportunity_verdict = Column(Text, nullable=True)
    last_calculated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    product = relationship("Product", back_populates="inventory_forecast")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "product_id": self.product_id,
            "current_stock": self.current_stock,
            "is_in_stock": self.is_in_stock,
            "sales_velocity_per_day": round(self.sales_velocity_per_day, 2) if self.sales_velocity_per_day is not None else 0.0,
            "estimated_daily_revenue": round(self.estimated_daily_revenue, 2) if self.estimated_daily_revenue is not None else 0.0,
            "predicted_stockout_date": self.predicted_stockout_date.isoformat() if self.predicted_stockout_date else None,
            "days_until_stockout": round(self.days_until_stockout, 1) if self.days_until_stockout is not None else None,
            "stockout_risk_level": self.stockout_risk_level,
            "total_units_sold": self.total_units_sold or 0,
            "total_restocks": self.total_restocks or 0,
            "last_restock_date": self.last_restock_date.isoformat() if self.last_restock_date else None,
            "opportunity_verdict": self.opportunity_verdict,
            "last_calculated_at": self.last_calculated_at.isoformat() if self.last_calculated_at else None,
        }