"""
Unit and integration tests for AI Competitor Product Matching and Catalog Deduplication.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import Response
from app.services.product_matching_service import ProductMatchingService, product_matching_service
from app.models.product import Product


def test_normalize_sku():
    service = ProductMatchingService()
    assert service.normalize_sku("abc-123_XYZ") == "ABC123XYZ"
    assert service.normalize_sku("  wh-1000xm5 / b  ") == "WH1000XM5B"
    assert service.normalize_sku("N/A") is None
    assert service.normalize_sku("none") is None
    assert service.normalize_sku("12") is None  # Too short
    assert service.normalize_sku(None) is None


def test_clean_title():
    service = ProductMatchingService()
    # Strips brackets, filler/noise words like 'pack of 1', 'brand new', 'official store'
    cleaned = service.clean_title("Sony WH-1000XM5 Wireless Headphones [Official Store] (Pack of 1) - Brand New")
    assert "sony" in cleaned
    assert "wh" in cleaned
    assert "1000xm5" in cleaned
    assert "official" not in cleaned
    assert "pack" not in cleaned
    assert "brand" not in cleaned
    assert "new" not in cleaned


def test_heuristic_similarity_exact_sku():
    service = ProductMatchingService()
    p1 = {"name": "Sony WH-1000XM5 Black", "sku": "WH-1000XM5"}
    p2 = {"name": "Sony Headphones 1000XM5 Over Ear", "sku": "wh1000xm5"}
    
    score, method = service.compute_heuristic_similarity(p1, p2)
    assert score == 1.0
    assert method == "sku_match"


def test_heuristic_similarity_brand_mismatch():
    service = ProductMatchingService()
    p1 = {"name": "Sony WH-1000XM5 Headphones", "brand": "Sony"}
    p2 = {"name": "Bose QuietComfort 45 Headphones", "brand": "Bose"}
    
    score, method = service.compute_heuristic_similarity(p1, p2)
    assert score == 0.0
    assert method == "brand_mismatch"


def test_heuristic_similarity_fuzzy_matching_titles():
    service = ProductMatchingService()
    p1 = {"name": "Sony WH-1000XM5 Wireless Noise Canceling Headphones - Black", "brand": "Sony"}
    p2 = {"name": "Sony WH-1000XM5 Noise-Canceling Bluetooth Over-Ear Headphones", "brand": "Sony"}
    
    score, method = service.compute_heuristic_similarity(p1, p2)
    assert method == "heuristic_fuzzy"
    assert score >= 0.75  # High similarity expected


def test_heuristic_similarity_dissimilar_titles():
    service = ProductMatchingService()
    p1 = {"name": "Apple iPhone 15 Pro Max 256GB Natural Titanium", "brand": "Apple"}
    p2 = {"name": "Apple MacBook Air 15-inch M2 Chip 512GB", "brand": "Apple"}
    
    score, method = service.compute_heuristic_similarity(p1, p2)
    assert score < 0.60


@pytest.mark.asyncio
async def test_compare_products_with_ai_mock():
    service = ProductMatchingService()
    mock_res = MagicMock(spec=Response)
    mock_res.status_code = 200
    mock_res.json = MagicMock(return_value={
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": '{"is_match": true, "confidence": 0.95, "reason": "Both are Sony WH-1000XM5 headphones differing only by retailer packaging"}'
                        }
                    ]
                }
            }
        ]
    })

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_res
        result = await service.compare_products_with_ai(
            p1_name="Sony WH-1000XM5 Silver",
            p2_name="Sony WH1000XM5/S Noise Canceling",
            brand1="Sony",
            brand2="Sony",
            api_key="test-gemini-key"
        )
        assert result["is_match"] is True
        assert result["confidence"] == 0.95
        assert "Sony WH-1000XM5" in result["reason"]


@pytest.mark.asyncio
async def test_evaluate_pair_tiered_fallback():
    service = ProductMatchingService()

    # Tier 1: Exact SKU
    res = await service.evaluate_pair(
        p1={"name": "Widget A", "sku": "SKU-999"},
        p2={"name": "Alternative Widget", "sku": "sku-999"},
        threshold=0.75,
        allow_ai=False
    )
    assert res["is_match"] is True
    assert res["confidence"] == 1.0
    assert res["method"] == "sku_match"

    # Tier 2: Strong fuzzy match
    res_fuzzy = await service.evaluate_pair(
        p1={"name": "Logitech MX Master 3S Wireless Mouse Black", "brand": "Logitech"},
        p2={"name": "Logitech MX Master 3S Performance Wireless Mouse", "brand": "Logitech"},
        threshold=0.70,
        allow_ai=False
    )
    assert res_fuzzy["is_match"] is True
    assert res_fuzzy["method"] == "heuristic_fuzzy"


@pytest.mark.asyncio
async def test_cluster_products_batch_sku():
    service = ProductMatchingService()

    # Create dummy products with matching SKU
    p1 = Product(id=1, name="Sony WH-1000XM5", sku="WH1000XM5", source_domain="amazon.com", price=349.99)
    p2 = Product(id=2, name="Sony WH-1000XM5 Headphones", sku="wh-1000xm5", source_domain="walmart.com", price=329.99)
    p3 = Product(id=3, name="Apple AirPods Max", sku="AIRPODS-MAX", source_domain="amazon.com", price=499.00)

    mock_db = AsyncMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [p1, p2, p3]
    mock_res = MagicMock()
    mock_res.scalars.return_value = mock_scalars
    mock_db.execute.return_value = mock_res

    res = await service.cluster_products_batch(db=mock_db, job_id=10, threshold=0.75, use_ai=False)
    assert res["success"] is True
    assert res["clusters_created"] >= 1
    assert p1.match_cluster_id is not None
    assert p1.match_cluster_id == p2.match_cluster_id
    assert p1.match_confidence == 1.0
    assert p2.match_confidence == 1.0


@pytest.mark.asyncio
async def test_matching_api_compare_endpoint():
    from httpx import AsyncClient, ASGITransport
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "product_a": {"name": "Sony WH-1000XM5 Wireless Headphones", "sku": "WH1000XM5", "brand": "Sony"},
            "product_b": {"name": "Sony WH-1000XM5 Over Ear Noise Canceling", "sku": "wh1000xm5", "brand": "Sony"},
            "threshold": 0.75,
            "use_ai": False
        }
        res = await client.post("/api/v1/matching/compare", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["result"]["is_match"] is True
        assert data["result"]["confidence"] == 1.0
