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
    original_price = Column(Numeric(12, 2), nullable=True)
    sale_price = Column(Numeric(12, 2), nullable=True)
    currency = Column(String(10), default="GBP")
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
    
    # Job relationship
    job_id = Column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    job = relationship("Job", back_populates="products")
    
    # Related data
    images = relationship("ProductImage", back_populates="product", cascade="all, delete-orphan")
    variants = relationship("ProductVariant", back_populates="product", cascade="all, delete-orphan")
    
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
            "original_price": float(self.original_price) if self.original_price else None,
            "sale_price": float(self.sale_price) if self.sale_price else None,
            "currency": self.currency,
            "in_stock": self.in_stock,
            "stock_quantity": self.stock_quantity,
            "url": self.url,
            "image_url": self.image_url,
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
            "scraped_at": self.scraped_at.isoformat() if self.scraped_at else None,
            "images": [img.to_dict() for img in self.images] if self.images else [],
            "variants": [var.to_dict() for var in self.variants] if self.variants else [],
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
            "In Stock": "Yes" if self.in_stock else "No",
            "Stock Quantity": self.stock_quantity or "",
            "URL": self.url,
            "Image URL": self.image_url,
            "Category": self.category,
            "Subcategory": self.subcategory,
            "Category Path": self.category_path,
            "Brand": self.brand,
            "Manufacturer": self.manufacturer,
            "Rating": self.rating,
            "Review Count": self.review_count,
            "Source": self.source_domain,
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