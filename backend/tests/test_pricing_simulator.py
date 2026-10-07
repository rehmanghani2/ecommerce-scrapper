"""
Unit and integration tests for AI Competitor Strategy & Pricing Simulator Engine.
Tests demand elasticity, margin and volume calculations, game-theory price war risks, and API endpoints.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.models.database import Base, get_db
from app.models.product import Product
from app.models.simulator import PricingSimulationScenario
from app.services.pricing_simulator_service import pricing_simulator_service
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


def test_elasticity_lookup():
    """Test category elasticity lookup."""
    assert pricing_simulator_service.get_elasticity("electronics") == -1.5
    assert pricing_simulator_service.get_elasticity("apparel & fashion") == -1.2
    assert pricing_simulator_service.get_elasticity("groceries") == -0.7
    assert pricing_simulator_service.get_elasticity("unknown_xyz") == -1.2


def test_run_simulation_mechanics():
    """Test price delta, volume gains, break-even multiplier, and price war risk."""
    # Test a 10% price drop on $100 electronics product with $60 COGS
    sim = pricing_simulator_service.run_simulation(
        current_price=100.0,
        proposed_price=90.0,
        cogs=60.0,
        category="electronics",
        competitor_price=100.0
    )

    assert sim["price_delta_pct"] == -10.0
    assert sim["elasticity"] == -1.5
    # Volume should expand by -1.5 * -10% = +15%
    assert sim["projected_unit_sales_change_pct"] == 15.0
    # Current margin = 40. Proposed margin = 30. Break even = 40/30 = 1.33x (+33.3% units needed)
    assert sim["break_even_volume_multiplier"] == 1.33
    assert sim["current_margin_pct"] == 40.0
    assert sim["proposed_margin_pct"] == 33.3
    # Dropping price by 10% against $100 competitor triggers moderate/high reaction
    assert sim["competitor_reaction_probability"] >= 70.0
    assert sim["price_war_risk"] in ("moderate", "high")
    assert sim["optimal_sweet_spot_price"] is not None
    assert len(sim["strategic_verdict"]) > 20


def test_invalid_simulation_inputs():
    """Ensure negative or zero prices raise validation error."""
    with pytest.raises(ValueError):
        pricing_simulator_service.run_simulation(current_price=-5.0, proposed_price=10.0)

    with pytest.raises(ValueError):
        pricing_simulator_service.run_simulation(current_price=10.0, proposed_price=0.0)


@pytest.mark.asyncio
async def test_scenario_persistence_and_crud(async_db):
    """Test saving, retrieving, and deleting simulation scenarios."""
    prod = Product(
        name="Noise Cancelling Wireless Earbuds",
        price=149.99,
        category="electronics",
        url="https://amazon.com/dp/earbuds"
    )
    async_db.add(prod)
    await async_db.commit()
    await async_db.refresh(prod)

    # 1. Save scenario
    saved = await pricing_simulator_service.save_scenario(
        db=async_db,
        product_id=prod.id,
        scenario_name="Test Black Friday 15% Drop",
        current_price=149.99,
        proposed_price=127.49,
        cogs=80.0,
        category="electronics"
    )
    assert saved["id"] is not None
    assert saved["price_change_percentage"] == -15.0
    assert saved["price_war_risk"] in ("high", "moderate")

    # 2. Get scenarios
    list_scenarios = await pricing_simulator_service.get_scenarios_for_product(async_db, prod.id)
    assert len(list_scenarios) == 1
    assert list_scenarios[0]["scenario_name"] == "Test Black Friday 15% Drop"

    # 3. Delete scenario
    deleted = await pricing_simulator_service.delete_scenario(async_db, saved["id"])
    assert deleted is True

    # Confirm deletion
    remaining = await pricing_simulator_service.get_scenarios_for_product(async_db, prod.id)
    assert len(remaining) == 0


@pytest.mark.asyncio
async def test_pricing_simulator_api_routes(client, async_db):
    """Test API routes for live simulation and scenario persistence."""
    prod = Product(
        name="Smart Coffee Maker Espresso Machine",
        price=299.99,
        category="appliances",
        url="https://target.com/coffee"
    )
    async_db.add(prod)
    await async_db.commit()
    await async_db.refresh(prod)

    # 1. POST /api/v1/simulator/simulate
    sim_resp = await client.post(
        "/api/v1/simulator/simulate",
        json={
            "current_price": 299.99,
            "proposed_price": 279.99,
            "cogs": 180.0,
            "category": "appliances",
            "competitor_price": 299.99
        }
    )
    assert sim_resp.status_code == 200
    res = sim_resp.json()
    assert res["price_delta_pct"] < 0
    assert res["projected_unit_sales_change_pct"] > 0
    assert "strategic_verdict" in res

    # 2. POST /api/v1/simulator/scenarios
    save_resp = await client.post(
        "/api/v1/simulator/scenarios",
        json={
            "product_id": prod.id,
            "scenario_name": "Summer Promo Test",
            "current_price": 299.99,
            "proposed_price": 269.99,
            "cogs": 180.0,
            "category": "appliances"
        }
    )
    assert save_resp.status_code == 200
    sid = save_resp.json()["id"]

    # 3. GET /api/v1/simulator/scenarios/{product_id}
    get_resp = await client.get(f"/api/v1/simulator/scenarios/{prod.id}")
    assert get_resp.status_code == 200
    assert len(get_resp.json()) == 1

    # 4. DELETE /api/v1/simulator/scenarios/{id}
    del_resp = await client.delete(f"/api/v1/simulator/scenarios/{sid}")
    assert del_resp.status_code == 200
    assert del_resp.json()["success"] is True
