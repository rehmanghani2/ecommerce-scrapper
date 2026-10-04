"""
Unit tests for Sitemap XML parser and Bulk URL / File importer service.
"""

import gzip
import pytest
from app.core.sitemap_parser import SitemapParser, sitemap_parser
from app.services.bulk_importer_service import BulkImporterService, bulk_importer_service
from app.core.bulk_batch_scraper import BulkBatchScraper


SAMPLE_SITEMAP_XML = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
        xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">
  <url>
    <loc>https://example.com/products/leather-jacket</loc>
    <lastmod>2026-10-01T12:00:00Z</lastmod>
    <priority>0.9</priority>
    <image:image>
      <image:loc>https://example.com/images/jacket.jpg</image:loc>
    </image:image>
  </url>
  <url>
    <loc>https://example.com/products/running-shoes</loc>
    <lastmod>2026-10-02T12:00:00Z</lastmod>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>https://example.com/blog/autumn-fashion</loc>
    <lastmod>2026-09-01T10:00:00Z</lastmod>
    <priority>0.3</priority>
  </url>
</urlset>
"""

SAMPLE_SITEMAP_INDEX_XML = """<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <sitemap>
    <loc>https://example.com/sitemap_products_1.xml</loc>
    <lastmod>2026-10-01</lastmod>
  </sitemap>
  <sitemap>
    <loc>https://example.com/sitemap_pages.xml</loc>
    <lastmod>2026-10-01</lastmod>
  </sitemap>
</sitemapindex>
"""


def test_parse_standard_sitemap_xml():
    parser = SitemapParser()
    res = parser.parse_xml_content(SAMPLE_SITEMAP_XML.encode("utf-8"))
    assert res["is_index"] is False
    assert len(res["entries"]) == 3
    urls = [e["loc"] for e in res["entries"]]
    assert "https://example.com/products/leather-jacket" in urls
    assert "https://example.com/products/running-shoes" in urls
    # Image check
    jacket_entry = next(e for e in res["entries"] if "leather-jacket" in e["loc"])
    assert jacket_entry["image"] == "https://example.com/images/jacket.jpg"


def test_parse_gzip_compressed_sitemap():
    parser = SitemapParser()
    compressed = gzip.compress(SAMPLE_SITEMAP_XML.encode("utf-8"))
    res = parser.parse_xml_content(compressed, url="https://example.com/sitemap.xml.gz")
    assert res["is_index"] is False
    assert len(res["entries"]) == 3


def test_parse_sitemap_index():
    parser = SitemapParser()
    res = parser.parse_xml_content(SAMPLE_SITEMAP_INDEX_XML.encode("utf-8"))
    assert res["is_index"] is True
    assert len(res["sitemaps"]) == 2
    assert "https://example.com/sitemap_products_1.xml" in res["sitemaps"]


def test_is_likely_product_url():
    parser = SitemapParser()
    assert parser.is_likely_product_url("https://example.com/products/sony-wh1000xm5") is True
    assert parser.is_likely_product_url("https://example.com/item/12345") is True
    assert parser.is_likely_product_url("https://example.com/p/nike-air-max") is True
    # Non-products should be False
    assert parser.is_likely_product_url("https://example.com/collections/summer-sale") is False
    assert parser.is_likely_product_url("https://example.com/blog/tech-news") is False
    assert parser.is_likely_product_url("https://example.com/cart") is False


def test_bulk_importer_csv_with_headers():
    service = BulkImporterService()
    csv_text = """product_name,url,price,sku
Leather Jacket,https://example.com/products/jacket,199.99,SKU-001
Running Shoes,https://example.com/products/shoes,89.50,SKU-002
Wireless Earbuds,https://example.com/products/earbuds,49.00,SKU-003
"""
    parsed = service.parse_csv_or_tsv(csv_text)
    assert parsed["success"] is True
    assert parsed["has_header"] is True
    assert parsed["valid_urls_count"] == 3
    assert len(parsed["urls"]) == 3
    assert parsed["urls"][0] == "https://example.com/products/jacket"
    assert parsed["items"][0]["name"] == "Leather Jacket"
    assert parsed["items"][0]["price"] == "199.99"


def test_bulk_importer_tsv():
    service = BulkImporterService()
    tsv_text = "Name\tLink\tPrice\nItem 1\thttps://example.com/item-1\t10\nItem 2\thttps://example.com/item-2\t20"
    parsed = service.parse_csv_or_tsv(tsv_text)
    assert parsed["success"] is True
    assert parsed["valid_urls_count"] == 2
    assert "https://example.com/item-1" in parsed["urls"]


def test_bulk_importer_raw_text():
    service = BulkImporterService()
    raw = """
    Check out these competitors:
    https://site.com/products/p1, and also https://site.com/products/p2;
    plus: https://site.com/products/p3.
    """
    parsed = service.parse_raw_text(raw)
    assert parsed["success"] is True
    assert parsed["total_found"] == 3
    assert parsed["urls"] == [
        "https://site.com/products/p1",
        "https://site.com/products/p2",
        "https://site.com/products/p3"
    ]


def test_bulk_batch_scraper_extract_product_page():
    scraper = BulkBatchScraper(job_id=99, urls=["https://example.com/item"])
    html_sample = """
    <html>
      <head><title>Super Wireless Headphones | Best Audio Store</title></head>
      <body>
        <h1 class="product-title">Super Wireless Headphones</h1>
        <div class="current-price">$149.99</div>
        <img class="product-image" src="/images/headphones.jpg" />
      </body>
    </html>
    """
    products = scraper.extract_from_product_page(
        html=html_sample,
        page_url="https://example.com/item",
        selectors={"product_container": ".non-existent"}
    )
    assert len(products) == 1
    p = products[0]
    assert p["name"] == "Super Wireless Headphones"
    assert p["price"] == 149.99
    assert p["price_text"] == "$149.99"
    assert p["image_url"] == "https://example.com/images/headphones.jpg"
