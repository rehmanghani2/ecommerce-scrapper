from app.scrapers.site_adapters import get_site_adapter, list_site_adapters
from app.core.product_extractor import ProductExtractor


def test_initial_uk_storefront_profiles_match_only_their_hosts():
    urls = [
        "https://leelicycles.co.uk/",
        "https://www.ballicom.co.uk/",
        "https://store.exertis.co.uk/",
        "https://uk.rs-online.com/web/",
    ]
    assert [get_site_adapter(url).key for url in urls] == [
        "leeli-cycles", "ballicom", "exertis-store", "rs-components"
    ]
    assert get_site_adapter("https://notballicom.co.uk/") is None
    assert get_site_adapter("https://example.com/?next=leelicycles.co.uk") is None


def test_profiles_include_listing_pagination_and_category_hints():
    for adapter in list_site_adapters():
        assert adapter.selector_config["product_container"]
        assert adapter.selector_config["fields"]["name"]
        assert adapter.pagination_selectors
        assert adapter.category_selectors


def test_product_extractor_uses_matching_site_profile():
    html = """
    <ul>
      <li class="product-card">
        <h2 class="product-title">Trail Bike</h2>
        <span class="price">£799.00</span>
        <a class="product-link" href="/products/trail-bike">
          <img src="/images/trail-bike.jpg" alt="Trail Bike">
        </a>
      </li>
    </ul>
    """
    products = ProductExtractor().extract(html, "https://leelicycles.co.uk/category/bikes")
    assert len(products) == 1
    assert products[0]["name"] == "Trail Bike"
    assert products[0]["price"] == "799.00"
    assert products[0]["currency"] == "GBP"
    assert products[0]["url"] == "https://leelicycles.co.uk/products/trail-bike"


def test_ballicom_profile_covers_published_product_catalogue_routes():
    ballicom = get_site_adapter("https://www.ballicom.co.uk/")
    selectors = set(ballicom.category_selectors)
    for path in ("all-products", "hardware", "office-supplies", "software", "electronics", "furniture", "facilities"):
        assert "a[href*='/" + path + "/']" in selectors
