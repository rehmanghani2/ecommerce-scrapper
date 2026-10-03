import pytest
from app.scrapers.scraper_registry import ScraperRegistry, detect_platform, get_scraper
from app.scrapers.bigcommerce_scraper import BigCommerceScraper
from app.scrapers.magento_scraper import MagentoScraper
from app.schemas.scraper_schema import ScraperConfig
from app.core.httpx_scraper import PLATFORM_SELECTORS

def test_registry_includes_platforms():
    platforms = ScraperRegistry.list_platforms()
    assert "bigcommerce" in platforms
    assert "magento" in platforms
    assert "shopify" in platforms
    assert "woocommerce" in platforms
    assert "generic" in platforms

def test_platform_detection():
    assert detect_platform("https://store.mybigcommerce.com/products") == "bigcommerce"
    assert detect_platform("https://demo.magento.com/gear") == "magento"
    assert detect_platform("https://test.myshopify.com") == "shopify"

def test_scraper_instantiation():
    config = ScraperConfig(start_url="https://store.mybigcommerce.com")
    bc_scraper = get_scraper("bigcommerce", config)
    assert isinstance(bc_scraper, BigCommerceScraper)
    assert bc_scraper.PLATFORM_NAME == "bigcommerce"

    mg_scraper = get_scraper("magento", config)
    assert isinstance(mg_scraper, MagentoScraper)
    assert mg_scraper.PLATFORM_NAME == "magento"

def test_httpx_selectors_configured():
    assert "bigcommerce" in PLATFORM_SELECTORS
    assert "magento" in PLATFORM_SELECTORS
    assert "product_container" in PLATFORM_SELECTORS["bigcommerce"]
    assert "product_container" in PLATFORM_SELECTORS["magento"]
