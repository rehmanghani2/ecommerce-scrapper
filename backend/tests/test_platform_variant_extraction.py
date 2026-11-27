from app.core.product_extractor import ProductExtractor


def test_extracts_shopify_product_json_variants_and_images():
    html = """
    <nav aria-label="Breadcrumb">
      <ol><li><a>Home</a></li><li><a>Clothing</a></li><li><span>Jackets</span></li></ol>
    </nav>
    <script type="application/json" id="ProductJson-product-template">
    {
      "id": 123,
      "title": "Outdoor Jacket",
      "handle": "outdoor-jacket",
      "vendor": "Northwind",
      "product_type": "Jackets",
      "tags": ["waterproof", "outdoor"],
      "options": ["Size", "Colour"],
      "images": [{"src": "//cdn.example/jacket-front.jpg"}, {"src": "//cdn.example/jacket-back.jpg"}],
      "variants": [
        {"id": 1001, "title": "Small / Blue", "public_title": "Small / Blue", "sku": "JKT-S-B", "price": "89.95", "compare_at_price": "109.95", "available": true, "inventory_quantity": 4, "option1": "Small", "option2": "Blue"},
        {"id": 1002, "title": "Medium / Blue", "public_title": "Medium / Blue", "sku": "JKT-M-B", "price": "89.95", "available": false, "option1": "Medium", "option2": "Blue"}
      ]
    }
    </script>
    """
    products = ProductExtractor().extract(html, "https://shop.example/products/outdoor-jacket")

    assert len(products) == 1
    product = products[0]
    assert product["platform"] == "shopify"
    assert product["name"] == "Outdoor Jacket"
    assert product["brand"] == "Northwind"
    assert product["category_path"] == "Clothing > Jackets"
    assert product["tags"] == ["waterproof", "outdoor"]
    assert len(product["images"]) == 2
    assert len(product["variants"]) == 2
    assert product["variants"][0]["attributes"] == {"Size": "Small", "Colour": "Blue"}
    assert product["variants"][0]["original_price"] == "109.95"
    assert product["variants"][0]["stock_quantity"] == 4
    assert product["variants"][1]["in_stock"] is False


def test_extracts_woocommerce_variation_form_payload():
    html = """
    <nav class="woocommerce-breadcrumb">
      <a>Home</a><a>Cycles</a><a>Helmets</a>
    </nav>
    <h1 class="product_title">Road Helmet</h1>
    <p class="price"><span class="woocommerce-Price-amount">£79.99</span></p>
    <span class="sku">HELMET-BASE</span>
    <div class="woocommerce-product-gallery__image">
      <img class="wp-post-image" src="/images/helmet.jpg">
    </div>
    <form class="variations_form" data-product_variations='[
      {"variation_id": 501, "sku": "HELMET-BLK-M", "display_price": 79.99, "display_regular_price": 99.99, "is_in_stock": true, "max_qty": 8, "attributes": {"attribute_pa_colour": "black", "attribute_pa_size": "medium"}, "image": {"src": "/images/helmet-black.jpg"}},
      {"variation_id": 502, "sku": "HELMET-WHT-L", "display_price": 84.99, "display_regular_price": 99.99, "is_in_stock": false, "attributes": {"attribute_pa_colour": "white", "attribute_pa_size": "large"}, "image": {"src": "/images/helmet-white.jpg"}}
    ]'></form>
    """
    products = ProductExtractor().extract(html, "https://shop.example/product/road-helmet/")

    assert len(products) == 1
    product = products[0]
    assert product["platform"] == "woocommerce"
    assert product["name"] == "Road Helmet"
    assert product["category_path"] == "Cycles > Helmets"
    assert len(product["variants"]) == 2
    assert product["variants"][0]["sku"] == "HELMET-BLK-M"
    assert product["variants"][0]["price"] == "79.99"
    assert product["variants"][0]["original_price"] == "99.99"
    assert product["variants"][0]["attributes"] == {"Colour": "black", "Size": "medium"}
    assert product["variants"][1]["in_stock"] is False
