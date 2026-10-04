import pytest
from datetime import datetime, timezone
from croniter import croniter

from app.services.scheduler_service import calculate_next_run
from app.models.product import Product, PriceHistory
from app.models.schedule import ScheduledJob
from app.schemas.schedule_schema import ScheduleCreate, ScheduleResponse


def test_calculate_next_run():
    base = datetime(2026, 1, 1, 8, 0, 0, tzinfo=timezone.utc)
    # Cron: daily at 9 AM
    next_run = calculate_next_run("0 9 * * *", base)
    assert next_run.hour == 9
    assert next_run.minute == 0
    assert next_run.day == 1

    # Hourly cron
    hourly_next = calculate_next_run("0 * * * *", base)
    assert hourly_next.hour == 9
    assert hourly_next.minute == 0


def test_price_history_model():
    p = Product(
        name="Test Laptop",
        url="https://example.com/laptop",
        price=1000.0,
        lowest_price=900.0,
        highest_price=1050.0,
        previous_price=1050.0,
        price_change=-50.0,
        price_change_percentage=-4.76,
    )
    p_dict = p.to_dict()
    assert p_dict["price"] == 1000.0
    assert p_dict["previous_price"] == 1050.0
    assert p_dict["price_change"] == -50.0
    assert p_dict["price_change_percentage"] == -4.76

    ph = PriceHistory(
        product_id=1,
        price=950.0,
        currency="USD",
        price_text="$950.00"
    )
    ph_dict = ph.to_dict()
    assert ph_dict["price"] == 950.0
    assert ph_dict["currency"] == "USD"


def test_scheduled_job_model():
    sched = ScheduledJob(
        name="Daily Monitor",
        url="https://allbirds.com",
        domain="allbirds.com",
        cron_expression="0 9 * * *",
        frequency_label="Daily at 09:00 AM",
        is_active=True,
    )
    d = sched.to_dict()
    assert d["name"] == "Daily Monitor"
    assert d["cron_expression"] == "0 9 * * *"
    assert d["is_active"] is True
    assert d["domain"] == "allbirds.com"
