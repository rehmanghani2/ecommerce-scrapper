from app.core.product_extractor import ProductExtractor


def test_extracts_product_cards_and_normalizes_relative_urls():
    html = """
    <div class="product-card">
      <h2 class="product-title">Road Bike</h2>
      <span class="price">£1,299.00</span>
      <a href="/products/road-bike"><img src="/images/bike.jpg" /></a>
    </div>
    """
    products = ProductExtractor().extract(html, "https://shop.example/category/bikes")

    assert len(products) == 1
    assert products[0]["name"] == "Road Bike"
    assert products[0]["price"] == "1299.00"
    assert products[0]["url"] == "https://shop.example/products/road-bike"
    assert products[0]["image_url"] == "https://shop.example/images/bike.jpg"


def test_extracts_product_from_jsonld_graph():
    html = """
    <script type="application/ld+json">
    {
      "@context": "https://schema.org",
      "@graph": [{
        "@type": "Product",
        "name": "City E-bike",
        "sku": "EB-100",
        "image": ["/assets/ebike.jpg"],
        "offers": {
          "@type": "Offer",
          "price": "899.99",
          "priceCurrency": "GBP",
          "availability": "https://schema.org/InStock",
          "url": "/products/city-ebike"
        }
      }]
    }
    </script>
    """
    products = ProductExtractor().extract(html, "https://shop.example")

    assert len(products) == 1
    assert products[0]["name"] == "City E-bike"
    assert products[0]["price"] == "899.99"
    assert products[0]["currency"] == "GBP"
    assert products[0]["sku"] == "EB-100"
    assert products[0]["url"] == "https://shop.example/products/city-ebike"
    assert products[0]["image_url"] == "https://shop.example/assets/ebike.jpg"


def test_extracts_product_detail_from_open_graph_metadata():
    html = """
    <html><head>
      <meta property="og:title" content="Helmet Pro">
      <meta property="product:price:amount" content="49.95">
      <meta property="og:image" content="/helmet.jpg">
    </head></html>
    """
    products = ProductExtractor().extract(html, "https://shop.example/p/helmet")

    assert len(products) == 1
    assert products[0]["name"] == "Helmet Pro"
    assert products[0]["price"] == "49.95"
    assert products[0]["image_url"] == "https://shop.example/helmet.jpg"
