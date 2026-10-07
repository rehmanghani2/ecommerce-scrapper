"""
Unit tests for Competitor Promotion, Coupon, and Bundle Tracker.
"""
import pytest
from app.services.promotion_service import promotion_service
from app.models.promotion import ProductPromotion
from app.models.product import Product


def test_calculate_effective_price_percentage():
    # 20% off $100.00 -> $80.00 net, $20.00 savings
    res = promotion_service.calculate_effective_price(
        original_price=100.0,
        discount_type="percentage",
        discount_value=20.0,
    )
    assert res["effective_price"] == 80.0
    assert res["savings_amount"] == 20.0
    assert res["discount_percentage"] == 20.0


def test_calculate_effective_price_fixed_amount():
    # $15.50 off $60.00 -> $44.50 net, $15.50 savings
    res = promotion_service.calculate_effective_price(
        original_price=60.0,
        discount_type="fixed_amount",
        discount_value=15.5,
    )
    assert res["effective_price"] == 44.5
    assert res["savings_amount"] == 15.5
    assert res["discount_percentage"] == 25.8


def test_calculate_effective_price_bogo_free():
    # Buy 1 Get 1 Free for $50 item: total cost = $50 for 2 items -> $25.00 effective unit price
    res = promotion_service.calculate_effective_price(
        original_price=50.0,
        discount_type="bogo",
        bogo_buy_qty=1,
        bogo_get_qty=1,
        bogo_discount_pct=100.0,
    )
    assert res["effective_price"] == 25.0
    assert res["savings_amount"] == 25.0
    assert res["discount_percentage"] == 50.0


def test_calculate_effective_price_bogo_half_off():
    # Buy 1 Get 1 50% Off for $100 item: item 1 is $100, item 2 is $50. Total = $150 / 2 = $75.00
    res = promotion_service.calculate_effective_price(
        original_price=100.0,
        discount_type="bogo",
        bogo_buy_qty=1,
        bogo_get_qty=1,
        bogo_discount_pct=50.0,
    )
    assert res["effective_price"] == 75.0
    assert res["savings_amount"] == 25.0
    assert res["discount_percentage"] == 25.0


def test_calculate_effective_price_volume_tier():
    # Volume tier 15% off for $200 item
    res = promotion_service.calculate_effective_price(
        original_price=200.0,
        discount_type="volume_tier",
        discount_value=15.0,
        volume_min_qty=3,
    )
    assert res["effective_price"] == 170.0
    assert res["savings_amount"] == 30.0
    assert res["discount_percentage"] == 15.0


def test_detect_promotions_from_text():
    # Test coupon code regex extraction
    sample_text = "Special Deal: Use code SAVE25 to get 25% off your order! Or clip $10.00 coupon at checkout."
    detected = promotion_service.detect_promotions_from_text(sample_text, original_price=100.0)

    assert len(detected) >= 2
    types = [d["promo_type"] for d in detected]
    assert "coupon_code" in types
    assert "fixed_amount_discount" in types

    code_deal = next(d for d in detected if d["promo_type"] == "coupon_code")
    assert code_deal["coupon_code"] == "SAVE25"
    assert code_deal["discount_value"] == 25.0
    assert code_deal["effective_price"] == 75.0

    clip_deal = next(d for d in detected if d["promo_type"] == "fixed_amount_discount")
    assert clip_deal["discount_value"] == 10.0
    assert clip_deal["effective_price"] == 90.0


def test_detect_bogo_and_volume_tier():
    sample_bogo = "Limited time offer: Buy 2 get 1 free on all shoes! Buy 3 or more save 20%."
    detected = promotion_service.detect_promotions_from_text(sample_bogo, original_price=60.0)

    types = [d["promo_type"] for d in detected]
    assert "bogo" in types
    assert "volume_tier" in types

    bogo = next(d for d in detected if d["promo_type"] == "bogo")
    assert bogo["bogo_buy_qty"] == 2
    assert bogo["bogo_get_qty"] == 1


import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.models.database import Base, get_db
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


@pytest.mark.asyncio
async def test_promotion_service_db_crud(async_db):
    # Create product
    prod = Product(
        name="Wireless Noise Cancelling Headphones",
        price=150.0,
        url="https://competitor.com/headphones",
        source_domain="competitor.com",
    )
    async_db.add(prod)
    await async_db.commit()
    await async_db.refresh(prod)

    # Add promotion
    promo = await promotion_service.add_or_update_promotion(
        db=async_db,
        product_id=prod.id,
        promo_data={
            "promo_type": "coupon_code",
            "title": "Summer Savings Code",
            "coupon_code": "SUMMER15",
            "discount_type": "percentage",
            "discount_value": 15.0,
            "banner_text": "Save 15% with SUMMER15",
        }
    )

    assert promo.id is not None
    assert promo.coupon_code == "SUMMER15"
    assert promo.effective_price == 127.5
    assert promo.savings_amount == 22.5
    assert promo.is_active is True

    # Retrieve promotions for product
    promos = await promotion_service.get_promotions_for_product(async_db, prod.id)
    assert len(promos) == 1
    assert promos[0]["coupon_code"] == "SUMMER15"

    # Catalog active query
    catalog = await promotion_service.get_active_promotions_catalog(async_db, domain="competitor.com")
    assert catalog["total"] == 1
    assert catalog["items"][0]["product_name"] == "Wireless Noise Cancelling Headphones"

    # Insights query
    insights = await promotion_service.get_promotional_insights(async_db)
    assert insights["total_active_promotions"] == 1
    assert insights["average_savings_amount"] == 22.5
    assert "coupon_code" in insights["promo_types_breakdown"]

    # Toggle promotion
    updated = await promotion_service.toggle_promotion(async_db, promo.id)
    assert updated["is_active"] is False

    # Delete promotion
    deleted = await promotion_service.delete_promotion(async_db, promo.id)
    assert deleted is True
    promos_after = await promotion_service.get_promotions_for_product(async_db, prod.id)
    assert len(promos_after) == 0


@pytest.mark.asyncio
async def test_promotions_api_routes(client, async_db):
    # Create product
    prod = Product(
        name="Ultra 4K Smart OLED TV",
        price=1000.0,
        url="https://electronics-store.com/tv",
        source_domain="electronics-store.com",
    )
    async_db.add(prod)
    await async_db.commit()
    await async_db.refresh(prod)

    # 1. POST /api/v1/promotions/product/{id}
    res = await client.post(
        f"/api/v1/promotions/product/{prod.id}",
        json={
            "promo_type": "coupon_code",
            "title": "VIP Club $150 Coupon",
            "coupon_code": "VIP150",
            "discount_type": "fixed_amount",
            "discount_value": 150.0,
            "description": "$150 instant discount for members",
        }
    )
    assert res.status_code == 201
    data = res.json()
    assert data["coupon_code"] == "VIP150"
    assert data["effective_price"] == 850.0
    promo_id = data["id"]

    # 2. GET /api/v1/promotions/product/{id}
    res = await client.get(f"/api/v1/promotions/product/{prod.id}")
    assert res.status_code == 200
    assert len(res.json()) == 1

    # 3. GET /api/v1/promotions/active
    res = await client.get("/api/v1/promotions/active")
    assert res.status_code == 200
    assert res.json()["total"] == 1

    # 4. POST /api/v1/promotions/detect
    res = await client.post(
        "/api/v1/promotions/detect",
        json={
            "text": "Flash deal: Save 30% using coupon CYBER30 at checkout!",
            "original_price": 200.0,
            "use_ai": False,
        }
    )
    assert res.status_code == 200
    detected = res.json()
    assert len(detected) >= 1
    assert detected[0]["coupon_code"] == "CYBER30"
    assert detected[0]["effective_price"] == 140.0

    # 5. POST /api/v1/promotions/{id}/toggle
    res = await client.post(f"/api/v1/promotions/{promo_id}/toggle")
    assert res.status_code == 200
    assert res.json()["is_active"] is False

    # 6. DELETE /api/v1/promotions/{id}
    res = await client.delete(f"/api/v1/promotions/{promo_id}")
    assert res.status_code == 200
    assert res.json()["success"] is True

