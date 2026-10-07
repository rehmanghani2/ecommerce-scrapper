"""
Unit and integration tests for Competitor Search Ranking & SERP Visibility Tracker.
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.models.database import Base, get_db
from app.models.serp import SerpKeyword, SerpRankingItem
from app.models.product import Product
from app.services.serp_service import serp_service
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


def test_calculate_share_of_voice():
    mock_items = [
        {"rank_position": 1, "brand": "Sony", "is_sponsored": False},
        {"rank_position": 2, "brand": "Sony", "is_sponsored": True},
        {"rank_position": 3, "brand": "Bose", "is_sponsored": False},
        {"rank_position": 4, "brand": "Apple", "is_sponsored": False},
    ]
    sov = serp_service.calculate_share_of_voice(mock_items)

    assert sov["total_items"] == 4
    assert sov["organic_count"] == 3
    assert sov["sponsored_count"] == 1
    assert sov["sponsored_density_pct"] == 25.0
    assert sov["brand_share_of_voice"]["Sony"] == 50.0
    assert sov["brand_share_of_voice"]["Bose"] == 25.0
    assert sov["top_brand"] == "Sony"


@pytest.mark.asyncio
async def test_serp_keyword_and_snapshot_lifecycle(async_db):
    # 1. Create keyword
    kw = await serp_service.create_keyword(
        db=async_db,
        keyword="wireless noise cancelling headphones",
        domain="amazon.com",
        marketplace="amazon",
    )
    assert kw.id is not None
    assert kw.keyword == "wireless noise cancelling headphones"

    # 2. Ingest first snapshot
    crawl_1 = [
        {"title": "Sony WH-1000XM5", "url": "https://amazon.com/dp/B01", "brand": "Sony", "rank_position": 1, "is_sponsored": False},
        {"title": "Bose QuietComfort 45", "url": "https://amazon.com/dp/B02", "brand": "Bose", "rank_position": 2, "is_sponsored": False},
        {"title": "Apple AirPods Max", "url": "https://amazon.com/dp/B03", "brand": "Apple", "rank_position": 3, "is_sponsored": True},
    ]
    res_1 = await serp_service.record_serp_snapshot(async_db, kw.id, crawl_1)
    assert res_1["total_items"] == 3
    assert res_1["analytics"]["top_brand"] == "Sony"

    # 3. Ingest second snapshot with rank movements: Bose moves to #1, Sony drops to #2
    crawl_2 = [
        {"title": "Bose QuietComfort 45", "url": "https://amazon.com/dp/B02", "brand": "Bose", "rank_position": 1, "is_sponsored": False},
        {"title": "Sony WH-1000XM5", "url": "https://amazon.com/dp/B01", "brand": "Sony", "rank_position": 2, "is_sponsored": False},
        {"title": "Apple AirPods Max", "url": "https://amazon.com/dp/B03", "brand": "Apple", "rank_position": 3, "is_sponsored": True},
    ]
    res_2 = await serp_service.record_serp_snapshot(async_db, kw.id, crawl_2)
    bose_item = next(i for i in res_2["rankings"] if i["brand"] == "Bose")
    sony_item = next(i for i in res_2["rankings"] if i["brand"] == "Sony")

    # Bose went from 2 to 1 -> rank_change = +1
    assert bose_item["rank_change"] == 1
    # Sony went from 1 to 2 -> rank_change = -1
    assert sony_item["rank_change"] == -1

    # 4. Detail view
    detail = await serp_service.get_keyword_detail(async_db, kw.id)
    assert detail is not None
    assert len(detail["rankings"]) == 3
    assert detail["analytics"]["sponsored_count"] == 1

    # 5. Catalog Insights
    insights = await serp_service.get_serp_insights(async_db)
    assert insights["monitored_keywords"] == 1
    assert insights["total_tracked_rankings"] == 3

    # 6. Delete
    deleted = await serp_service.delete_keyword(async_db, kw.id)
    assert deleted is True
    assert await serp_service.get_keyword_detail(async_db, kw.id) is None


@pytest.mark.asyncio
async def test_serp_api_routes(client, async_db):
    # 1. POST /api/v1/serp/keywords
    post_res = await client.post(
        "/api/v1/serp/keywords",
        json={
            "keyword": "ergonomic mechanical keyboard",
            "domain": "amazon.com",
            "marketplace": "amazon",
            "check_frequency": "daily",
        }
    )
    assert post_res.status_code == 201
    kw_data = post_res.json()
    kw_id = kw_data["id"]
    assert kw_data["keyword"] == "ergonomic mechanical keyboard"

    # 2. GET /api/v1/serp/keywords
    list_res = await client.get("/api/v1/serp/keywords")
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 1

    # 3. POST /api/v1/serp/keywords/{id}/snapshot
    snap_res = await client.post(
        f"/api/v1/serp/keywords/{kw_id}/snapshot",
        json={
            "items": [
                {
                    "title": "Keychron Q1 Pro Wireless Keyboard",
                    "url": "https://amazon.com/dp/KEY01",
                    "brand": "Keychron",
                    "price": 199.99,
                    "rank_position": 1,
                    "is_sponsored": False,
                    "badge": "Amazon's Choice",
                },
                {
                    "title": "Logitech MX Mechanical Mini",
                    "url": "https://amazon.com/dp/LOGI01",
                    "brand": "Logitech",
                    "price": 149.99,
                    "rank_position": 2,
                    "is_sponsored": True,
                }
            ]
        }
    )
    assert snap_res.status_code == 200
    snap_data = snap_res.json()
    assert snap_data["total_items"] == 2
    assert snap_data["analytics"]["top_brand"] == "Keychron"

    # 4. GET /api/v1/serp/keywords/{id}
    detail_res = await client.get(f"/api/v1/serp/keywords/{kw_id}")
    assert detail_res.status_code == 200
    assert len(detail_res.json()["rankings"]) == 2

    # 5. GET /api/v1/serp/insights
    insights_res = await client.get("/api/v1/serp/insights")
    assert insights_res.status_code == 200
    assert insights_res.json()["monitored_keywords"] >= 1

    # 6. DELETE /api/v1/serp/keywords/{id}
    del_res = await client.delete(f"/api/v1/serp/keywords/{kw_id}")
    assert del_res.status_code == 200
    assert del_res.json()["success"] is True
