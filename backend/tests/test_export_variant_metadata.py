import json
from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.services.export_service import ExportService


@pytest.mark.asyncio
async def test_json_export_preserves_variant_and_image_gallery_metadata(tmp_path):
    service = ExportService(db=None)
    service.export_path = str(tmp_path)
    product = SimpleNamespace(
        id=7,
        product_id="P-7",
        sku="BASE-7",
        name="Trail Jacket",
        description="Waterproof jacket",
        price=Decimal("89.95"),
        original_price=Decimal("109.95"),
        currency="GBP",
        in_stock=True,
        stock_quantity=5,
        url="https://shop.example/products/trail-jacket",
        image_url="https://cdn.example/front.jpg",
        images=[
            SimpleNamespace(url="https://cdn.example/front.jpg"),
            SimpleNamespace(url="https://cdn.example/back.jpg"),
        ],
        category="Clothing",
        subcategory="Jackets",
        category_path="Clothing > Jackets",
        brand="Northwind",
        manufacturer="Northwind",
        tags=["waterproof", "outdoor"],
        specifications={"material": "nylon"},
        features=["hooded"],
        rating=4.8,
        review_count=12,
        variants=[
            SimpleNamespace(
                variant_id="V-1",
                name="Small / Blue",
                sku="JKT-S-B",
                price=Decimal("89.95"),
                original_price=Decimal("109.95"),
                in_stock=True,
                stock_quantity=3,
                attributes={"size": "Small", "colour": "Blue"},
                image_url="https://cdn.example/small-blue.jpg",
            )
        ],
        source_domain="shop.example",
        scraped_at=datetime(2026, 1, 1),
    )

    path = await service._export_json([product], "variants")
    with open(path, encoding="utf-8") as handle:
        exported = json.load(handle)

    item = exported["products"][0]
    assert len(item["images"]) == 2
    assert item["tags"] == ["waterproof", "outdoor"]
    assert item["variants"][0]["variant_id"] == "V-1"
    assert item["variants"][0]["original_price"] == 109.95
    assert item["variants"][0]["stock_quantity"] == 3
    assert item["variants"][0]["attributes"] == {"size": "Small", "colour": "Blue"}
