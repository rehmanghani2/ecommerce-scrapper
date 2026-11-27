def test_extracts_nested_jsonld_and_product_image_gallery():
    html = """
    <script type="application/ld+json">
    {
      "@context": "https://schema.org",
      "@type": "WebPage",
      "mainEntity": {
        "@type": "Product",
        "name": "Touring Bike",
        "sku": "TB-500",
        "image": ["/img/front.jpg", {"url": "/img/side.jpg"}],
        "offers": {
          "@type": "Offer",
          "price": "1,249.95",
          "priceCurrency": "GBP",
          "availability": "https://schema.org/InStock"
        }
      }
    }
    </script>
    """
    products = ProductExtractor().extract(html, "https://shop.example/bikes/touring")

    assert len(products) == 1
    product = products[0]
    assert product["name"] == "Touring Bike"
    assert product["price"] == "1249.95"
    assert product["currency"] == "GBP"
    assert product["in_stock"] is True
    assert product["images"] == [
        "https://shop.example/img/front.jpg",
        "https://shop.example/img/side.jpg",
    ]


def test_extracts_currency_availability_and_lazy_image_from_card():
    html = """
    <div class="product-card" data-product="123">
      <h2 class="product-title">Helmet</h2>
      <span class="price">€89,50</span>
      <a href="/products/helmet">
        <img data-src="/images/helmet.webp" alt="Helmet">
        <img src="/images/helmet-side.webp" alt="Helmet side">
      </a>
      <span itemprop="availability">Out of stock</span>
    </div>
    """
    products = ProductExtractor().extract(html, "https://shop.example/catalog")

    assert len(products) == 1
    product = products[0]
    assert product["name"] == "Helmet"
    assert product["currency"] == "EUR"
    assert product["url"] == "https://shop.example/products/helmet"
    assert product["image_url"] == "https://shop.example/images/helmet.webp"
    assert len(product["images"]) == 2


def test_deduplicates_product_cards_by_sku():
    html = """
    <div class="product-card">
      <h2 class="product-title">Same Product</h2>
      <span class="price">£10.00</span>
      <span itemprop="sku" content="SKU-1"></span>
      <a href="/products/one">One</a>
    </div>
    <div class="product-card">
      <h2 class="product-title">Same Product</h2>
      <span class="price">£10.00</span>
      <span itemprop="sku" content="SKU-1"></span>
      <a href="/products/one?variant=2">Two</a>
    </div>
    """
    products = ProductExtractor().extract(html, "https://shop.example/catalog")
    assert len(products) == 1
