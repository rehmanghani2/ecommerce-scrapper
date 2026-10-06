"""
Unit and integration tests for Competitor Inventory Depletion & Stockout Forecasting Engine.
Tests stock observation deltas, sales velocity calculation, predicted stockouts, and API endpoints.
"""

import pytest
import pytest_asyncio
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.models.database import Base, get_db
from app.models.product import Product
from app.services.inventory_depletion_service import inventory_service
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
async def test_record_stock_observations_and_deltas(async_db):
    """Test tracking stock level changes (initial, depletion, restock, out of stock)."""
    # 1. Create a product
    product = Product(
        name="Competitor Wireless Noise Cancelling Headphones",
        price=199.99,
        source_domain="amazon.com",
        url="https://amazon.com/dp/B001",
        in_stock=True,
        stock_quantity=50
    )
    async_db.add(product)
    await async_db.commit()
    await async_db.refresh(product)

    t0 = datetime.now(timezone.utc) - timedelta(days=5)
    t1 = datetime.now(timezone.utc) - timedelta(days=3)
    t2 = datetime.now(timezone.utc) - timedelta(days=1)
    now = datetime.now(timezone.utc)

    # Observation 1: initial 50 units
    obs1 = await inventory_service.record_stock_observation(
        async_db, product_id=product.id, stock_quantity=50, in_stock=True, recorded_at=t0
    )
    assert obs1["history"]["change_type"] == "initial"
    assert obs1["history"]["delta"] == 0

    # Observation 2: dropped to 35 units (depletion of 15 units over 2 days)
    obs2 = await inventory_service.record_stock_observation(
        async_db, product_id=product.id, stock_quantity=35, in_stock=True, recorded_at=t1
    )
    assert obs2["history"]["change_type"] == "depletion"
    assert obs2["history"]["delta"] == -15

    # Observation 3: restocked to 80 units (+45 units)
    obs3 = await inventory_service.record_stock_observation(
        async_db, product_id=product.id, stock_quantity=80, in_stock=True, recorded_at=t2
    )
    assert obs3["history"]["change_type"] == "restock"
    assert obs3["history"]["delta"] == 45

    # Observation 4: dropped to 10 units (depletion of 70 units)
    obs4 = await inventory_service.record_stock_observation(
        async_db, product_id=product.id, stock_quantity=10, in_stock=True, recorded_at=now
    )
    assert obs4["history"]["change_type"] == "depletion"
    assert obs4["history"]["delta"] == -70

    # Verify forecast velocity and stockout calculation
    fc = obs4["forecast"]
    assert fc["total_units_sold"] == 85  # 15 + 70
    assert fc["total_restocks"] == 1
    assert fc["current_stock"] == 10
    assert fc["sales_velocity_per_day"] > 0
    assert fc["days_until_stockout"] is not None
    assert fc["stockout_risk_level"] in ("high", "medium")
    assert "High Stockout Risk" in fc["opportunity_verdict"] or "Medium Stockout Risk" in fc["opportunity_verdict"]


@pytest.mark.asyncio
async def test_out_of_stock_transition_and_opportunity(async_db):
    """Test transition to out of stock triggers out_of_stock risk and opportunity verdict."""
    product = Product(
        name="Ultra Slim OLED TV 65-inch",
        price=1299.00,
        source_domain="walmart.com",
        url="https://walmart.com/ip/oled65",
        in_stock=True,
        stock_quantity=4
    )
    async_db.add(product)
    await async_db.commit()
    await async_db.refresh(product)

    # Initial 4 units
    await inventory_service.record_stock_observation(
        async_db, product_id=product.id, stock_quantity=4, in_stock=True
    )

    # Flip to out of stock
    res = await inventory_service.record_stock_observation(
        async_db, product_id=product.id, stock_quantity=0, in_stock=False
    )
    fc = res["forecast"]
    assert fc["is_in_stock"] is False
    assert fc["stockout_risk_level"] == "out_of_stock"
    assert fc["days_until_stockout"] == 0.0
    assert "Out of Stock" in fc["opportunity_verdict"]


@pytest.mark.asyncio
async def test_inventory_api_routes(client, async_db):
    """Test API endpoints for inventory stock observation and opportunity queries."""
    # Create product
    product = Product(
        name="Mechanical Gaming Keyboard RGB",
        price=89.99,
        source_domain="bestbuy.com",
        url="https://bestbuy.com/kb1",
        in_stock=True,
        stock_quantity=20
    )
    async_db.add(product)
    await async_db.commit()
    await async_db.refresh(product)

    # 1. Record stock observation via API
    resp1 = await client.post(
        f"/api/v1/products/{product.id}/stock",
        json={"stock_quantity": 20, "in_stock": True}
    )
    assert resp1.status_code == 200
    assert resp1.json()["history"]["stock_quantity"] == 20

    # 2. Record depletion to 3 units
    resp2 = await client.post(
        f"/api/v1/products/{product.id}/stock",
        json={"stock_quantity": 3, "in_stock": True}
    )
    assert resp2.status_code == 200
    assert resp2.json()["history"]["change_type"] == "depletion"
    assert resp2.json()["history"]["delta"] == -17

    # 3. Get Forecast
    fc_resp = await client.get(f"/api/v1/products/{product.id}/inventory-forecast")
    assert fc_resp.status_code == 200
    fc = fc_resp.json()
    assert fc["current_stock"] == 3
    assert fc["total_units_sold"] == 17

    # 4. Get History
    hist_resp = await client.get(f"/api/v1/products/{product.id}/stock-history")
    assert hist_resp.status_code == 200
    history = hist_resp.json()
    assert len(history) == 2

    # 5. Get Opportunities across catalog
    opp_resp = await client.get("/api/v1/inventory/opportunities")
    assert opp_resp.status_code == 200
    opps = opp_resp.json()
    assert len(opps) >= 1
    assert opps[0]["product"]["id"] == product.id
