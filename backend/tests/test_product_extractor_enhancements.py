from app.core.product_extractor import ProductExtractor

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
    assert product["in_stock"] is False
    assert product["stock_status"] == "Out of Stock"


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



def test_extracts_jsonld_product_variants_without_emitting_them_as_products():
    html = """
    <script type="application/ld+json">
    {
      "@type": "Product",
      "name": "Running Shoe",
      "sku": "SHOE-BASE",
      "offers": {"price": "100.00", "priceCurrency": "GBP"},
      "hasVariant": [
        {
          "@type": "Product",
          "name": "Running Shoe - Size 9",
          "sku": "SHOE-9",
          "size": "9",
          "offers": {
            "price": "105.00",
            "availability": "https://schema.org/InStock"
          }
        },
        {
          "@type": "Product",
          "name": "Running Shoe - Size 10",
          "sku": "SHOE-10",
          "size": "10",
          "offers": {
            "price": "110.00",
            "availability": "https://schema.org/OutOfStock"
          }
        }
      ]
    }
    </script>
    """
    products = ProductExtractor().extract(html, "https://shop.example/products/running-shoe")

    assert len(products) == 1
    assert len(products[0]["variants"]) == 2
    assert products[0]["variants"][0]["sku"] == "SHOE-9"
    assert products[0]["variants"][0]["price"] == "105.00"
    assert products[0]["variants"][1]["in_stock"] is False
