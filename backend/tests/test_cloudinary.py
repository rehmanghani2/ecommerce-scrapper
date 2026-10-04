"""
Unit tests for Cloudinary Service and Image CDN functionality.
"""

import pytest
from unittest.mock import patch, MagicMock
from app.services.cloudinary_service import CloudinaryService, cloudinary_service


def test_cloudinary_service_configuration():
    service = CloudinaryService()
    assert hasattr(service, "is_configured")
    assert hasattr(service, "upload_image_url")
    assert hasattr(service, "get_transformed_url")


def test_cloudinary_transformed_url():
    service = CloudinaryService()
    with patch("cloudinary.utils.cloudinary_url", return_value=("https://res.cloudinary.com/demo/image/upload/w_300,h_300,c_fill/sample.webp", {})):
        url = service.get_transformed_url("sample", width=300, height=300, crop="fill")
        assert "https://res.cloudinary.com" in url
        assert "sample" in url


@pytest.mark.asyncio
async def test_cloudinary_test_connection_unconfigured():
    service = CloudinaryService()
    service._configured = False
    res = await service.test_connection()
    assert res["success"] is False
    assert "not configured" in res["message"]


@pytest.mark.asyncio
async def test_cloudinary_upload_image_url_mock():
    service = CloudinaryService()
    service._configured = True

    mock_resp = {
        "secure_url": "https://res.cloudinary.com/demo/image/upload/v1234/sample.jpg",
        "public_id": "ecommerce_scraper/sample",
        "format": "jpg",
        "width": 800,
        "height": 600,
        "bytes": 54321,
    }

    with patch("cloudinary.uploader.upload", return_value=mock_resp), \
         patch("cloudinary.utils.cloudinary_url", side_effect=[
             ("https://res.cloudinary.com/demo/image/upload/w_300,h_300,c_fill/thumb.webp", {}),
             ("https://res.cloudinary.com/demo/image/upload/q_auto,f_auto/optimized.webp", {})
         ]):
        result = await service.upload_image_url("https://example.com/product.jpg")
        assert result["success"] is True
        assert result["public_id"] == "ecommerce_scraper/sample"
        assert result["secure_url"] == "https://res.cloudinary.com/demo/image/upload/v1234/sample.jpg"
        assert result["thumbnail_url"] is not None
        assert result["format"] == "jpg"


@pytest.mark.asyncio
async def test_cloudinary_batch_upload():
    service = CloudinaryService()
    service._configured = True

    products = [
        {"name": "Item 1", "image_url": "https://example.com/img1.jpg"},
        {"name": "Item 2", "image_url": "https://example.com/img2.jpg"},
        {"name": "Item 3", "image_url": None},  # No image
    ]

    mock_upload_res = {
        "success": True,
        "secure_url": "https://res.cloudinary.com/demo/item.jpg",
        "public_id": "prod_1",
        "thumbnail_url": "https://res.cloudinary.com/demo/thumb.webp",
    }

    with patch.object(service, "upload_image_url", return_value=mock_upload_res):
        updated = await service.batch_upload_product_images(products)
        assert len(updated) == 3
        assert updated[0]["cloudinary_url"] == "https://res.cloudinary.com/demo/item.jpg"
        assert updated[1]["cloudinary_url"] == "https://res.cloudinary.com/demo/item.jpg"
        assert "cloudinary_url" not in updated[2]
