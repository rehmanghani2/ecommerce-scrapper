import pytest
from app.scrapers.scraper_registry import ScraperRegistry, detect_platform, get_scraper
from app.scrapers.bigcommerce_scraper import BigCommerceScraper
from app.scrapers.magento_scraper import MagentoScraper
from app.scrapers.squarespace_scraper import SquarespaceScraper
from app.scrapers.wix_scraper import WixScraper
from app.scrapers.etsy_scraper import EtsyScraper
from app.scrapers.walmart_scraper import WalmartScraper
from app.schemas.scraper_schema import ScraperConfig
from app.core.httpx_scraper import PLATFORM_SELECTORS

def test_registry_includes_platforms():
    platforms = ScraperRegistry.list_platforms()
    assert "bigcommerce" in platforms
    assert "magento" in platforms
    assert "shopify" in platforms
    assert "woocommerce" in platforms
    assert "squarespace" in platforms
    assert "wix" in platforms
    assert "etsy" in platforms
    assert "walmart" in platforms
    assert "generic" in platforms

def test_platform_detection():
    assert detect_platform("https://store.mybigcommerce.com/products") == "bigcommerce"
    assert detect_platform("https://demo.magento.com/gear") == "magento"
    assert detect_platform("https://test.myshopify.com") == "shopify"
    assert detect_platform("https://studio.squarespace.com/shop") == "squarespace"
    assert detect_platform("https://mybrand.wixsite.com/store") == "wix"
    assert detect_platform("https://www.etsy.com/c/vintage") == "etsy"
    assert detect_platform("https://www.walmart.com/browse/electronics") == "walmart"

def test_scraper_instantiation():
    config = ScraperConfig(start_url="https://store.mybigcommerce.com")
    bc_scraper = get_scraper("bigcommerce", config)
    assert isinstance(bc_scraper, BigCommerceScraper)
    assert bc_scraper.PLATFORM_NAME == "bigcommerce"

    mg_scraper = get_scraper("magento", config)
    assert isinstance(mg_scraper, MagentoScraper)
    assert mg_scraper.PLATFORM_NAME == "magento"

    sq_scraper = get_scraper("squarespace", config)
    assert isinstance(sq_scraper, SquarespaceScraper)
    assert sq_scraper.PLATFORM_NAME == "squarespace"

    wix_scraper = get_scraper("wix", config)
    assert isinstance(wix_scraper, WixScraper)
    assert wix_scraper.PLATFORM_NAME == "wix"

    etsy_scraper = get_scraper("etsy", config)
    assert isinstance(etsy_scraper, EtsyScraper)
    assert etsy_scraper.PLATFORM_NAME == "etsy"

    walmart_scraper = get_scraper("walmart", config)
    assert isinstance(walmart_scraper, WalmartScraper)
    assert walmart_scraper.PLATFORM_NAME == "walmart"

def test_httpx_selectors_configured():
    assert "bigcommerce" in PLATFORM_SELECTORS
    assert "magento" in PLATFORM_SELECTORS
    assert "squarespace" in PLATFORM_SELECTORS
    assert "wix" in PLATFORM_SELECTORS
    assert "etsy" in PLATFORM_SELECTORS
    assert "walmart" in PLATFORM_SELECTORS
    assert "product_container" in PLATFORM_SELECTORS["etsy"]
    assert "product_container" in PLATFORM_SELECTORS["walmart"]
