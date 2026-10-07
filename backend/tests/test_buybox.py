"""
Unit and integration tests for Marketplace Buy Box Win/Loss Predictor & Tracker.
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.models.database import Base, get_db
from app.models.product import Product
from app.models.buybox import ProductBuyBoxState, ProductBuyBoxHistory
from app.services.buybox_service import buybox_service
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


def test_calculate_win_probability_fba_vs_fbm():
    # Both FBA at same price ($100.00)
    res_parity = buybox_service.calculate_win_probability(
        winner_price=100.0,
        winner_fulfillment="fba",
        seller_price=100.0,
        seller_fulfillment="fba",
    )
    assert 50.0 <= res_parity["win_probability_pct"] <= 60.0

    # Seller is FBA, competitor is FBM (FBA gives big advantage)
    res_fba_adv = buybox_service.calculate_win_probability(
        winner_price=100.0,
        winner_fulfillment="fbm",
        seller_price=100.0,
        seller_fulfillment="fba",
    )
    assert res_fba_adv["win_probability_pct"] >= 75.0

    # Seller is FBM, competitor is FBA (FBM disadvantage)
    res_fbm_disadv = buybox_service.calculate_win_probability(
        winner_price=100.0,
        winner_fulfillment="fba",
        seller_price=100.0,
        seller_fulfillment="fbm",
    )
    assert res_fbm_disadv["win_probability_pct"] <= 35.0


def test_calculate_win_probability_suppression():
    res = buybox_service.calculate_win_probability(
        winner_price=50.0,
        is_suppressed=True,
    )
    assert res["win_probability_pct"] == 0.0
    assert "suppressed" in res["status_verdict"].lower()


@pytest.mark.asyncio
async def test_buybox_observation_and_history_lifecycle(async_db):
    prod = Product(
        name="Noise Cancelling Wireless Earbuds",
        price=79.99,
        url="https://amazon.com/dp/B001",
        source_domain="amazon.com",
    )
    async_db.add(prod)
    await async_db.commit()
    await async_db.refresh(prod)

    # Observation 1: Competitor owns Buy Box
    obs_1 = {
        "current_winner": "CompetitorDirect",
        "winner_price": 79.99,
        "fulfillment_type": "fba",
        "is_suppressed": False,
        "tracked_seller_name": "My Store",
        "tracked_seller_price": 84.99,
        "tracked_seller_fulfillment": "fba",
    }
    state_1 = await buybox_service.record_buybox_observation(async_db, prod.id, obs_1)
    assert state_1["current_winner"] == "CompetitorDirect"
    assert state_1["is_tracked_seller_winner"] is False
    assert len(state_1["history"]) == 1

    # Observation 2: My Store undercuts and wins Buy Box
    obs_2 = {
        "current_winner": "My Store",
        "winner_price": 74.99,
        "fulfillment_type": "fba",
        "is_suppressed": False,
        "tracked_seller_name": "My Store",
        "tracked_seller_price": 74.99,
        "tracked_seller_fulfillment": "fba",
    }
    state_2 = await buybox_service.record_buybox_observation(async_db, prod.id, obs_2)
    assert state_2["is_tracked_seller_winner"] is True
    assert state_2["history"][0]["event_type"] == "won"

    # Observation 3: Buy Box suppressed
    obs_3 = {
        "current_winner": "My Store",
        "winner_price": 74.99,
        "is_suppressed": True,
        "tracked_seller_name": "My Store",
    }
    state_3 = await buybox_service.record_buybox_observation(async_db, prod.id, obs_3)
    assert state_3["is_suppressed"] is True
    assert state_3["history"][0]["event_type"] == "suppressed"

    # Check analytics
    detail = await buybox_service.get_buybox_detail(async_db, prod.id)
    assert detail["analytics"]["total_observations"] == 3

    # Check catalog alerts
    alerts = await buybox_service.get_catalog_buybox_alerts(async_db)
    assert alerts["total_suppressed_buyboxes"] >= 1


@pytest.mark.asyncio
async def test_buybox_api_routes(client, async_db):
    prod = Product(
        name="Gaming Mechanical Keyboard RGB",
        price=129.99,
        url="https://amazon.com/dp/B002",
        source_domain="amazon.com",
    )
    async_db.add(prod)
    await async_db.commit()
    await async_db.refresh(prod)

    # 1. GET /api/v1/buybox/product/{id}
    get_res = await client.get(f"/api/v1/buybox/product/{prod.id}")
    assert get_res.status_code == 200
    assert get_res.json()["product_id"] == prod.id

    # 2. POST /api/v1/buybox/product/{id}/evaluate
    eval_res = await client.post(
        f"/api/v1/buybox/product/{prod.id}/evaluate",
        json={
            "winner_price": 120.0,
            "winner_fulfillment": "fba",
            "seller_price": 115.0,
            "seller_fulfillment": "fba",
        }
    )
    assert eval_res.status_code == 200
    assert eval_res.json()["win_probability_pct"] >= 70.0

    # 3. POST /api/v1/buybox/product/{id}/observation
    obs_res = await client.post(
        f"/api/v1/buybox/product/{prod.id}/observation",
        json={
            "current_winner": "KeyboardKing",
            "winner_price": 119.0,
            "fulfillment_type": "fba",
            "is_suppressed": False,
            "tracked_seller_name": "My Store",
            "tracked_seller_price": 129.0,
        }
    )
    assert obs_res.status_code == 200
    assert obs_res.json()["current_winner"] == "KeyboardKing"

    # 4. GET /api/v1/buybox/alerts
    alerts_res = await client.get("/api/v1/buybox/alerts")
    assert alerts_res.status_code == 200
    assert alerts_res.json()["total_lost_buyboxes"] >= 1
