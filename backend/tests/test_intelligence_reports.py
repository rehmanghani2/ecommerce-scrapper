"""
Unit and integration tests for Scheduled Competitor Intelligence Reports via Email and PDF.
Tests data compilation, HTML digest generation, ReportLab PDF compilation, and API routes.
"""

import pytest
import pytest_asyncio
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.models.database import Base, get_db
from app.models.product import Product, ProductInventoryForecast, ProductSentimentSummary
from app.models.report import ReportSchedule, GeneratedReport
from app.services.report_service import report_service, calculate_next_run
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
async def test_compile_intelligence_data_and_templates(async_db):
    """Test data compilation, HTML email generation, and ReportLab PDF generation."""
    # 1. Seed products with price drops and stockouts
    p1 = Product(
        name="Flagship Active Noise Cancelling Headphones",
        price=149.99,
        previous_price=199.99,  # $50 price drop
        source_domain="amazon.com",
        url="https://amazon.com/dp/1",
        in_stock=True,
        stock_quantity=8
    )
    p2 = Product(
        name="Ultra 4K Smart OLED Television 55-inch",
        price=899.00,
        previous_price=899.00,
        source_domain="walmart.com",
        url="https://walmart.com/ip/2",
        in_stock=True,
        stock_quantity=2
    )
    async_db.add_all([p1, p2])
    await async_db.commit()
    await async_db.refresh(p1)
    await async_db.refresh(p2)

    # Add stockout forecast for p2
    fc = ProductInventoryForecast(
        product_id=p2.id,
        current_stock=2,
        sales_velocity_per_day=1.5,
        estimated_daily_revenue=1348.5,
        days_until_stockout=1.3,
        stockout_risk_level="high",
        opportunity_verdict="High stockout risk in 1.3 days"
    )
    # Add sentiment weaknesses for p1
    sent = ProductSentimentSummary(
        product_id=p1.id,
        total_reviews_analyzed=10,
        negative_percentage=35.0,
        key_weaknesses=["Ear cushions wear out", "Bluetooth disconnects"],
        buyer_pain_points=["Charging case feels cheap"]
    )
    async_db.add_all([fc, sent])
    await async_db.commit()

    # Compile data
    data = await report_service.compile_intelligence_data(async_db)
    assert data["total_products"] == 2
    assert data["total_price_drops_count"] == 1
    assert data["top_price_drops"][0]["drop_percentage"] == 25.0
    assert len(data["stockout_opportunities"]) == 1
    assert len(data["vulnerabilities"]) == 1

    # Generate HTML
    html = report_service.generate_html_report(data)
    assert "Competitor Intelligence Digest" in html
    assert "Flagship Active Noise Cancelling Headphones" in html
    assert "-25.0%" in html
    assert "1.3 days" in html

    # Generate PDF
    pdf_bytes = report_service.generate_pdf_report(data)
    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 1000


@pytest.mark.asyncio
async def test_schedule_crud_and_trigger(async_db):
    """Test creating, triggering, and managing report schedules."""
    # Create schedule
    sched = await report_service.create_schedule(
        db=async_db,
        name="Weekly Monday Executive Digest",
        recipient_emails=["analytics@mybrand.com"],
        frequency="weekly",
        cron_expression="0 9 * * 1",
        format="both"
    )
    assert sched["id"] is not None
    assert sched["is_active"] is True
    assert sched["next_run_at"] is not None

    # Trigger immediately
    run_res = await report_service.trigger_schedule_report(async_db, sched["id"])
    assert run_res["success"] is True
    assert run_res["report_id"] is not None
    assert run_res["next_run_at"] is not None

    # Check updated record in DB
    updated = await async_db.get(ReportSchedule, sched["id"])
    assert updated.total_sent == 1
    assert updated.last_status == "success"

    # Delete
    del_res = await report_service.delete_schedule(async_db, sched["id"])
    assert del_res is True


@pytest.mark.asyncio
async def test_report_api_routes(client, async_db):
    """Test API endpoints for PDF downloads, HTML previews, and schedules."""
    # 1. Preview HTML
    prev_resp = await client.get("/api/v1/reports/preview")
    assert prev_resp.status_code == 200
    assert "text/html" in prev_resp.headers.get("content-type", "")
    assert "Competitor Intelligence" in prev_resp.text

    # 2. Download PDF
    pdf_resp = await client.get("/api/v1/reports/download-pdf")
    assert pdf_resp.status_code == 200
    assert "application/pdf" in pdf_resp.headers.get("content-type", "")
    assert pdf_resp.content.startswith(b"%PDF")

    # 3. Create Schedule
    sched_resp = await client.post(
        "/api/v1/reports/schedules",
        json={
            "name": "Daily Price Drops Brief",
            "recipient_emails": ["team@store.com"],
            "frequency": "daily",
            "cron_expression": "0 8 * * *",
            "format": "email_html"
        }
    )
    assert sched_resp.status_code == 200
    sid = sched_resp.json()["id"]

    # 4. List Schedules
    list_resp = await client.get("/api/v1/reports/schedules")
    assert list_resp.status_code == 200
    assert len(list_resp.json()) >= 1

    # 5. Send Test
    test_send_resp = await client.post(
        "/api/v1/reports/send-test",
        json={"recipient_email": "test@domain.com", "format": "both"}
    )
    assert test_send_resp.status_code == 200
    assert test_send_resp.json()["success"] is True

    # 6. Delete Schedule
    del_resp = await client.delete(f"/api/v1/reports/schedules/{sid}")
    assert del_resp.status_code == 200
    assert del_resp.json()["success"] is True
