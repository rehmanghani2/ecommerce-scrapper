"""
Unit and integration tests for Headless Browser Proxy Rotation Dashboard & Service.
Tests proxy parsing, state calculation, domain telemetry, blacklisting, and API routes.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient, Response
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.models.database import Base, get_db
from app.models.proxy import ProxyRecord
from app.services.proxy_service import proxy_service, parse_proxy_string, extract_domain
from app.main import app


# Use in-memory SQLite for testing
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


def test_parse_proxy_string():
    """Test various proxy syntax parsing formats."""
    # Standard http with user/pass
    p1 = parse_proxy_string("http://bob:secret123@192.168.1.1:8080")
    assert p1 is not None
    assert p1["server"] == "192.168.1.1:8080"
    assert p1["username"] == "bob"
    assert p1["password"] == "secret123"
    assert p1["protocol"] == "http"

    # IP:PORT:USER:PASS format
    p2 = parse_proxy_string("10.0.0.1:9090:admin:pass999")
    assert p2 is not None
    assert p2["server"] == "10.0.0.1:9090"
    assert p2["username"] == "admin"
    assert p2["password"] == "pass999"

    # SOCKS5 format
    p3 = parse_proxy_string("socks5://proxy.datacenter.io:1080")
    assert p3 is not None
    assert p3["protocol"] == "socks5"
    assert p3["server"] == "proxy.datacenter.io:1080"
    assert p3["username"] is None

    # Empty or comment
    assert parse_proxy_string("") is None
    assert parse_proxy_string("# comment") is None


def test_extract_domain():
    """Test domain extraction utility."""
    assert extract_domain("https://www.amazon.com/dp/B08N5WRWNW") == "amazon.com"
    assert extract_domain("http://walmart.com/ip/12345") == "walmart.com"
    assert extract_domain("https://store.target.com:443/item") == "store.target.com"


@pytest.mark.asyncio
async def test_proxy_record_states_and_serialization(async_db):
    """Test dynamic health states (healthy, cooling, banned, inactive)."""
    # 1. Healthy record
    p1 = ProxyRecord(
        raw_url="http://admin:pass@192.168.1.100:8080",
        server="192.168.1.100:8080",
        protocol="http",
        username="admin",
        password="pass",
        country_code="US",
        is_active=True,
        is_banned=False,
    )
    async_db.add(p1)
    await async_db.commit()
    await async_db.refresh(p1)

    assert p1.state == "healthy"
    assert "admin:****@192.168.1.100:8080" in p1.masked_url()
    d1 = p1.to_dict()
    assert d1["has_auth"] is True
    assert d1["state"] == "healthy"

    # 2. Inactive record
    p1.is_active = False
    assert p1.state == "inactive"

    # 3. Cooling record
    p1.is_active = True
    p1.cooldown_until = datetime.now(timezone.utc) + timedelta(minutes=5)
    assert p1.is_cooling is True
    assert p1.state == "cooling"

    # 4. Banned record
    p1.is_banned = True
    p1.ban_reason = "Manual ban"
    assert p1.state == "banned"


@pytest.mark.asyncio
async def test_import_and_filter_proxies(async_db):
    """Test bulk import with duplicate detection and filter querying."""
    raw_list = [
        "http://1.1.1.1:8080",
        "http://2.2.2.2:8080",
        "http://1.1.1.1:8080",  # Duplicate
        "socks5://3.3.3.3:1080",
    ]
    res = await proxy_service.import_proxies(async_db, raw_list, country_code="US")
    assert res["added"] == 3
    assert res["skipped"] == 1

    # Query all
    data = await proxy_service.get_all_proxies(async_db)
    assert data["total"] == 3
    assert data["healthy"] == 3

    # Query filtered by protocol
    socks_data = await proxy_service.get_all_proxies(async_db, protocol="socks5")
    assert len(socks_data["proxies"]) == 1
    assert socks_data["proxies"][0]["server"] == "3.3.3.3:1080"


@pytest.mark.asyncio
async def test_proxy_live_testing_and_cooldown(async_db):
    """Test single proxy pinging, measuring latency, exit IP, and 403 cooldown."""
    res = await proxy_service.import_proxies(async_db, ["http://1.2.3.4:8080"])
    proxy_id = res["proxies"][0]["id"]

    # Mock successful response
    mock_resp_200 = MagicMock()
    mock_resp_200.status_code = 200
    mock_resp_200.json.return_value = {"origin": "104.28.19.4"}

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp_200
        test_res = await proxy_service.test_proxy(async_db, proxy_id)
        assert test_res["success"] is True
        assert test_res["status_code"] == 200
        assert test_res["exit_ip"] == "104.28.19.4"
        assert test_res["state"] == "healthy"

    # Mock 403 Forbidden triggering cooldown
    mock_resp_403 = MagicMock()
    mock_resp_403.status_code = 403

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp_403
        test_res_403 = await proxy_service.test_proxy(async_db, proxy_id)
        assert test_res_403["success"] is False
        assert test_res_403["status_code"] == 403
        assert test_res_403["state"] == "cooling"


@pytest.mark.asyncio
async def test_domain_telemetry_and_blacklisting(async_db):
    """Test recording scraper outcomes per domain and blacklisting."""
    res = await proxy_service.import_proxies(async_db, ["http://9.9.9.9:8080"])
    proxy_id = res["proxies"][0]["id"]

    # Record successful scrape on amazon.com
    await proxy_service.record_scrape_telemetry(
        async_db,
        proxy_server_or_url="9.9.9.9:8080",
        target_url="https://www.amazon.com/dp/123",
        success=True,
        status_code=200,
        latency_ms=250.0,
    )

    # Record 3 blocks on walmart.com triggering domain ban
    for _ in range(3):
        await proxy_service.record_scrape_telemetry(
            async_db,
            proxy_server_or_url="9.9.9.9:8080",
            target_url="https://www.walmart.com/ip/555",
            success=False,
            status_code=403,
            latency_ms=120.0,
        )

    # Check domain summary
    summaries = await proxy_service.get_domain_metrics_summary(async_db)
    domains = {s["domain"]: s for s in summaries}
    assert "amazon.com" in domains
    assert domains["amazon.com"]["success_rate"] == 100.0
    assert "walmart.com" in domains
    assert domains["walmart.com"]["success_rate"] == 0.0
    assert domains["walmart.com"]["banned_proxies"] == 1

    # Manual blacklist toggle
    banned = await proxy_service.toggle_blacklist(async_db, proxy_id, is_banned=True, reason="User manual ban")
    assert banned["is_banned"] is True
    assert banned["state"] == "banned"

    # Unban
    unbanned = await proxy_service.toggle_blacklist(async_db, proxy_id, is_banned=False)
    assert unbanned["is_banned"] is False
    assert unbanned["state"] == "healthy"


@pytest.mark.asyncio
async def test_proxy_api_routes(client, async_db):
    """Test FastAPI endpoints for proxy management dashboard."""
    # 1. Import via API
    import_resp = await client.post(
        "/api/v1/proxies",
        json={"proxies": "http://user:pass@127.0.0.1:8888\nhttp://127.0.0.2:8888", "default_protocol": "http"}
    )
    assert import_resp.status_code == 200
    assert import_resp.json()["added"] == 2

    # 2. List proxies
    list_resp = await client.get("/api/v1/proxies")
    assert list_resp.status_code == 200
    data = list_resp.json()
    assert data["total"] == 2
    proxy_id = data["proxies"][0]["id"]

    # 3. Toggle blacklist
    bl_resp = await client.post(
        f"/api/v1/proxies/{proxy_id}/blacklist",
        json={"is_banned": True, "reason": "Target blocked IP"}
    )
    assert bl_resp.status_code == 200
    assert bl_resp.json()["is_banned"] is True
    assert bl_resp.json()["state"] == "banned"

    # 4. Domain metrics
    dom_resp = await client.get("/api/v1/proxies/domain-metrics")
    assert dom_resp.status_code == 200
    assert isinstance(dom_resp.json(), list)

    # 5. Reset metrics
    reset_resp = await client.post("/api/v1/proxies/reset-metrics")
    assert reset_resp.status_code == 200
    assert reset_resp.json()["success"] is True

    # 6. Delete proxy
    del_resp = await client.delete(f"/api/v1/proxies/{proxy_id}")
    assert del_resp.status_code == 200
    assert del_resp.json()["success"] is True
