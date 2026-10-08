"""
Unit and integration tests for AI-Powered Product Catalog Categorization & Taxonomy Auto-Mapper.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from app.models.database import Base, get_db
from app.models.taxonomy import (
    TaxonomyStandard, TaxonomyNode, CategoryMappingRule, ProductTaxonomyMapping
)
from app.models.product import Product
from app.services.taxonomy_service import TaxonomyService, taxonomy_service
from app.main import app

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def async_db():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def client(async_db):
    async def override_get_db():
        yield async_db

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


def test_normalize_breadcrumb():
    """Verify messy breadcrumbs and e-commerce separators are cleaned and normalized."""
    raw1 = "Home / Electronics // Audio & Video -> Headphones"
    normalized1 = TaxonomyService.normalize_breadcrumb(raw1)
    assert normalized1 == "Electronics > Audio & Video > Headphones"

    raw2 = "Shop > Catalog > Sporting Goods > Cycling"
    normalized2 = TaxonomyService.normalize_breadcrumb(raw2)
    assert normalized2 == "Sporting Goods > Cycling"


@pytest.mark.asyncio
async def test_ensure_default_taxonomies_and_trees(async_db: AsyncSession):
    """Verify standard taxonomy trees (Google, Amazon, Shopify) seed with hierarchical nodes."""
    await taxonomy_service.ensure_default_taxonomies(async_db)

    standards = (await async_db.execute(select(TaxonomyStandard))).scalars().all()
    assert len(standards) >= 3

    names = {s.name for s in standards}
    assert "google_shopping" in names
    assert "amazon" in names
    assert "shopify" in names

    # Check nodes under google_shopping
    google_std = next(s for s in standards if s.name == "google_shopping")
    nodes = (await async_db.execute(
        select(TaxonomyNode).where(TaxonomyNode.standard_id == google_std.id)
    )).scalars().all()
    assert len(nodes) >= 15
    paths = {n.full_path for n in nodes}
    assert "Electronics > Audio > Headphones" in paths


@pytest.mark.asyncio
async def test_classify_product_via_mapping_rules(async_db: AsyncSession):
    """Verify rule-based category matching takes priority with high confidence."""
    await taxonomy_service.ensure_default_taxonomies(async_db)
    google_std = (await async_db.execute(
        select(TaxonomyStandard).where(TaxonomyStandard.name == "google_shopping")
    )).scalar_one()

    # Create mapping rule
    rule = CategoryMappingRule(
        source_domain="walmart.com",
        source_category_path="Personal Audio / Over-Ear Cans",
        target_taxonomy_id=google_std.id,
        target_category_path="Electronics > Audio > Headphones",
        confidence=0.99,
        match_method="exact_rule"
    )
    async_db.add(rule)
    await async_db.commit()

    product = Product(
        name="Sony WH-1000XM5 Wireless Headphones",
        source_domain="walmart.com",
        category="Personal Audio / Over-Ear Cans",
        category_path="Personal Audio / Over-Ear Cans",
        url="https://walmart.com/item/1"
    )

    nodes = (await async_db.execute(
        select(TaxonomyNode).where(TaxonomyNode.standard_id == google_std.id)
    )).scalars().all()
    rules = [rule]

    result = await taxonomy_service.classify_product(
        product=product,
        taxonomy_id=google_std.id,
        nodes=nodes,
        rules=rules,
        allow_gemini_fallback=False
    )

    assert result["category_path"] == "Electronics > Audio > Headphones"
    assert result["confidence"] >= 0.99
    assert "rule_match" in result["match_method"]


@pytest.mark.asyncio
async def test_classify_product_via_token_fuzzy(async_db: AsyncSession):
    """Verify token Jaccard and title keyword matching detects correct category."""
    await taxonomy_service.ensure_default_taxonomies(async_db)
    google_std = (await async_db.execute(
        select(TaxonomyStandard).where(TaxonomyStandard.name == "google_shopping")
    )).scalar_one()

    nodes = (await async_db.execute(
        select(TaxonomyNode).where(TaxonomyNode.standard_id == google_std.id)
    )).scalars().all()

    product = Product(
        name="Apple MacBook Pro 16 M3 Max Laptop",
        source_domain="bestbuy.com",
        category="Computers",
        category_path="Computers > Laptops",
        url="https://bestbuy.com/macbook"
    )

    result = await taxonomy_service.classify_product(
        product=product,
        taxonomy_id=google_std.id,
        nodes=nodes,
        rules=[],
        allow_gemini_fallback=False
    )

    assert result["category_path"] == "Electronics > Computers > Laptops"
    assert result["confidence"] > 0.70


@pytest.mark.asyncio
async def test_auto_categorize_catalog_batch(async_db: AsyncSession):
    """Test batch auto-categorization runner persisting to ProductTaxonomyMapping."""
    await taxonomy_service.ensure_default_taxonomies(async_db)
    google_std = (await async_db.execute(
        select(TaxonomyStandard).where(TaxonomyStandard.name == "google_shopping")
    )).scalar_one()

    # Create test product
    p1 = Product(
        name="Samsung 65-Inch OLED 4K Smart TV",
        source_domain="target.com",
        category="Television",
        url="https://target.com/tv1"
    )
    p2 = Product(
        name="Men Cotton Casual T-Shirt",
        source_domain="target.com",
        category="Apparel > Shirts",
        url="https://target.com/shirt1"
    )
    async_db.add_all([p1, p2])
    await async_db.commit()
    await async_db.refresh(p1)
    await async_db.refresh(p2)

    res = await taxonomy_service.auto_categorize_catalog(
        db=async_db,
        taxonomy_id=google_std.id,
        product_ids=[p1.id, p2.id]
    )

    assert res["success"] is True
    assert res["classified_count"] == 2

    # Verify database mappings
    mappings = (await async_db.execute(
        select(ProductTaxonomyMapping).where(ProductTaxonomyMapping.taxonomy_id == google_std.id)
    )).scalars().all()
    assert len(mappings) == 2


@pytest.mark.asyncio
async def test_manual_verification_and_override(async_db: AsyncSession):
    """Verify manual override and user approval flow."""
    await taxonomy_service.ensure_default_taxonomies(async_db)
    google_std = (await async_db.execute(
        select(TaxonomyStandard).where(TaxonomyStandard.name == "google_shopping")
    )).scalar_one()

    p = Product(
        name="Generic Gadget Item",
        source_domain="generic.com",
        url="https://generic.com/item"
    )
    async_db.add(p)
    await async_db.commit()
    await async_db.refresh(p)

    # Approve with override
    verified = await taxonomy_service.verify_mapping(
        db=async_db,
        product_id=p.id,
        taxonomy_id=google_std.id,
        category_path="Electronics > Communications > Smartphones",
        is_verified=True
    )

    assert verified["category_path"] == "Electronics > Communications > Smartphones"
    assert verified["is_verified"] is True
    assert verified["match_method"] == "manual_override"
    assert verified["confidence"] == 1.0


@pytest.mark.asyncio
async def test_taxonomy_api_routes(client: AsyncClient, async_db: AsyncSession):
    """Verify FastAPI routes for taxonomy standards, summary, and rules."""
    # List standards
    res = await client.get("/api/v1/taxonomy/standards")
    assert res.status_code == 200
    standards = res.json()
    assert len(standards) >= 3

    google_id = next(s["id"] for s in standards if s["name"] == "google_shopping")

    # Get summary
    res_summary = await client.get(f"/api/v1/taxonomy/summary/{google_id}")
    assert res_summary.status_code == 200
    summary = res_summary.json()
    assert "coverage_percentage" in summary

    # Create mapping rule
    rule_payload = {
        "source_category_path": "Audio > Cans",
        "target_taxonomy_id": google_id,
        "target_category_path": "Electronics > Audio > Headphones",
        "confidence": 0.95,
        "match_method": "manual"
    }
    res_rule = await client.post("/api/v1/taxonomy/rules", json=rule_payload)
    assert res_rule.status_code == 200
    rule_obj = res_rule.json()
    assert rule_obj["id"] is not None

    # List rules
    res_rules = await client.get(f"/api/v1/taxonomy/rules?taxonomy_id={google_id}")
    assert res_rules.status_code == 200
    assert len(res_rules.json()) >= 1
