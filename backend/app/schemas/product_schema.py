"""
Pydantic schemas for product-related operations.
"""

from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class ProductImageSchema(BaseModel):
    """Schema for product image."""
    
    id: int
    url: str
    alt_text: Optional[str]
    position: int
    is_primary: bool
    
    class Config:
        from_attributes = True


class ProductVariantSchema(BaseModel):
    """Schema for product variant."""
    
    id: int
    variant_id: Optional[str]
    sku: Optional[str]
    name: str
    attributes: Dict[str, Any]
    price: Optional[float]
    in_stock: bool
    stock_quantity: Optional[int]
    image_url: Optional[str]
    
    class Config:
        from_attributes = True


class ProductBase(BaseModel):
    """Base product schema."""
    
    name: str
    description: Optional[str] = None
    price: Optional[float] = None
    currency: str = "GBP"
    url: str
    image_url: Optional[str] = None
    category: Optional[str] = None
    brand: Optional[str] = None


class ProductCreate(ProductBase):
    """Schema for creating a product."""
    
    product_id: Optional[str] = None
    sku: Optional[str] = None
    original_price: Optional[float] = None
    sale_price: Optional[float] = None
    in_stock: bool = True
    stock_quantity: Optional[int] = None
    subcategory: Optional[str] = None
    category_path: Optional[str] = None
    manufacturer: Optional[str] = None
    specifications: Optional[Dict[str, Any]] = None
    features: Optional[List[str]] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None
    source_domain: str
    job_id: int
    raw_data: Optional[Dict[str, Any]] = None


class ProductResponse(BaseModel):
    """Schema for product response."""
    
    id: int
    product_id: Optional[str]
    sku: Optional[str]
    name: str
    description: Optional[str]
    price: Optional[float]
    original_price: Optional[float]
    sale_price: Optional[float]
    currency: str
    in_stock: bool
    stock_quantity: Optional[int]
    url: str
    image_url: Optional[str]
    category: Optional[str]
    subcategory: Optional[str]
    category_path: Optional[str]
    brand: Optional[str]
    manufacturer: Optional[str]
    specifications: Optional[Dict[str, Any]]
    features: Optional[List[str]]
    rating: Optional[float]
    review_count: Optional[int]
    source_domain: str
    scraped_at: datetime
    images: List[ProductImageSchema] = []
    variants: List[ProductVariantSchema] = []
    
    class Config:
        from_attributes = True


class ProductListResponse(BaseModel):
    """Schema for paginated product list response."""
    
    products: List[ProductResponse]
    total: int
    page: int
    page_size: int
    pages: int


class ProductFilter(BaseModel):
    """Schema for filtering products."""
    
    job_id: Optional[int] = None
    domain: Optional[str] = None
    category: Optional[str] = None
    brand: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    in_stock: Optional[bool] = None
    search: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "domain": "leelicycles.co.uk",
                "category": "Bikes",
                "min_price": 100,
                "max_price": 500,
                "in_stock": True
            }
        }


class ProductStatistics(BaseModel):
    """Schema for product statistics."""
    
    total_products: int
    unique_categories: int
    unique_brands: int
    average_price: Optional[float]
    min_price: Optional[float]
    max_price: Optional[float]
    in_stock_count: int
    out_of_stock_count: int
    with_images_count: int
    with_variants_count: int