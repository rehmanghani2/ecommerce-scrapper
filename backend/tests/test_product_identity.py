from app.core.data_cleaner import DataCleaner


def product(url, **overrides):
    record = {
        "name": "Acme Road Bike",
        "brand": "Acme",
        "sku": "AB-123",
        "price": "£1,299.99",
        "url": url,
        "images": [],
    }
    record.update(overrides)
    return record


def test_tracking_parameters_are_removed_but_variant_parameters_are_kept():
    cleaner = DataCleaner()
    first = cleaner._canonicalize_url(
        "https://Shop.Example/products/bike?utm_source=newsletter&variant=red#details"
    )
    second = cleaner._canonicalize_url(
        "https://shop.example/products/bike?variant=red&gclid=abc"
    )
    other_variant = cleaner._canonicalize_url(
        "https://shop.example/products/bike?variant=blue"
    )

    assert first == second
    assert first != other_variant


def test_deduplicates_same_product_url_even_when_tracking_differs():
    cleaner = DataCleaner()
    records = [
        product("https://shop.example/p/123?utm_campaign=spring", price="£1,299.99"),
        product("https://shop.example/p/123?gclid=tracking", description="Carbon frame"),
    ]

    cleaned = cleaner.clean_products(records)

    assert len(cleaned) == 1
    assert cleaned[0]["price"] == 1299.99
    assert cleaned[0]["currency"] == "GBP"
    assert cleaned[0]["description"] == "Carbon frame"


def test_does_not_merge_distinct_variant_urls_even_when_parent_sku_matches():
    cleaner = DataCleaner()
    records = [
        product("https://shop.example/p/123?variant=red", sku="PARENT-1"),
        product("https://shop.example/p/123?variant=blue", sku="PARENT-1"),
    ]

    assert len(cleaner.clean_products(records)) == 2


def test_does_not_merge_different_urls_based_only_on_same_title_and_price():
    cleaner = DataCleaner()
    records = [
        product("https://shop.example/p/one", sku=None),
        product("https://shop.example/p/two", sku=None),
    ]

    assert len(cleaner.clean_products(records)) == 2


def test_price_parser_handles_uk_and_european_formats():
    cleaner = DataCleaner()

    assert cleaner._parse_price("£1,299.99") == (1299.99, "GBP")
    assert cleaner._parse_price("1.299,99 EUR") == (1299.99, "EUR")
    assert cleaner._parse_price("1,299") == (1299.0, None)


def test_numeric_price_does_not_erase_existing_currency():
    cleaner = DataCleaner()
    cleaned = cleaner.clean_product(product(
        "https://shop.example/p/123",
        price=49.99,
        currency="GBP",
    ))

    assert cleaned["price"] == 49.99
    assert cleaned["currency"] == "GBP"


def test_duplicate_records_merge_image_gallery_and_variants():
    cleaner = DataCleaner()
    records = [
        product(
            "https://shop.example/p/123",
            images=["https://shop.example/a.jpg"],
            variants=[{"variant_id": "red", "name": "Red"}],
        ),
        product(
            "https://shop.example/p/123?utm_source=x",
            images=["https://shop.example/b.jpg"],
            variants=[{"variant_id": "blue", "name": "Blue"}],
        ),
    ]

    cleaned = cleaner.clean_products(records)

    assert len(cleaned) == 1
    assert cleaned[0]["images"] == [
        "https://shop.example/a.jpg",
        "https://shop.example/b.jpg",
    ]
    assert {variant["variant_id"] for variant in cleaned[0]["variants"]} == {"red", "blue"}
