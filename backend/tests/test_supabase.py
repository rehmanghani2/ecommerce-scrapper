import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import Response
from app.services.supabase_storage_service import SupabaseStorageService
from app.models.product import Product


@pytest.fixture
def supabase_service():
    return SupabaseStorageService(
        project_url="https://xyzcompany.supabase.co",
        api_key="sb_test_api_key_123",
        bucket="products",
        folder="test-images"
    )


def test_supabase_configured(supabase_service):
    assert supabase_service.is_configured() is True
    assert supabase_service._custom_bucket == "products"
    assert supabase_service._custom_folder == "test-images"

    unconfigured = SupabaseStorageService(project_url="", api_key="")
    assert unconfigured.is_configured() is False


def test_get_public_url(supabase_service):
    url = supabase_service.get_public_url(bucket="products", path="test-images/item_1.jpg", supabase_url="https://xyzcompany.supabase.co")
    assert url == "https://xyzcompany.supabase.co/storage/v1/object/public/products/test-images/item_1.jpg"


@pytest.mark.asyncio
async def test_supabase_test_connection_success(supabase_service):
    mock_response = MagicMock(spec=Response)
    mock_response.status_code = 200
    mock_response.json = MagicMock(return_value={"public": True, "file_size_limit": 52428800})

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        result = await supabase_service.test_connection(
            custom_url="https://xyzcompany.supabase.co",
            custom_key="sb_test_api_key_123",
            custom_bucket="products"
        )
        assert result["success"] is True
        assert "Successfully connected" in result["message"]
        assert result["bucket"] == "products"


@pytest.mark.asyncio
async def test_supabase_test_connection_missing_bucket(supabase_service):
    mock_response = MagicMock(spec=Response)
    mock_response.status_code = 404

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        result = await supabase_service.test_connection(
            custom_url="https://xyzcompany.supabase.co",
            custom_key="sb_test_api_key_123",
            custom_bucket="nonexistent-bucket"
        )
        assert result["success"] is False
        assert "does not exist" in result["message"]


@pytest.mark.asyncio
async def test_download_and_upload_image(supabase_service):
    image_bytes = b"fake-raw-image-bytes"

    async def mock_get(url, *args, **kwargs):
        res = MagicMock(spec=Response)
        res.status_code = 200
        res.content = image_bytes
        res.headers = {"content-type": "image/jpeg"}
        return res

    async def mock_post(url, *args, **kwargs):
        res = MagicMock(spec=Response)
        res.status_code = 200
        res.json = MagicMock(return_value={"Key": "products/test-images/prod_1.jpg"})
        return res

    with patch("httpx.AsyncClient.get", side_effect=mock_get), \
         patch("httpx.AsyncClient.post", side_effect=mock_post):
        res = await supabase_service.download_and_upload_image(
            image_url="https://example.com/product.jpg",
            custom_bucket="products",
            custom_folder="test-images",
            custom_url="https://xyzcompany.supabase.co",
            custom_key="sb_test_key"
        )
        assert res["success"] is True
        assert res["supabase_url"].startswith("https://xyzcompany.supabase.co/storage/v1/object/public/products/test-images/")
        assert res["supabase_url"].endswith(".jpg")
        assert res["size_bytes"] == len(image_bytes)


@pytest.mark.asyncio
async def test_batch_upload_product_images(supabase_service):
    products = [
        {"name": "Laptop A", "price": 999.0, "image_url": "https://example.com/a.jpg"},
        {"name": "Laptop B", "price": 1299.0, "image_url": "https://example.com/b.png"},
        {"name": "No Image", "price": 10.0, "image_url": None},
    ]

    mock_upload_result = {
        "success": True,
        "supabase_url": "https://xyzcompany.supabase.co/storage/v1/object/public/products/test-images/sample.jpg",
        "supabase_path": "test-images/sample.jpg"
    }

    with patch.object(supabase_service, "download_and_upload_image", new_callable=AsyncMock) as mock_upload:
        mock_upload.return_value = mock_upload_result
        res = await supabase_service.batch_upload_product_images(products)

        assert len(res) == 3
        assert res[0]["supabase_url"] == mock_upload_result["supabase_url"]
        assert res[1]["supabase_url"] == mock_upload_result["supabase_url"]
        assert "supabase_url" not in res[2] or res[2].get("supabase_url") is None
