import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import Response
from app.services.currency_service import CurrencyService, currency_service


def test_detect_currency():
    assert currency_service.detect_currency("£49.99") == "GBP"
    assert currency_service.detect_currency("$120.00") == "USD"
    assert currency_service.detect_currency("CA$ 89.95") == "CAD"
    assert currency_service.detect_currency("A$ 150.00") == "AUD"
    assert currency_service.detect_currency("PKR 14,500") == "PKR"
    assert currency_service.detect_currency("Rs. 1,200") == "PKR"
    assert currency_service.detect_currency("29.99 €") == "EUR"
    assert currency_service.detect_currency("¥ 4,500") == "JPY"
    assert currency_service.detect_currency("None", default="USD") == "USD"


@pytest.mark.asyncio
async def test_convert_price_same_currency():
    converted, rate = await currency_service.convert_price(100.0, "USD", "USD")
    assert converted == 100.0
    assert rate == 1.0


@pytest.mark.asyncio
async def test_convert_price_fallback_rates():
    # Test using fallback rates without network call
    service = CurrencyService()
    # Mock network error to verify graceful fallback
    with patch("httpx.AsyncClient.get", side_effect=Exception("API down")):
        converted, rate = await service.convert_price(100.0, "GBP", "USD")
        assert converted is not None
        assert converted > 100.0  # 1 GBP > 1 USD in fallback rates (0.79 GBP per USD)
        assert rate is not None


@pytest.mark.asyncio
async def test_convert_price_live_rates():
    service = CurrencyService()
    mock_res = MagicMock(spec=Response)
    mock_res.status_code = 200
    mock_res.json = MagicMock(return_value={
        "result": "success",
        "rates": {
            "USD": 1.0,
            "EUR": 0.90,
            "GBP": 0.80,
            "PKR": 280.0,
        }
    })

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_res
        converted, rate = await service.convert_price(80.0, "GBP", "USD")
        # 80 GBP with rate 0.80 means 100 USD
        assert converted == 100.0
        assert rate == 1.25


@pytest.mark.asyncio
async def test_normalize_product():
    product = {
        "name": "Mechanical Keyboard",
        "price": 50.0,
        "currency": "GBP",
        "price_text": "£50.00"
    }
    with patch.object(currency_service, "convert_price", new_callable=AsyncMock) as mock_convert:
        mock_convert.return_value = (65.0, 1.30)
        res = await currency_service.normalize_product(product, target_currency="USD")
        assert res["normalized_price"] == 65.0
        assert res["normalized_currency"] == "USD"
        assert res["exchange_rate"] == 1.30
