import pytest
from bs4 import BeautifulSoup
from app.services.variant_extractor_service import VariantExtractorService, variant_extractor_service


def test_extract_variants_from_woocommerce_form():
    html = """
    <html>
      <body>
        <form class="variations_form cart" data-product_variations='[
          {
            "variation_id": 101,
            "attributes": {"attribute_pa_color": "Blue", "attribute_pa_size": "Large"},
            "display_price": 49.99,
            "display_regular_price": 59.99,
            "is_in_stock": true,
            "max_qty": 15,
            "sku": "TSHIRT-BLU-L"
          },
          {
            "variation_id": 102,
            "attributes": {"attribute_pa_color": "Red", "attribute_pa_size": "Medium"},
            "display_price": 44.99,
            "is_in_stock": false,
            "max_qty": 0,
            "sku": "TSHIRT-RED-M"
          }
        ]'>
        </form>
      </body>
    </html>
    """
    variants = variant_extractor_service.extract_from_html(html)
    assert len(variants) == 2
    
    v1 = variants[0]
    assert v1["variant_id"] == "101"
    assert v1["price"] == 49.99
    assert v1["sku"] == "TSHIRT-BLU-L"
    assert v1["in_stock"] is True
    assert v1["stock_quantity"] == 15
    assert "Color: Blue" in v1["name"] or "Blue" in v1["name"]

    v2 = variants[1]
    assert v2["variant_id"] == "102"
    assert v2["price"] == 44.99
    assert v2["in_stock"] is False
    assert v2["stock_status"] == "Out of Stock"


def test_extract_variants_from_json_ld():
    html = """
    <html>
      <head>
        <script type="application/ld+json">
        {
          "@context": "https://schema.org",
          "@type": "Product",
          "name": "Men Running Shoes",
          "hasVariant": [
            {
              "@type": "Product",
              "name": "Men Running Shoes - Size 10",
              "sku": "RUN-10",
              "size": "10",
              "offers": {
                "@type": "Offer",
                "price": "120.00",
                "availability": "https://schema.org/InStock"
              }
            },
            {
              "@type": "Product",
              "name": "Men Running Shoes - Size 11",
              "sku": "RUN-11",
              "size": "11",
              "offers": {
                "@type": "Offer",
                "price": "125.00",
                "availability": "https://schema.org/OutOfStock"
              }
            }
          ]
        }
        </script>
      </head>
      <body></body>
    </html>
    """
    variants = variant_extractor_service.extract_from_html(html)
    assert len(variants) == 2
    assert variants[0]["sku"] == "RUN-10"
    assert variants[0]["price"] == 120.0
    assert variants[0]["in_stock"] is True

    assert variants[1]["sku"] == "RUN-11"
    assert variants[1]["price"] == 125.0
    assert variants[1]["in_stock"] is False


def test_extract_variants_from_select_dropdowns():
    html = """
    <html>
      <body>
        <div class="product-options">
          <select id="select-product-size" name="product_size">
            <option value="">Select Size</option>
            <option value="s">Small ($19.99)</option>
            <option value="m">Medium ($24.99)</option>
            <option value="l" disabled>Large (Sold out)</option>
          </select>
        </div>
      </body>
    </html>
    """
    variants = variant_extractor_service.extract_from_html(html)
    assert len(variants) == 3
    assert any("Small" in v["name"] and v["price"] == 19.99 for v in variants)
    assert any("Large" in v["name"] and v["in_stock"] is False for v in variants)


def test_normalize_variants_parses_limited_stock():
    raw = [
        {
            "name": "Only 3 left in stock - Red XL",
            "price": 29.99,
            "in_stock": True,
        }
    ]
    normalized = VariantExtractorService.normalize_variants(raw)
    assert len(normalized) == 1
    assert normalized[0]["stock_quantity"] == 3
    assert normalized[0]["stock_status"] == "Only 3 left"
