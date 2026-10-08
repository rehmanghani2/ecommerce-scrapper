"""
API Routes for AI-Powered Product Catalog Categorization & Taxonomy Auto-Mapping.
Provides endpoints for standard taxonomy trees, auto-categorization batch runs,
single-product AI classification, review verification, and mapping rules management.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
import logging

from app.models.database import get_db
from app.models.product import Product
from app.models.taxonomy import (
    TaxonomyStandard, TaxonomyNode, CategoryMappingRule, ProductTaxonomyMapping
)
from app.services.taxonomy_service import taxonomy_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/taxonomy", tags=["Catalog Categorization & Taxonomy Auto-Mapper"])


class AutoCategorizeRequest(BaseModel):
    taxonomy_id: int
    product_ids: Optional[List[int]] = None
    source_domain: Optional[str] = None
    overwrite_existing: bool = False
    gemini_api_key: Optional[str] = None
    limit: int = 100


class ClassifySingleRequest(BaseModel):
    product_id: int
    taxonomy_id: int
    gemini_api_key: Optional[str] = None


class VerifyMappingRequest(BaseModel):
    product_id: int
    taxonomy_id: int
    category_path: Optional[str] = None
    is_verified: bool = True


class MappingRuleCreateRequest(BaseModel):
    source_domain: Optional[str] = None
    source_category_path: str
    target_taxonomy_id: int
    target_node_id: Optional[int] = None
    target_category_path: str
    confidence: float = 1.0
    match_method: str = "manual"
    is_active: bool = True


@router.get("/standards")
async def list_taxonomy_standards(db: AsyncSession = Depends(get_db)):
    """List supported standard taxonomy systems (Google, Amazon, Shopify, etc.)."""
    return await taxonomy_service.get_taxonomies(db)


@router.get("/standards/{taxonomy_id}/tree")
async def get_taxonomy_tree(taxonomy_id: int, db: AsyncSession = Depends(get_db)):
    """Get the full hierarchical node tree for a taxonomy standard."""
    return await taxonomy_service.get_taxonomy_tree(taxonomy_id, db)


@router.get("/summary/{taxonomy_id}")
async def get_taxonomy_summary(taxonomy_id: int, db: AsyncSession = Depends(get_db)):
    """Get mapping coverage statistics, confidence breakdown, and top categories."""
    return await taxonomy_service.get_catalog_taxonomy_summary(db, taxonomy_id)


@router.post("/auto-categorize")
async def auto_categorize_catalog(
    request: AutoCategorizeRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Trigger batch automated categorization of catalog products into target taxonomy.
    """
    res = await taxonomy_service.auto_categorize_catalog(
        db=db,
        taxonomy_id=request.taxonomy_id,
        product_ids=request.product_ids,
        source_domain=request.source_domain,
        overwrite_existing=request.overwrite_existing,
        gemini_api_key=request.gemini_api_key,
        limit=request.limit
    )
    return res


@router.post("/classify-product")
async def classify_single_product(
    request: ClassifySingleRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Analyze and predict the taxonomy category for a single product with Gemini AI reasoning.
    """
    product = await db.get(Product, request.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    nodes = (await db.execute(
        select(TaxonomyNode).where(TaxonomyNode.standard_id == request.taxonomy_id)
    )).scalars().all()

    rules = (await db.execute(
        select(CategoryMappingRule).where(
            CategoryMappingRule.target_taxonomy_id == request.taxonomy_id,
            CategoryMappingRule.is_active == True
        )
    )).scalars().all()

    classification = await taxonomy_service.classify_product(
        product=product,
        taxonomy_id=request.taxonomy_id,
        nodes=nodes,
        rules=rules,
        gemini_api_key=request.gemini_api_key,
        allow_gemini_fallback=True
    )
    return classification


@router.post("/verify")
async def verify_product_mapping(
    request: VerifyMappingRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Verify or manually override the taxonomy mapping for a product.
    """
    result = await taxonomy_service.verify_mapping(
        db=db,
        product_id=request.product_id,
        taxonomy_id=request.taxonomy_id,
        category_path=request.category_path,
        is_verified=request.is_verified
    )
    if not result:
        raise HTTPException(status_code=400, detail="Failed to verify mapping")
    return {"success": True, "mapping": result}


@router.get("/mappings")
async def list_product_mappings(
    taxonomy_id: Optional[int] = Query(None),
    is_verified: Optional[bool] = Query(None),
    min_confidence: Optional[float] = Query(None),
    max_confidence: Optional[float] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    List mapped products with pagination and confidence filtering.
    """
    q = select(ProductTaxonomyMapping, Product).join(Product, Product.id == ProductTaxonomyMapping.product_id)
    count_q = select(func.count(ProductTaxonomyMapping.id))

    if taxonomy_id:
        q = q.where(ProductTaxonomyMapping.taxonomy_id == taxonomy_id)
        count_q = count_q.where(ProductTaxonomyMapping.taxonomy_id == taxonomy_id)

    if is_verified is not None:
        q = q.where(ProductTaxonomyMapping.is_verified == is_verified)
        count_q = count_q.where(ProductTaxonomyMapping.is_verified == is_verified)

    if min_confidence is not None:
        q = q.where(ProductTaxonomyMapping.confidence >= min_confidence)
        count_q = count_q.where(ProductTaxonomyMapping.confidence >= min_confidence)

    if max_confidence is not None:
        q = q.where(ProductTaxonomyMapping.confidence <= max_confidence)
        count_q = count_q.where(ProductTaxonomyMapping.confidence <= max_confidence)

    total = (await db.execute(count_q)).scalar() or 0

    offset = (page - 1) * page_size
    q = q.order_by(ProductTaxonomyMapping.confidence.asc(), ProductTaxonomyMapping.id.desc()).offset(offset).limit(page_size)

    rows = (await db.execute(q)).all()

    items = []
    for mapping, prod in rows:
        m_dict = mapping.to_dict()
        m_dict["product"] = {
            "id": prod.id,
            "name": prod.name,
            "brand": prod.brand,
            "price": float(prod.price) if prod.price else None,
            "currency": prod.currency,
            "image_url": prod.image_url,
            "source_domain": prod.source_domain,
            "original_category": prod.category_path or prod.category,
        }
        items.append(m_dict)

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size if total > 0 else 0
    }


@router.get("/rules")
async def list_mapping_rules(
    taxonomy_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """List category mapping rules."""
    return await taxonomy_service.get_mapping_rules(db, taxonomy_id)


@router.post("/rules")
async def create_mapping_rule(
    request: MappingRuleCreateRequest,
    db: AsyncSession = Depends(get_db)
):
    """Create a new category mapping rule."""
    return await taxonomy_service.create_mapping_rule(db, request.model_dump())


@router.delete("/rules/{rule_id}")
async def delete_mapping_rule(
    rule_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete a category mapping rule."""
    success = await taxonomy_service.delete_mapping_rule(db, rule_id)
    if not success:
        raise HTTPException(status_code=404, detail="Mapping rule not found")
    return {"success": True}
