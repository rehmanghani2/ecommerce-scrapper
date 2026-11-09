"""Unit tests for safe URL and pagination helpers used by website discovery."""

import socket

from app.api.routes import scraper


def test_public_target_rejects_non_http_and_local_hosts():
    assert not scraper._is_public_target("file:///etc/passwd")
    assert not scraper._is_public_target("http://localhost/")
    assert not scraper._is_public_target("http://127.0.0.1/")
    assert not scraper._is_public_target("http://service.local/")


def test_public_target_rejects_private_dns_answers(monkeypatch):
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *args, **kwargs: [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.5", 443))
        ],
    )
    assert not scraper._is_public_target("https://shop.example/")


def test_public_target_accepts_global_dns_answers(monkeypatch):
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *args, **kwargs: [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))
        ],
    )
    assert scraper._is_public_target("https://shop.example/")


def test_pagination_detects_query_parameters():
    assert scraper._is_pagination_candidate("https://shop.example/category?page=2")


def test_pagination_detects_path_rel_and_labels():
    assert scraper._is_pagination_candidate("https://shop.example/category/page/2")
    assert scraper._is_pagination_candidate("https://shop.example/category", rel="next")
    assert scraper._is_pagination_candidate("https://shop.example/category", label="Next page")


def test_pagination_does_not_classify_product_urls_as_next_pages():
    assert not scraper._is_pagination_candidate(
        "https://shop.example/products/road-bike",
        label="Road bike",
    )
