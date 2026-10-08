"""
Products API routes.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, distinct
from typing import Optional, List
import logging

from app.models.database import get_db
from app.models.product import Product, PriceHistory
from app.schemas.product_schema import (
    ProductResponse, ProductListResponse, ProductStatistics, PriceHistorySchema
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", response_model=ProductListResponse)
@router.get("/", response_model=ProductListResponse)
async def list_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    brand: Optional[str] = Query(None),
    min_price: Optional[float] = Query(None),
    max_price: Optional[float] = Query(None),
    in_stock: Optional[bool] = Query(None),
    is_price_drop: Optional[bool] = Query(None),
    domain: Optional[str] = Query(None),
    job_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """
    List all products with filtering and pagination.
    """
    # Build query
    from sqlalchemy.orm import selectinload
    query = select(Product).options(
        selectinload(Product.images),
        selectinload(Product.variants),
        selectinload(Product.price_history)
    ).order_by(desc(Product.scraped_at))
    count_query = select(func.count(Product.id))
    
    # Apply filters
    if is_price_drop is True:
        query = query.where(Product.price_change < 0)
        count_query = count_query.where(Product.price_change < 0)
    
    # Apply filters
    if search:
        query = query.where(Product.name.ilike(f"%{search}%") | Product.description.ilike(f"%{search}%"))
        count_query = count_query.where(Product.name.ilike(f"%{search}%") | Product.description.ilike(f"%{search}%"))
    
    if category:
        query = query.where(Product.category == category)
        count_query = count_query.where(Product.category == category)
        
    if brand:
        query = query.where(Product.brand == brand)
        count_query = count_query.where(Product.brand == brand)
        
    if min_price is not None:
        query = query.where(Product.price >= min_price)
        count_query = count_query.where(Product.price >= min_price)
        
    if max_price is not None:
        query = query.where(Product.price <= max_price)
        count_query = count_query.where(Product.price <= max_price)
        
    if in_stock is not None:
        query = query.where(Product.in_stock == in_stock)
        count_query = count_query.where(Product.in_stock == in_stock)
        
    if domain:
        query = query.where(Product.source_domain == domain)
        count_query = count_query.where(Product.source_domain == domain)
        
    if job_id:
        query = query.where(Product.job_id == job_id)
        count_query = count_query.where(Product.job_id == job_id)
    
    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    
    # Execute query
    result = await db.execute(query)
    products = result.scalars().all()
    
    # Calculate pages
    pages = (total + page_size - 1) // page_size
    
    return ProductListResponse(
        products=[ProductResponse.model_validate(p) for p in products],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages
    )


@router.get("/filter-options")
async def get_filter_options(
    domain: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Get available filter options (categories, brands, domains).
    """
    # Categories
    cat_query = select(distinct(Product.category)).where(Product.category.isnot(None))
    if domain:
        cat_query = cat_query.where(Product.source_domain == domain)
    
    # Brands
    brand_query = select(distinct(Product.brand)).where(Product.brand.isnot(None))
    if domain:
        brand_query = brand_query.where(Product.source_domain == domain)
        
    # Domains
    domain_query = select(distinct(Product.source_domain))
    
    cat_result = await db.execute(cat_query)
    brand_result = await db.execute(brand_query)
    domain_result = await db.execute(domain_query)
    
    return {
        "categories": [r for r in cat_result.scalars().all() if r],
        "brands": [r for r in brand_result.scalars().all() if r],
        "domains": [r for r in domain_result.scalars().all() if r]
    }


@router.get("/statistics", response_model=ProductStatistics)
async def get_product_statistics(
    domain: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Get statistics for products.
    """
    query_base = select(Product)
    if domain:
        query_base = query_base.where(Product.source_domain == domain)
        
    # Total products
    total_query = select(func.count(Product.id))
    if domain:
        total_query = total_query.where(Product.source_domain == domain)
    
    # Unique cats & brands
    cat_query = select(func.count(distinct(Product.category)))
    brand_query = select(func.count(distinct(Product.brand)))
    if domain:
        cat_query = cat_query.where(Product.source_domain == domain)
        brand_query = brand_query.where(Product.source_domain == domain)
        
    # Price stats
    price_query = select(
        func.avg(Product.price).label('avg'),
        func.min(Product.price).label('min'),
        func.max(Product.price).label('max')
    )
    if domain:
        price_query = price_query.where(Product.source_domain == domain)
        
    # Stock stats
    stock_query = select(
        func.count(Product.id)
    ).where(Product.in_stock == True)
    if domain:
        stock_query = stock_query.where(Product.source_domain == domain)
        
    # Execute all
    total = (await db.execute(total_query)).scalar() or 0
    cats = (await db.execute(cat_query)).scalar() or 0
    brands = (await db.execute(brand_query)).scalar() or 0
    prices = (await db.execute(price_query)).first()
    stock_count = (await db.execute(stock_query)).scalar() or 0
    
    # Count with images
    image_query = select(func.count(Product.id)).where(Product.image_url.isnot(None))
    if domain:
        image_query = image_query.where(Product.source_domain == domain)
    image_count = (await db.execute(image_query)).scalar() or 0
    
    # Count with variants
    from app.models.product import ProductVariant
    variant_query = select(func.count(distinct(ProductVariant.product_id)))
    if domain:
        variant_query = variant_query.join(Product, Product.id == ProductVariant.product_id).where(Product.source_domain == domain)
    variant_count = (await db.execute(variant_query)).scalar() or 0

    return ProductStatistics(
        total_products=total,
        unique_categories=cats,
        unique_brands=brands,
        average_price=float(prices.avg) if prices.avg else 0,
        min_price=float(prices.min) if prices.min else 0,
        max_price=float(prices.max) if prices.max else 0,
        in_stock_count=stock_count,
        out_of_stock_count=total - stock_count,
        with_images_count=image_count,
        with_variants_count=variant_count,
    )


@router.get("/price-drops", response_model=ProductListResponse)
async def get_price_drops(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all products that have experienced a price drop, ordered by discount percentage.
    """
    from sqlalchemy.orm import selectinload
    query = (
        select(Product)
        .options(
            selectinload(Product.images),
            selectinload(Product.variants),
            selectinload(Product.price_history)
        )
        .where(Product.price_change < 0)
        .order_by(Product.price_change_percentage.asc())
    )
    count_query = select(func.count(Product.id)).where(Product.price_change < 0)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    offset = (page - 1) * page_size
    result = await db.execute(query.offset(offset).limit(page_size))
    products = result.scalars().all()

    pages = (total + page_size - 1) // page_size if total > 0 else 0
    return ProductListResponse(
        products=[ProductResponse.model_validate(p) for p in products],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages
    )


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(product_id: int, db: AsyncSession = Depends(get_db)):
    """
    Get details for a specific product including its full price history.
    """
    from sqlalchemy.orm import selectinload
    query = (
        select(Product)
        .options(
            selectinload(Product.images),
            selectinload(Product.variants),
            selectinload(Product.price_history)
        )
        .where(Product.id == product_id)
    )
    result = await db.execute(query)
    product = result.scalar_one_or_none()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    return ProductResponse.model_validate(product)


@router.get("/{product_id}/history", response_model=List[PriceHistorySchema])
async def get_product_price_history(product_id: int, db: AsyncSession = Depends(get_db)):
    """
    Get chronological price history snapshots for a product.
    """
    query = (
        select(PriceHistory)
        .where(PriceHistory.product_id == product_id)
        .order_by(PriceHistory.recorded_at.asc())
    )
    result = await db.execute(query)
    history = result.scalars().all()
    return [PriceHistorySchema.model_validate(h) for h in history]
