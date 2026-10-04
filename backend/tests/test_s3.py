"""
Unit tests for AWS S3 Storage Service and Cloud Ingestion functionality.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from app.services.s3_storage_service import S3StorageService, s3_storage_service


def test_s3_storage_service_initialization():
    service = S3StorageService()
    assert hasattr(service, "is_configured")
    assert hasattr(service, "test_connection")
    assert hasattr(service, "download_and_upload_image")
    assert hasattr(service, "batch_upload_product_images")


@pytest.mark.asyncio
async def test_s3_test_connection_unconfigured():
    service = S3StorageService()
    service._configured = False
    service._s3_client = None
    res = await service.test_connection()
    assert res["success"] is False
    assert "not configured" in res["message"]


@pytest.mark.asyncio
async def test_s3_download_and_upload_image_mock():
    service = S3StorageService()
    service._configured = True
    service._s3_client = MagicMock()

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = b"fake-jpg-binary-data"
    mock_resp.headers = {"content-type": "image/jpeg"}

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        service._s3_client.put_object = MagicMock(return_value={"ETag": '"test-etag"'})

        result = await service.download_and_upload_image(
            image_url="https://example.com/products/sneaker.jpg",
            bucket="test-bucket",
            custom_prefix="catalog",
            acl="public-read"
        )

        assert result["success"] is True
        assert result["bucket"] == "test-bucket"
        assert result["s3_key"].startswith("catalog/")
        assert "sneaker.jpg" not in result["s3_key"]  # Uses hash key
        assert "https://test-bucket.s3" in result["s3_url"]
        assert result["size_bytes"] == len(b"fake-jpg-binary-data")
        service._s3_client.put_object.assert_called_once()


@pytest.mark.asyncio
async def test_s3_batch_upload():
    service = S3StorageService()
    service._configured = True
    service._s3_client = MagicMock()

    products = [
        {"name": "Sneaker", "image_url": "https://example.com/s.jpg"},
        {"name": "Watch", "image_url": "https://example.com/w.jpg"},
        {"name": "T-Shirt", "image_url": None},
    ]

    mock_upload = {
        "success": True,
        "s3_url": "https://bucket.s3.amazonaws.com/products/item.jpg",
        "s3_key": "products/item.jpg",
    }

    with patch.object(service, "download_and_upload_image", new_callable=AsyncMock) as mock_func:
        mock_func.return_value = mock_upload
        updated = await service.batch_upload_product_images(products)
        assert len(updated) == 3
        assert updated[0]["s3_url"] == "https://bucket.s3.amazonaws.com/products/item.jpg"
        assert updated[1]["s3_url"] == "https://bucket.s3.amazonaws.com/products/item.jpg"
        assert "s3_url" not in updated[2]
