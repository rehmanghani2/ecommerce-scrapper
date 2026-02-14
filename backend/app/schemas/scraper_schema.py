"""
Pydantic schemas for scraper configuration and requests.
"""

from pydantic import BaseModel, Field, HttpUrl, validator
from typing import Optional, Dict, Any, List
from enum import Enum


class ScraperType(str, Enum):
    """Types of scrapers available."""
    AUTO = "auto"
    GENERIC = "generic"
    SHOPIFY = "shopify"
    WOOCOMMERCE = "woocommerce"
    MAGENTO = "magento"
    CUSTOM = "custom"


class PaginationType(str, Enum):
    """Types of pagination handling."""
    AUTO = "auto"
    CLICK = "click"
    SCROLL = "scroll"
    URL_PARAM = "url_param"
    NEXT_BUTTON = "next_button"
    NONE = "none"


class SelectorConfig(BaseModel):
    """Configuration for CSS/XPath selectors."""
    
    # Product list page selectors
    product_container: Optional[str] = None
    product_card: Optional[str] = None
    product_link: Optional[str] = None
    product_name: Optional[str] = None
    product_price: Optional[str] = None
    product_image: Optional[str] = None
    
    # Product detail page selectors
    detail_name: Optional[str] = None
    detail_price: Optional[str] = None
    detail_description: Optional[str] = None
    detail_images: Optional[str] = None
    detail_sku: Optional[str] = None
    detail_brand: Optional[str] = None
    detail_category: Optional[str] = None
    detail_specifications: Optional[str] = None
    detail_availability: Optional[str] = None
    
    # Navigation selectors
    category_links: Optional[str] = None
    subcategory_links: Optional[str] = None
    pagination_next: Optional[str] = None
    pagination_pages: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "product_card": ".product-item",
                "product_link": ".product-item a",
                "product_name": ".product-title",
                "product_price": ".price",
                "pagination_next": ".next-page"
            }
        }


class PaginationConfig(BaseModel):
    """Configuration for pagination handling."""
    
    type: PaginationType = PaginationType.AUTO
    max_pages: int = Field(default=100, ge=1, le=10000)
    wait_after_page: int = Field(default=2000, ge=0, le=30000)  # ms
    
    # For URL parameter pagination
    page_param: Optional[str] = "page"
    start_page: int = 1
    
    # For click pagination
    next_button_selector: Optional[str] = None
    load_more_selector: Optional[str] = None
    
    # For infinite scroll
    scroll_delay: int = Field(default=1000, ge=100, le=10000)  # ms
    max_scroll_attempts: int = Field(default=50, ge=1, le=500)


class ScraperConfig(BaseModel):
    """Complete scraper configuration."""
    
    # Basic settings
    scraper_type: ScraperType = ScraperType.AUTO
    follow_product_links: bool = True
    include_images: bool = True
    include_variants: bool = True
    include_specifications: bool = True
    
    # Crawling settings
    max_depth: int = Field(default=5, ge=1, le=20)
    max_pages: int = Field(default=100, ge=1, le=10000)
    max_products: int = Field(default=10000, ge=1, le=100000)
    
    # Performance settings
    concurrent_requests: int = Field(default=3, ge=1, le=10)
    request_delay: int = Field(default=1000, ge=0, le=30000)  # ms
    timeout: int = Field(default=30000, ge=5000, le=120000)  # ms
    
    # Selectors (optional - will auto-detect if not provided)
    selectors: Optional[SelectorConfig] = None
    
    # Pagination
    pagination: Optional[PaginationConfig] = None
    
    # Filters
    url_patterns: Optional[List[str]] = None  # Include only matching URLs
    exclude_patterns: Optional[List[str]] = None  # Exclude matching URLs
    category_filter: Optional[List[str]] = None  # Only scrape specific categories
    
    # Advanced
    javascript_rendering: bool = True
    wait_for_selector: Optional[str] = None
    custom_headers: Optional[Dict[str, str]] = None
    cookies: Optional[List[Dict[str, Any]]] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "scraper_type": "auto",
                "max_pages": 50,
                "max_products": 1000,
                "follow_product_links": True,
                "include_images": True
            }
        }


class ScraperRequest(BaseModel):
    """Request to start a new scraping job."""
    
    url: HttpUrl
    name: Optional[str] = None
    description: Optional[str] = None
    config: Optional[ScraperConfig] = None
    
    @validator("name", pre=True, always=True)
    def set_default_name(cls, v, values):
        if v is None and "url" in values:
            from urllib.parse import urlparse
            parsed = urlparse(str(values["url"]))
            return f"Scrape {parsed.netloc}"
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://leelicycles.co.uk/",
                "name": "Lee Cycles Full Scrape",
                "config": {
                    "max_pages": 100,
                    "max_products": 5000
                }
            }
        }


class ScraperResponse(BaseModel):
    """Response after starting a scraping job."""
    
    success: bool
    message: str
    job_id: Optional[str] = None
    status: Optional[str] = None


class ScraperPreviewRequest(BaseModel):
    """Request to preview selectors and test scraping."""
    
    url: HttpUrl
    selectors: Optional[SelectorConfig] = None
    sample_size: int = Field(default=5, ge=1, le=20)


class DetectedSelectors(BaseModel):
    """Auto-detected selectors for a website."""
    
    confidence: float  # 0-1 confidence score
    platform: Optional[str] = None  # Detected platform (Shopify, WooCommerce, etc.)
    selectors: SelectorConfig
    sample_products: List[Dict[str, Any]] = []