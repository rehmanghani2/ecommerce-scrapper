"""
Unit tests for Price Drop & Stock Alerts Service and notification dispatchers.
"""

import json
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from app.services.alert_service import AlertService, alert_service
from app.models.alert import AlertConfig, AlertNotificationLog


def test_alert_config_model():
    """Verify AlertConfig model attributes."""
    cfg = AlertConfig(
        id=1,
        channel="telegram",
        name="Telegram Alerts",
        credentials=json.dumps({"bot_token": "12345:ABCDE", "chat_id": "-987654"}),
        is_active=True,
        min_drop_percentage=10.0,
        alert_on_out_of_stock=True,
        alert_on_back_in_stock=True,
    )
    assert cfg.id == 1
    assert cfg.channel == "telegram"
    assert cfg.name == "Telegram Alerts"
    assert cfg.min_drop_percentage == 10.0
    assert cfg.is_active is True
    assert cfg.alert_on_out_of_stock is True
    assert "Telegram Alerts" in repr(cfg)


def test_alert_notification_log_model():
    """Verify AlertNotificationLog model attributes."""
    log_entry = AlertNotificationLog(
        id=42,
        product_id=1,
        channel="slack",
        alert_type="price_drop",
        product_name="Sony WH-1000XM5",
        product_url="https://example.com/sony",
        old_price=399.99,
        new_price=329.99,
        price_change_percentage=17.5,
        status="sent",
        error_message=None
    )
    assert log_entry.id == 42
    assert log_entry.channel == "slack"
    assert log_entry.alert_type == "price_drop"
    assert log_entry.price_change_percentage == 17.5
    assert log_entry.status == "sent"
    assert "Sony WH-1000XM5" in repr(log_entry)


@pytest.mark.asyncio
async def test_telegram_alert_success():
    """Test successful Telegram alert dispatch."""
    service = AlertService()
    sample_data = {
        "alert_type": "price_drop",
        "product_name": "Apple MacBook Pro 16",
        "product_url": "https://example.com/macbook",
        "currency": "USD",
        "old_price": 2499.00,
        "new_price": 2199.00,
        "drop_pct": 12.0
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        ok, msg = await service.send_telegram_alert("12345:TOKEN", "998877", sample_data)
        assert ok is True
        assert "successfully" in msg
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args[1]
        assert "api.telegram.org/bot12345:TOKEN/sendMessage" in mock_post.call_args[0][0]
        assert call_kwargs["json"]["chat_id"] == "998877"
        assert "PRICE DROP DETECTED!" in call_kwargs["json"]["text"]


@pytest.mark.asyncio
async def test_slack_alert_success():
    """Test successful Slack webhook dispatch."""
    service = AlertService()
    sample_data = {
        "alert_type": "price_drop",
        "product_name": "Nike Air Zoom",
        "product_url": "https://example.com/nike",
        "currency": "USD",
        "old_price": 150.00,
        "new_price": 120.00,
        "drop_pct": 20.0,
        "image_url": "https://example.com/nike.jpg"
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        ok, msg = await service.send_slack_alert("https://hooks.slack.com/services/T00/B00/X00", sample_data)
        assert ok is True
        assert "successfully" in msg
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args[1]
        assert "blocks" in call_kwargs["json"]
        assert "-20.0% Off" in call_kwargs["json"]["blocks"][0]["text"]["text"]


@pytest.mark.asyncio
async def test_discord_alert_success():
    """Test successful Discord embed webhook dispatch."""
    service = AlertService()
    sample_data = {
        "alert_type": "price_drop",
        "product_name": "Dell XPS 15",
        "product_url": "https://example.com/dell",
        "currency": "USD",
        "old_price": 1800.00,
        "new_price": 1500.00,
        "drop_pct": 16.67
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 204

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        ok, msg = await service.send_discord_alert("https://discord.com/api/webhooks/123/abc", sample_data)
        assert ok is True
        assert "successfully" in msg
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args[1]
        assert "embeds" in call_kwargs["json"]
        embed = call_kwargs["json"]["embeds"][0]
        assert "Price Drop Alert" in embed["title"]
        assert embed["color"] == 0x10B981


@pytest.mark.asyncio
async def test_generic_webhook_alert():
    """Test generic webhook dispatch."""
    service = AlertService()
    sample_data = {
        "alert_type": "price_drop",
        "product_name": "Test Item",
        "old_price": 50.0,
        "new_price": 40.0
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        ok, msg = await service.send_generic_webhook_alert("https://webhook.site/abc-123", sample_data)
        assert ok is True
        assert "successfully" in msg
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["json"]["event"] == "ecommerce_alert"


@pytest.mark.asyncio
async def test_channel_test_trigger():
    """Test test_channel method for telegram with invalid creds."""
    service = AlertService()
    ok, err = await service.test_channel("telegram", {})
    assert ok is False
    assert "Telegram requires" in err

    ok2, err2 = await service.test_channel("slack", {})
    assert ok2 is False
    assert "Slack requires" in err2


@pytest.mark.asyncio
async def test_process_price_change_filtering():
    """Test process_price_change respects min_drop_percentage."""
    service = AlertService()

    # If drop is below min_drop_percentage, nothing should be dispatched
    cfg = AlertConfig(
        id=1,
        channel="telegram",
        name="Telegram Channel",
        credentials=json.dumps({"bot_token": "token", "chat_id": "123"}),
        is_active=True,
        min_drop_percentage=15.0  # requires >= 15% drop
    )

    mock_session = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = [cfg]
    mock_session.execute = AsyncMock(return_value=mock_res)

    with patch("app.services.alert_service.AlertService.send_telegram_alert", new_callable=AsyncMock) as mock_tele:
        mock_tele.return_value = (True, "sent")

        # 10% drop < 15% threshold -> should NOT dispatch
        await service.process_price_change(
            db=mock_session,
            product_id=10,
            product_name="Gadget",
            product_url="https://example.com/gadget",
            old_price=100.0,
            new_price=90.0,
            currency="USD"
        )
        mock_tele.assert_not_called()

        # 20% drop >= 15% threshold -> SHOULD dispatch
        await service.process_price_change(
            db=mock_session,
            product_id=10,
            product_name="Gadget",
            product_url="https://example.com/gadget",
            old_price=100.0,
            new_price=80.0,
            currency="USD"
        )
        mock_tele.assert_called_once()


@pytest.mark.asyncio
async def test_webhook_hmac_signature_dispatch():
    """Verify HMAC-SHA256 signature generation and outbound header injection."""
    service = AlertService()
    secret = "my_super_secret_webhook_key_456"
    sample_data = {
        "alert_type": "buybox_lost",
        "product_name": "Logitech MX Master 3S",
        "store_domain": "amazon.com",
        "winner_price": 89.99,
        "target_winning_price": 88.00,
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        ok, msg = await service.send_generic_webhook_alert(
            webhook_url="https://api.myapp.com/webhooks/pricing",
            alert_data=sample_data,
            hmac_secret=secret,
        )
        assert ok is True
        mock_post.assert_called_once()
        headers = mock_post.call_args[1]["headers"]
        assert "X-Scraper-Signature" in headers
        assert headers["X-Scraper-Signature"].startswith("sha256=")
        assert headers["X-Scraper-Event"] == "buybox_lost"


@pytest.mark.asyncio
async def test_multistore_and_event_subscription_filtering():
    """Verify event and domain filtering across multi-store configurations."""
    service = AlertService()
    cfg_amazon_buybox = AlertConfig(
        id=1,
        channel="slack",
        name="Amazon Buy Box Slack Alerts",
        credentials=json.dumps({"webhook_url": "https://hooks.slack.com/services/T/B/X"}),
        is_active=True,
        events_subscribed=json.dumps(["buybox_lost", "buybox_won"]),
        store_domains=json.dumps(["amazon.com"]),
    )

    # 1. Matching event and domain -> eligible
    assert service._is_config_eligible(cfg_amazon_buybox, "buybox_lost", "amazon.com") is True

    # 2. Matching event but different domain -> NOT eligible
    assert service._is_config_eligible(cfg_amazon_buybox, "buybox_lost", "walmart.com") is False

    # 3. Same domain but unsubscribed event (price_drop) -> NOT eligible
    assert service._is_config_eligible(cfg_amazon_buybox, "price_drop", "amazon.com") is False


@pytest.mark.asyncio
async def test_simulate_webhook_route():
    """Test POST /api/v1/alerts/simulate-webhook."""
    from httpx import AsyncClient
    from app.main import app

    async with AsyncClient(app=app, base_url="http://test") as ac:
        res = await ac.post("/api/v1/alerts/simulate-webhook", json={
            "event_type": "buybox_lost",
            "hmac_secret": "test_secret_abc",
            "store_domain": "amazon.com",
        })
        assert res.status_code == 200
        data = res.json()
        assert data["event"] == "buybox_lost"
        assert "X-Scraper-Signature" in data["headers"]
        assert data["headers"]["X-Scraper-Signature"].startswith("sha256=")

