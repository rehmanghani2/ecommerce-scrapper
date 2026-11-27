from app.scripts.live_store_smoke import (
    _absolute_same_host_links,
    _is_challenge,
    _normalise_host,
    _same_storefront,
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
    monkeypatch.setattr("app.scripts.live_store_smoke._is_public_http_url", lambda url: True)
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
