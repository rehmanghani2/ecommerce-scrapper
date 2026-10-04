import pytest
from unittest.mock import patch, MagicMock
import httpx
import json

from app.services.ai_extractor_service import ai_extractor_service


SAMPLE_HTML = """
<!DOCTYPE html>
<html>
<head>
  <title>Test Store</title>
  <style>.hidden { display: none; }</style>
  <script>console.log("analytics tracking");</script>
</head>
<body>
  <header><nav><a href="/">Home</a></nav></header>
  <main>
    <div class="product-item">
      <h2 class="title">Wireless Noise Cancelling Headphones</h2>
      <span class="price">$199.99</span>
      <span class="old-price">$249.99</span>
      <img src="/images/headphones.jpg" alt="Headphones" />
      <a href="/products/wireless-headphones">View Details</a>
    </div>
  </main>
  <footer><p>Copyright 2026</p></footer>
</body>
</html>
"""


def test_clean_html_for_llm():
    cleaned = ai_extractor_service.clean_html_for_llm(SAMPLE_HTML)
    assert "analytics tracking" not in cleaned
    assert ".hidden" not in cleaned
    assert "<nav" not in cleaned
    assert "<footer" not in cleaned
    assert "Wireless Noise Cancelling Headphones" in cleaned
    assert "$199.99" in cleaned


@pytest.mark.asyncio
async def test_extract_products_with_ai_mocked():
    mock_gemini_response = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": json.dumps({
                                "products": [
                                    {
                                        "name": "Wireless Noise Cancelling Headphones",
                                        "price": 199.99,
                                        "original_price": 249.99,
                                        "currency": "USD",
                                        "in_stock": True,
                                        "image_url": "/images/headphones.jpg",
                                        "url": "/products/wireless-headphones"
                                    }
                                ]
                            })
                        }
                    ]
                }
            }
        ]
    }

    mock_resp = httpx.Response(
        status_code=200,
        content=json.dumps(mock_gemini_response).encode("utf-8"),
        request=httpx.Request("POST", "https://generativelanguage.googleapis.com")
    )

    with patch("httpx.AsyncClient.post", return_value=mock_resp):
        res = await ai_extractor_service.extract_products_with_ai(
            html=SAMPLE_HTML,
            base_url="https://example.com/shop",
            api_key="test_fake_key"
        )
        assert res["success"] is True
        assert len(res["products"]) == 1
        prod = res["products"][0]
        assert prod["name"] == "Wireless Noise Cancelling Headphones"
        assert prod["price"] == 199.99
        # Absolute URL normalization check
        assert prod["url"] == "https://example.com/products/wireless-headphones"
        assert prod["image_url"] == "https://example.com/images/headphones.jpg"


@pytest.mark.asyncio
async def test_suggest_selectors_with_ai_mocked():
    mock_gemini_response = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": json.dumps({
                                "selectors": {
                                    "product_card": ".product-item",
                                    "product_name": ".title",
                                    "product_price": ".price"
                                },
                                "confidence": 0.95,
                                "reasoning": "Standard e-commerce CSS classes"
                            })
                        }
                    ]
                }
            }
        ]
    }

    mock_resp = httpx.Response(
        status_code=200,
        content=json.dumps(mock_gemini_response).encode("utf-8"),
        request=httpx.Request("POST", "https://generativelanguage.googleapis.com")
    )

    with patch("httpx.AsyncClient.post", return_value=mock_resp):
        res = await ai_extractor_service.suggest_selectors_with_ai(
            html=SAMPLE_HTML,
            base_url="https://example.com",
            api_key="test_fake_key"
        )
        assert res["success"] is True
        assert res["selectors"]["product_card"] == ".product-item"
        assert res["selectors"]["product_name"] == ".title"
        assert res["confidence"] == 0.95


@pytest.mark.asyncio
async def test_test_api_key():
    mock_resp_success = httpx.Response(
        status_code=200,
        content=b"{}",
        request=httpx.Request("POST", "https://generativelanguage.googleapis.com")
    )

    with patch("httpx.AsyncClient.post", return_value=mock_resp_success):
        res = await ai_extractor_service.test_api_key("valid_key")
        assert res["success"] is True
        assert "Google Gemini" in res["message"]

    mock_resp_err = httpx.Response(
        status_code=400,
        content=json.dumps({"error": {"message": "API key not valid"}}).encode("utf-8"),
        request=httpx.Request("POST", "https://generativelanguage.googleapis.com")
    )

    with patch("httpx.AsyncClient.post", return_value=mock_resp_err):
        res_err = await ai_extractor_service.test_api_key("bad_key")
        assert res_err["success"] is False
        assert "API key not valid" in res_err["message"]
