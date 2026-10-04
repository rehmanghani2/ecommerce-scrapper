import pytest
import time
from unittest.mock import patch, AsyncMock
import httpx

from app.core.proxy_manager import ProxyNode, ProxyPoolManager, build_proxy_pool
from app.core.httpx_scraper import HttpxScraper


def test_proxy_node_parsing():
    raw = "http://myuser:mypassword@192.168.1.100:8080"
    node = ProxyNode(raw)
    assert node.scheme == "http"
    assert node.host_port == "192.168.1.100:8080"
    assert node.username == "myuser"
    assert node.password == "mypassword"
    assert node.to_httpx_proxy() == raw
    pw_dict = node.to_playwright_proxy()
    assert pw_dict["server"] == "http://192.168.1.100:8080"
    assert pw_dict["username"] == "myuser"
    assert pw_dict["password"] == "mypassword"
    # Password must be masked
    assert "mypassword" not in node.masked()
    assert "myuser:****@192.168.1.100:8080" in node.masked()


def test_proxy_pool_rotation_and_health():
    proxies = [
        "http://proxy1.com:8080",
        "http://proxy2.com:8080",
        "http://proxy3.com:8080"
    ]
    pool = ProxyPoolManager(proxies=proxies, cooldown_seconds=2)
    assert pool.total_proxies == 3

    # Round-robin checks
    p1 = pool.get_next_proxy()
    p2 = pool.get_next_proxy()
    p3 = pool.get_next_proxy()
    assert p1.raw_url == "http://proxy1.com:8080"
    assert p2.raw_url == "http://proxy2.com:8080"
    assert p3.raw_url == "http://proxy3.com:8080"

    # Simulate 403 block on proxy1
    cooled = pool.report_failure(p1, status_code=403)
    assert cooled is True
    assert p1.is_cooling is True
    assert p1.consecutive_failures == 1

    # Next proxy should skip proxy1 and pick proxy2 or proxy3
    next_p = pool.get_next_proxy()
    assert next_p.raw_url in ("http://proxy2.com:8080", "http://proxy3.com:8080")

    # Success report on proxy2
    pool.report_success(p2)
    assert p2.success_count == 1
    assert p2.consecutive_failures == 0

    status = pool.get_status_summary()
    assert status["total"] == 3
    assert status["cooling"] == 1
    assert status["healthy"] == 2


@pytest.mark.asyncio
async def test_httpx_scraper_auto_failover_on_403():
    """
    Test that HttpxScraper automatically fails over to the next proxy
    when receiving an HTTP 403 block, successfully scraping on attempt 2.
    """
    proxies = [
        "http://bad-blocked-proxy.com:8080",
        "http://good-clean-proxy.com:8080"
    ]
    pool = ProxyPoolManager(proxies=proxies, max_retries=2, cooldown_seconds=10)

    logs = []
    async def record_log(msg, lvl):
        logs.append(msg)

    scraper = HttpxScraper(
        job_id=999,
        start_url="https://books.toscrape.com",
        max_pages=1,
        proxy_pool=pool,
        on_log=record_log
    )

    # Mock response: 1st call gives 403 (blocked), 2nd call gives 200 (success)
    resp_403 = httpx.Response(403, request=httpx.Request("GET", "https://books.toscrape.com"))
    resp_200 = httpx.Response(
        200,
        text="<html><body><article class='product_pod'><h3><a href='book.html'>Test Book</a></h3><p class='price_color'>$19.99</p></article></body></html>",
        request=httpx.Request("GET", "https://books.toscrape.com")
    )

    call_count = 0
    async def mock_get(url):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return resp_403
        return resp_200

    with patch("httpx.AsyncClient.get", side_effect=mock_get):
        await scraper.run()

    # Verify that failover happened
    assert call_count == 2
    # Check that rotation log was written
    failover_logs = [l for l in logs if "Blocked (HTTP 403)" in l and "Auto-switching" in l]
    assert len(failover_logs) >= 1
    assert scraper._total_products == 1
