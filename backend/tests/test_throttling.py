"""
Unit and integration tests for Intelligent Scraping Rate-Limiter & Auto-Throttling Engine.
"""
import pytest
import pytest_asyncio
import time
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.models.database import Base, get_db
from app.models.throttle import DomainThrottlePolicy
from app.core.rate_limiter import rate_limiter, TokenBucket, DomainThrottleState
from app.services.rate_limiter_service import rate_limiter_service
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
async def test_token_bucket_flow():
    # TokenBucket with capacity 2 and rate 10 tokens/sec
    bucket = TokenBucket(capacity=2.0, rate=10.0)
    
    # First 2 should have 0 wait time
    wait1 = await bucket.acquire(1.0)
    wait2 = await bucket.acquire(1.0)
    assert wait1 == 0.0
    assert wait2 == 0.0

    # Third should require wait
    t0 = time.monotonic()
    wait3 = await bucket.acquire(1.0)
    t_elapsed = time.monotonic() - t0
    assert wait3 > 0.0
    assert t_elapsed >= 0.05


def test_domain_rate_limiter_backoff_and_jitter():
    dom = "test-store.com"
    state = DomainThrottleState(dom, {
        "min_delay_seconds": 1.0,
        "max_delay_seconds": 20.0,
        "backoff_multiplier": 2.0,
        "jitter_type": "full",
        "is_adaptive": True,
    })

    assert state.status == "healthy"
    assert state.consecutive_throttles == 0

    # 1. First 429
    state.report_error(429)
    assert state.consecutive_throttles == 1
    assert state.total_throttled_429 == 1
    assert state.current_delay >= 0.1
    assert state.status in ("throttled", "degraded")

    # 2. Second 429 (exponential increase)
    state.report_error(429)
    assert state.consecutive_throttles == 2

    # 3. Explicit Retry-After header
    state.report_error(429, retry_after=12.0)
    assert state.current_delay == 12.0
    assert state.cooldown_until > time.monotonic()

    # 4. Successes leading to recovery
    for _ in range(5):
        state.report_success()
    # After 5 successes, delay steps down
    assert state.current_delay < 12.0

    # 5. Reset
    state.reset()
    assert state.status == "healthy"
    assert state.consecutive_throttles == 0
    assert state.current_delay == 1.0


def test_simulate_backoff_curve():
    steps = rate_limiter.simulate_backoff(
        min_delay=0.5,
        max_delay=30.0,
        multiplier=2.0,
        consecutive_errors=4,
        jitter_type="none"
    )
    assert len(steps) == 4
    # Step 1: 0.5 * 2^1 = 1.0
    assert steps[0]["raw_backoff_seconds"] == 1.0
    # Step 2: 0.5 * 2^2 = 2.0
    assert steps[1]["raw_backoff_seconds"] == 2.0
    # Step 3: 0.5 * 2^3 = 4.0
    assert steps[2]["raw_backoff_seconds"] == 4.0
    # Step 4: 0.5 * 2^4 = 8.0
    assert steps[3]["raw_backoff_seconds"] == 8.0


@pytest.mark.asyncio
async def test_throttling_api_endpoints(client, async_db):
    # 1. GET /api/v1/throttling/domains
    res = await client.get("/api/v1/throttling/domains")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) >= 1  # includes defaults

    # 2. POST /api/v1/throttling/domains (create custom policy)
    create_payload = {
        "domain": "custom-market.com",
        "requests_per_second": 1.5,
        "burst_capacity": 4,
        "max_concurrency": 2,
        "min_delay_seconds": 1.0,
        "max_delay_seconds": 25.0,
        "backoff_multiplier": 2.0,
        "jitter_type": "decorrelated",
        "is_adaptive": True,
    }
    create_res = await client.post("/api/v1/throttling/domains", json=create_payload)
    assert create_res.status_code == 200
    created = create_res.json()
    assert created["domain"] == "custom-market.com"
    assert created["requests_per_second"] == 1.5

    # 3. GET /api/v1/throttling/domains/{domain}
    get_res = await client.get("/api/v1/throttling/domains/custom-market.com")
    assert get_res.status_code == 200
    assert get_res.json()["domain"] == "custom-market.com"

    # 4. POST /api/v1/throttling/domains/{domain}/reset
    reset_res = await client.post("/api/v1/throttling/domains/custom-market.com/reset")
    assert reset_res.status_code == 200
    assert reset_res.json()["status"] == "healthy"

    # 5. POST /api/v1/throttling/simulate
    sim_res = await client.post("/api/v1/throttling/simulate", json={
        "min_delay_seconds": 1.0,
        "max_delay_seconds": 20.0,
        "backoff_multiplier": 2.0,
        "consecutive_errors": 3,
        "jitter_type": "full",
    })
    assert sim_res.status_code == 200
    steps = sim_res.json()
    assert len(steps) == 3

    # 6. DELETE /api/v1/throttling/domains/{domain}
    del_res = await client.delete("/api/v1/throttling/domains/custom-market.com")
    assert del_res.status_code == 200
    assert del_res.json()["success"] is True
