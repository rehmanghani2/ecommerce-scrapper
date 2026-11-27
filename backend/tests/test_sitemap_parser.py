import socket
import httpx
import pytest

from app.core.sitemap_parser import SitemapParser


def _public_dns(host, port, type=None):
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", port))]


def test_sitemap_url_rejects_private_and_credentialed_targets(monkeypatch):
    parser = SitemapParser()
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: [
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.5", 443))
    ])
    assert parser._is_public_http_url("https://shop.example/sitemap.xml") is False
    assert parser._is_public_http_url("https://user:pass@shop.example/sitemap.xml") is False


def test_sitemap_url_rejects_cross_host_and_non_http_targets(monkeypatch):
    parser = SitemapParser()
    monkeypatch.setattr(socket, "getaddrinfo", _public_dns)
    assert parser._is_public_http_url("https://cdn.example/sitemap.xml", "shop.example") is False
    assert parser._is_public_http_url("file:///etc/passwd", "shop.example") is False
    assert parser._is_public_http_url("https://shop.example/sitemap.xml", "shop.example") is True


@pytest.mark.asyncio
async def test_recursive_sitemap_traversal_keeps_same_host_urls_only(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", _public_dns)
    index_url = "https://shop.example/sitemap.xml"
    child_url = "https://shop.example/sitemap-products.xml"
    index_xml = b'''<?xml version="1.0" encoding="UTF-8"?>
    <sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
      <sitemap><loc>https://shop.example/sitemap-products.xml</loc></sitemap>
      <sitemap><loc>https://other.example/sitemap.xml</loc></sitemap>
    </sitemapindex>'''
    child_xml = b'''<?xml version="1.0" encoding="UTF-8"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
      <url><loc>https://shop.example/products/item-1</loc></url>
      <url><loc>https://other.example/products/secret</loc></url>
      <url><loc>javascript:alert(1)</loc></url>
    </urlset>'''

    class FakeResponse:
        def __init__(self, url, content):
            self.url = httpx.URL(url)
            self.status_code = 200
            self.content = content

    class FakeClient:
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            return False
        async def get(self, url):
            if url == index_url:
                return FakeResponse(url, index_xml)
            if url == child_url:
                return FakeResponse(url, child_xml)
            raise AssertionError("Unexpected URL requested: " + url)

    monkeypatch.setattr("app.core.sitemap_parser.httpx.AsyncClient", lambda **kwargs: FakeClient())
    result = await SitemapParser(max_depth=2, max_urls=20).fetch_and_parse(index_url)
    assert result["sitemaps_inspected"] == 2
    assert result["urls"] == ["https://shop.example/products/item-1"]


@pytest.mark.asyncio
async def test_sitemap_fetch_rejects_unsafe_initial_target(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: [
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443))
    ])
    with pytest.raises(ValueError, match="public HTTP"):
        await SitemapParser().fetch_and_parse("https://shop.example/sitemap.xml")
