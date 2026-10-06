import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.repricing_service import RepricingService, repricing_service
from app.models.repricing import RepricingRule
from app.models.product import Product


def test_calculate_new_price_beat_percentage():
    # 2% cheaper than $100 -> $98.00
    price, status = RepricingService.calculate_new_price(
        competitor_price=100.0,
        strategy="beat_by_percentage",
        adjustment_value=2.0
    )
    assert price == 98.0
    assert status == "applied"


def test_calculate_new_price_beat_fixed():
    # $5 cheaper than $50 -> $45.00
    price, status = RepricingService.calculate_new_price(
        competitor_price=50.0,
        strategy="beat_by_fixed",
        adjustment_value=5.0
    )
    assert price == 45.0
    assert status == "applied"


def test_calculate_new_price_match():
    # Exactly match competitor
    price, status = RepricingService.calculate_new_price(
        competitor_price=79.99,
        strategy="match_price",
        adjustment_value=0.0
    )
    assert price == 79.99
    assert status == "applied"


def test_calculate_new_price_markup_percentage():
    # 10% markup over competitor $100 -> $110
    price, status = RepricingService.calculate_new_price(
        competitor_price=100.0,
        strategy="markup_percentage",
        adjustment_value=10.0
    )
    assert price == 110.0
    assert status == "applied"


def test_calculate_new_price_floor_guardrail():
    # Competitor drops to $10, rule says 50% cheaper ($5), but floor is $15 -> bounded to $15
    price, status = RepricingService.calculate_new_price(
        competitor_price=10.0,
        strategy="beat_by_percentage",
        adjustment_value=50.0,
        min_floor_price=15.0
    )
    assert price == 15.0
    assert status == "bounded_by_floor"


def test_calculate_new_price_ceiling_guardrail():
    # Price would be $200, but ceiling is $150 -> bounded to $150
    price, status = RepricingService.calculate_new_price(
        competitor_price=200.0,
        strategy="match_price",
        adjustment_value=0.0,
        max_ceiling_price=150.0
    )
    assert price == 150.0
    assert status == "bounded_by_ceiling"


@pytest.mark.asyncio
async def test_trigger_custom_webhook():
    payload = {"event": "price_match", "new_price": 49.99}
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp

        success, msg = await repricing_service.trigger_custom_webhook(
            webhook_url="https://example.com/api/repricer",
            payload=payload,
            secret="test_secret_token"
        )
        assert success is True
        assert "HTTP 200" in msg
