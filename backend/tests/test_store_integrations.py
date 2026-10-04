import pytest
from app.services.store_integration_service import store_integration_service
from app.models.product import Product
from app.models.integration import IntegrationConfig, SyncLog
from app.api.routes.integrations import _mask_credentials


def test_url_cleaners():
    # Shopify URL cleaner
    assert store_integration_service._clean_shopify_url("my-store.myshopify.com") == "my-store.myshopify.com"
    assert store_integration_service._clean_shopify_url("https://my-store.myshopify.com/") == "my-store.myshopify.com"
    assert store_integration_service._clean_shopify_url("my-store") == "my-store.myshopify.com"

    # WooCommerce URL cleaner
    assert store_integration_service._clean_wc_url("example.com") == "https://example.com"
    assert store_integration_service._clean_wc_url("https://example.com/") == "https://example.com"


def test_mask_credentials():
    creds = {
        "shop_url": "shop.myshopify.com",
        "access_token": "shpat_1234567890abcdef",
        "consumer_secret": "cs_abcdef123456",
    }
    masked = _mask_credentials("shopify", creds)
    assert masked["shop_url"] == "shop.myshopify.com"
    assert masked["access_token"].startswith("shpa****")
    assert masked["access_token"].endswith("cdef")
    assert masked["consumer_secret"].startswith("cs_a****")


def test_generate_shopify_csv():
    p1 = Product(
        id=1,
        name="Wireless Noise-Canceling Headphones",
        description="Great sound quality",
        price=199.99,
        previous_price=249.99,
        currency="USD",
        in_stock=True,
        sku="WNC-01",
        brand="Sony",
        category="Electronics",
        url="https://amazon.com/dp/B123",
        image_url="https://images.example.com/item.jpg",
        source_domain="amazon.com"
    )
    csv_str = store_integration_service.generate_shopify_csv([p1])
    assert "Handle,Title,Body (HTML),Vendor" in csv_str
    assert "Wireless Noise-Canceling Headphones" in csv_str
    assert "199.99" in csv_str
    assert "249.99" in csv_str  # compare at price
    assert "Sony" in csv_str


def test_generate_woocommerce_csv():
    p1 = Product(
        id=2,
        name="Running Shoes",
        description="Comfortable cushioned soles",
        price=89.0,
        currency="USD",
        in_stock=True,
        sku="RUN-02",
        brand="Nike",
        category="Footwear",
        url="https://nike.com/running",
        image_url="https://images.example.com/shoes.jpg",
        source_domain="nike.com"
    )
    csv_str = store_integration_service.generate_woocommerce_csv([p1])
    assert "ID,Type,SKU,Name,Published" in csv_str
    assert "Running Shoes" in csv_str
    assert "89.00" in csv_str
    assert "Nike" in csv_str


def test_generate_google_sheets_csv():
    p1 = Product(
        id=3,
        name="Organic Coffee Beans",
        price=15.5,
        previous_price=18.0,
        price_change=-2.5,
        price_change_percentage=-13.88,
        currency="USD",
        in_stock=True,
        brand="Blue Bottle",
        category="Coffee",
        source_domain="bluebottlecoffee.com"
    )
    csv_str = store_integration_service.generate_google_sheets_csv([p1])
    assert "Product Name,Price,Previous Price,Price Change (%),Currency" in csv_str
    assert "Organic Coffee Beans" in csv_str
    assert "15.50" in csv_str
    assert "-13.9%" in csv_str


def test_integration_models():
    config = IntegrationConfig(
        platform="shopify",
        name="My US Store",
        credentials='{"shop_url": "test.myshopify.com"}',
        is_active=True
    )
    assert config.platform == "shopify"
    assert config.name == "My US Store"

    log = SyncLog(
        platform="shopify",
        target_name="test.myshopify.com",
        items_count=10,
        success_count=10,
        failed_count=0,
        status="success"
    )
    assert log.items_count == 10
    assert log.status == "success"
