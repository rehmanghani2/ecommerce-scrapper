"""
Unit and integration tests for Competitor Catalog Change Detection and Differential Intelligence.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone
from app.services.catalog_diff_service import CatalogDiffService, catalog_diff_service
from app.models.job import Job, JobStatus, JobType
from app.models.product import Product


def test_calculate_diff_additions_and_delistings():
    service = CatalogDiffService()
    now = datetime.now(timezone.utc)

    job_a = Job(id=1, job_id="job_1", name="Crawl Week 1", domain="competitor.com", created_at=now)
    job_b = Job(id=2, job_id="job_2", name="Crawl Week 2", domain="competitor.com", created_at=now)

    p1 = Product(id=101, name="Sony WH-1000XM4", url="https://competitor.com/p1", sku="XM4", price=299.99, in_stock=True)
    p2 = Product(id=102, name="Sony WH-1000XM5", url="https://competitor.com/p2", sku="XM5", price=399.99, in_stock=True)
    p3 = Product(id=103, name="Apple AirPods Max", url="https://competitor.com/p3", sku="MAX", price=549.99, in_stock=True)

    products_a = [p1, p2]  # Baseline
    products_b = [p2, p3]  # Current: p1 removed, p3 added, p2 unchanged

    diff = service.calculate_diff(job_a, products_a, job_b, products_b)
    summary = diff["summary"]

    assert summary["added_count"] == 1
    assert summary["removed_count"] == 1
    assert summary["price_changed_count"] == 0
    assert summary["unchanged_count"] == 1

    assert diff["added_products"][0]["name"] == "Apple AirPods Max"
    assert diff["removed_products"][0]["name"] == "Sony WH-1000XM4"


def test_calculate_diff_price_shifts():
    service = CatalogDiffService()
    now = datetime.now(timezone.utc)

    job_a = Job(id=1, job_id="job_1", name="Baseline", domain="shop.com", created_at=now)
    job_b = Job(id=2, job_id="job_2", name="Current", domain="shop.com", created_at=now)

    # Product A: Price drop from $100 -> $80 (-20%)
    p_a1 = Product(id=1, name="Widget One", url="https://shop.com/1", price=100.0, in_stock=True)
    p_b1 = Product(id=2, name="Widget One", url="https://shop.com/1", price=80.0, in_stock=True)

    # Product B: Price increase from $50 -> $60 (+20%)
    p_a2 = Product(id=3, name="Widget Two", url="https://shop.com/2", price=50.0, in_stock=True)
    p_b2 = Product(id=4, name="Widget Two", url="https://shop.com/2", price=60.0, in_stock=True)

    diff = service.calculate_diff(job_a, [p_a1, p_a2], job_b, [p_b1, p_b2])
    summary = diff["summary"]

    assert summary["price_changed_count"] == 2
    assert summary["price_decreased_count"] == 1
    assert summary["price_increased_count"] == 1
    assert summary["added_count"] == 0
    assert summary["removed_count"] == 0

    p_drop = next(p for p in diff["price_changes"] if p["direction"] == "decreased")
    assert p_drop["difference"] == -20.0
    assert p_drop["percentage"] == -20.0

    p_up = next(p for p in diff["price_changes"] if p["direction"] == "increased")
    assert p_up["difference"] == 10.0
    assert p_up["percentage"] == 20.0


def test_calculate_diff_stock_status_changes():
    service = CatalogDiffService()
    now = datetime.now(timezone.utc)

    job_a = Job(id=1, job_id="job_1", name="Baseline", domain="shop.com", created_at=now)
    job_b = Job(id=2, job_id="job_2", name="Current", domain="shop.com", created_at=now)

    # Product goes out of stock
    p_a1 = Product(id=1, name="Item Alpha", url="https://shop.com/alpha", price=25.0, in_stock=True)
    p_b1 = Product(id=2, name="Item Alpha", url="https://shop.com/alpha", price=25.0, in_stock=False)

    # Product returns back in stock
    p_a2 = Product(id=3, name="Item Beta", url="https://shop.com/beta", price=50.0, in_stock=False)
    p_b2 = Product(id=4, name="Item Beta", url="https://shop.com/beta", price=50.0, in_stock=True)

    diff = service.calculate_diff(job_a, [p_a1, p_a2], job_b, [p_b1, p_b2])
    stock_changes = diff["stock_changes"]

    assert len(stock_changes) == 2
    out_of_stock_item = next(s for s in stock_changes if s["status"] == "out_of_stock")
    assert out_of_stock_item["name"] == "Item Alpha"

    back_in_stock_item = next(s for s in stock_changes if s["status"] == "back_in_stock")
    assert back_in_stock_item["name"] == "Item Beta"


def test_export_diff_to_csv():
    service = CatalogDiffService()
    sample_diff = {
        "added_products": [
            {"name": "New Gadget", "sku": "GAD-01", "brand": "BrandX", "price": 49.99, "in_stock": True, "url": "https://shop.com/gadget"}
        ],
        "removed_products": [
            {"name": "Old Gadget", "sku": "GAD-00", "brand": "BrandX", "price": 39.99, "in_stock": False, "url": "https://shop.com/old"}
        ],
        "price_changes": [
            {"name": "Standard Widget", "sku": "WID-1", "brand": "BrandY", "old_price": 20.0, "new_price": 15.0, "difference": -5.0, "percentage": -25.0, "direction": "decreased", "url": "https://shop.com/widget"}
        ],
        "stock_changes": [
            {"name": "Rare Collectible", "sku": "COL-1", "price": 100.0, "old_in_stock": False, "new_in_stock": True, "url": "https://shop.com/col"}
        ]
    }

    csv_data = service.export_diff_to_csv(sample_diff)
    assert "Change Type,Product Name,SKU,Brand" in csv_data
    assert "NEW PRODUCT (ADDED)" in csv_data
    assert "New Gadget" in csv_data
    assert "DELISTED (REMOVED)" in csv_data
    assert "PRICE DECREASED" in csv_data
    assert "BACK IN STOCK" in csv_data


@pytest.mark.asyncio
async def test_compare_two_jobs_async_service():
    service = CatalogDiffService()
    now = datetime.now(timezone.utc)

    j1 = Job(id=1, job_id="j1", name="First", domain="site.com", created_at=now)
    j2 = Job(id=2, job_id="j2", name="Second", domain="site.com", created_at=now)

    p1 = Product(id=10, name="Item 1", url="https://site.com/1", price=10.0, in_stock=True)
    p2 = Product(id=11, name="Item 1", url="https://site.com/1", price=12.0, in_stock=True)

    mock_db = AsyncMock()
    mock_db.get.side_effect = lambda model, pk: j1 if pk == 1 else j2

    # Mock execute results
    mock_res_1 = MagicMock()
    mock_res_1.scalars.return_value.all.return_value = [p1]

    mock_res_2 = MagicMock()
    mock_res_2.scalars.return_value.all.return_value = [p2]

    mock_db.execute.side_effect = [mock_res_1, mock_res_2]

    diff = await service.compare_two_jobs(mock_db, 1, 2)
    assert diff is not None
    assert diff["summary"]["price_changed_count"] == 1
    assert diff["summary"]["price_increased_count"] == 1


@pytest.mark.asyncio
async def test_diff_api_compare_endpoint():
    from httpx import AsyncClient, ASGITransport
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Mocking catalog_diff_service.compare_two_jobs
        with patch("app.services.catalog_diff_service.catalog_diff_service.compare_two_jobs", new_callable=AsyncMock) as mock_comp:
            mock_comp.return_value = {
                "summary": {
                    "domain": "test.com",
                    "added_count": 2,
                    "removed_count": 1,
                    "price_changed_count": 0,
                    "stock_changed_count": 0,
                },
                "added_products": [],
                "removed_products": [],
                "price_changes": [],
                "stock_changes": [],
            }

            res = await client.post("/api/v1/diff/compare", json={"job_id_1": 1, "job_id_2": 2})
            assert res.status_code == 200
            data = res.json()
            assert data["success"] is True
            assert data["diff"]["summary"]["added_count"] == 2
