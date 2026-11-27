from scripts.live_store_smoke import (
    _absolute_same_host_links,
    _is_challenge,
    _normalise_host,
    _same_storefront,
    _classify_readiness,
)
from app.scrapers.site_adapters import SITE_ADAPTERS


def test_host_normalization_and_storefront_allowlist():
    adapter = SITE_ADAPTERS[0]
    assert _normalise_host("WWW.LeeliCycles.co.uk.") == "leelicycles.co.uk"
    assert _same_storefront("https://www.leelicycles.co.uk/", adapter)
    assert not _same_storefront("https://leelicycles.co.uk.evil.test/", adapter)


def test_challenge_detection_does_not_attempt_to_solve():
    assert _is_challenge("Just a moment", "Checking your browser before accessing")
    assert not _is_challenge("Bikes", "Shop mountain bikes and accessories")


def test_link_filter_rejects_cross_host_and_duplicates(monkeypatch):
    adapter = SITE_ADAPTERS[0]
    monkeypatch.setattr("scripts.live_store_smoke._is_public_http_url", lambda url: True)
    links = _absolute_same_host_links(
        [
            "/collections/bikes",
            "https://www.leelicycles.co.uk/collections/bikes",
            "https://example.com/redirect",
            "javascript:alert(1)",
        ],
        "https://leelicycles.co.uk/",
        adapter,
    )
    assert links == ["https://leelicycles.co.uk/collections/bikes"]



def test_host_public_status_reports_all_resolved_addresses(monkeypatch):
    from scripts import live_store_smoke

    monkeypatch.setattr(
        live_store_smoke.socket,
        "getaddrinfo",
        lambda *args, **kwargs: [
            (2, 1, 6, "", ("93.184.216.34", 443)),
            (2, 1, 6, "", ("1.1.1.1", 443)),
        ],
    )
    live_store_smoke._host_public_status.cache_clear()
    is_public, addresses, error = live_store_smoke._host_public_status("example.test", 443)
    assert is_public is True
    assert addresses == ("1.1.1.1", "93.184.216.34")
    assert error is None


def test_host_public_status_rejects_any_non_public_dns_answer(monkeypatch):
    from scripts import live_store_smoke

    monkeypatch.setattr(
        live_store_smoke.socket,
        "getaddrinfo",
        lambda *args, **kwargs: [
            (2, 1, 6, "", ("93.184.216.34", 443)),
            (2, 1, 6, "", ("127.0.0.1", 443)),
        ],
    )
    live_store_smoke._host_public_status.cache_clear()
    is_public, addresses, error = live_store_smoke._host_public_status("mixed.test", 443)
    assert is_public is False
    assert "127.0.0.1" in error
    assert len(addresses) == 2


def test_robots_http_error_includes_status(monkeypatch):
    import urllib.error
    from scripts import live_store_smoke

    def raise_http_error(*args, **kwargs):
        raise urllib.error.HTTPError(
            "https://ballicom.co.uk/robots.txt", 403, "Forbidden", {}, None
        )

    monkeypatch.setattr(live_store_smoke.urllib.request, "urlopen", raise_http_error)
    allowed, message = live_store_smoke._robots_allows("https://ballicom.co.uk/")
    assert allowed is False
    assert "HTTP 403 Forbidden" in message


def test_leeli_category_selectors_include_non_navigation_collection_links():
    leeli = next(adapter for adapter in SITE_ADAPTERS if adapter.key == "leeli-cycles")
    assert "a[href*='/collections/']" in leeli.category_selectors
    assert "nav a[href*='/collections/']" not in leeli.category_selectors


def test_readiness_classifies_robots_denial():
    result = _classify_readiness({"robots": "robots.txt could not be checked: HTTP 403 Forbidden", "status": "skipped_robots"})
    assert result["outcome"] == "robots_check_blocked"
    assert result["product_extraction_verified"] is False


def test_readiness_distinguishes_dns_failure():
    result = _classify_readiness({"status": "blocked", "public_address_check": {"is_public": False, "error": "gaierror: Name or service not known"}})
    assert result["outcome"] == "dns_resolution_failed"


def test_readiness_does_not_treat_category_candidates_as_verified_products():
    result = _classify_readiness({"status": "completed", "robots": "allowed by robots.txt", "category_candidates": 213, "root_product_cards": 0, "category_pages": [{"loaded": False, "error": "HTTP 403"}]})
    assert result["outcome"] == "category_access_denied"
    assert result["product_extraction_verified"] is False


def test_readiness_requires_product_detail_record():
    result = _classify_readiness({"status": "completed", "robots": "allowed by robots.txt", "category_candidates": 2, "product_page": {"loaded": True, "extracted_records": 1}})
    assert result["outcome"] == "product_extraction_verified"
    assert result["product_extraction_verified"] is True
