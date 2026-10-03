import pytest
from app.scrapers.scraper_registry import (
    ScraperRegistry,
    detect_platform,
    detect_platform_detailed,
    get_scraper
)
from app.scrapers.bigcommerce_scraper import BigCommerceScraper
from app.scrapers.magento_scraper import MagentoScraper
from app.scrapers.squarespace_scraper import SquarespaceScraper
from app.scrapers.wix_scraper import WixScraper
from app.scrapers.etsy_scraper import EtsyScraper
from app.scrapers.walmart_scraper import WalmartScraper
from app.schemas.scraper_schema import ScraperConfig
from app.core.httpx_scraper import PLATFORM_SELECTORS
from app.core.pattern_detector import PatternDetector

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

def test_platform_detection_domain():
    assert detect_platform("https://store.mybigcommerce.com/products") == "bigcommerce"
    assert detect_platform("https://demo.magento.com/gear") == "magento"
    assert detect_platform("https://test.myshopify.com") == "shopify"
    assert detect_platform("https://studio.squarespace.com/shop") == "squarespace"
    assert detect_platform("https://mybrand.wixsite.com/store") == "wix"
    assert detect_platform("https://www.etsy.com/c/vintage") == "etsy"
    assert detect_platform("https://www.walmart.com/browse/electronics") == "walmart"

def test_platform_detection_meta_generator():
    # Independent store with custom domain (e.g. bakery.com) but WooCommerce meta generator
    woo_html = '<!DOCTYPE html><html><head><meta name="generator" content="WooCommerce 8.5.2" /></head></html>'
    assert detect_platform("https://bakery.com/shop", html=woo_html) == "woocommerce"

    # Shopify store on custom domain with reversed attribute order
    shopify_html = '<html><head><meta content="Shopify" name="generator"></head></html>'
    assert detect_platform("https://modernapparel.com", html=shopify_html) == "shopify"

    # BigCommerce on custom domain
    bc_html = '<html><head><meta name="generator" content="BigCommerce" /></head></html>'
    assert detect_platform("https://outdoorshop.com", html=bc_html) == "bigcommerce"

    # Squarespace on custom domain
    sq_html = '<html><head><meta name="generator" content="Squarespace" /></head></html>'
    assert detect_platform("https://photostudio.com", html=sq_html) == "squarespace"

    # Wix on custom domain
    wix_html = '<html><head><meta name="generator" content="Wix.com Website Builder" /></head></html>'
    assert detect_platform("https://artgallery.com", html=wix_html) == "wix"

def test_platform_detection_headers():
    # Header detection on custom domains
    shopify_headers = {"X-Shopify-Stage": "production", "Content-Type": "text/html"}
    assert detect_platform("https://customstore.com", headers=shopify_headers) == "shopify"

    magento_headers = {"X-Magento-Tags": "store,cms_p_1", "Server": "nginx"}
    assert detect_platform("https://customauto.com", headers=magento_headers) == "magento"

    wix_headers = {"X-Wix-Renderer-Server": "app-runner-4"}
    assert detect_platform("https://customportfolio.com", headers=wix_headers) == "wix"

def test_platform_detection_html_signatures():
    # Custom domain with Shopify CDN script
    shopify_script_html = '<html><head><script src="https://cdn.shopify.com/s/files/1/theme.js"></script></head></html>'
    assert detect_platform("https://shoesbrand.com", html=shopify_script_html) == "shopify"

    # Custom domain with WooCommerce plugin path
    woo_script_html = '<html><body><link rel="stylesheet" href="/wp-content/plugins/woocommerce/assets/css/style.css"></body></html>'
    assert detect_platform("https://florist.com", html=woo_script_html) == "woocommerce"

def test_pattern_detector_class():
    detector = PatternDetector()
    res = detect_platform_detailed("https://customstore.com", html='<meta name="generator" content="BigCommerce">')
    assert res["platform"] == "bigcommerce"
    assert res["confidence"] >= 0.9
    assert res["method"] == "meta_generator"

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
