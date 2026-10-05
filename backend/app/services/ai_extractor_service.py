"""
AI-Powered Product Extraction Service (Google Gemini / Zero-Shot).
Extracts structured product data and reverse-engineers CSS selectors
from unstructured, custom, or heavily obfuscated e-commerce HTML.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from urllib.parse import urljoin
import httpx
from bs4 import BeautifulSoup

from app.config import settings

logger = logging.getLogger(__name__)


class AIExtractorService:
    """Service utilizing Google Gemini LLM for zero-shot e-commerce data extraction."""

    def __init__(self):
        self.default_model = getattr(settings, "GEMINI_MODEL", "gemini-2.5-flash")

    def _get_api_key(self, custom_key: Optional[str] = None) -> Optional[str]:
        """Resolve Gemini API key from parameter or environment settings."""
        if custom_key and custom_key.strip():
            return custom_key.strip()
        return settings.GEMINI_API_KEY

    def clean_html_for_llm(self, html: str, max_chars: int = 35000) -> str:
        """
        Pre-process HTML by stripping non-informative tags (scripts, styles, SVGs, footers),
        reducing token footprint by up to 90% while preserving e-commerce signals.
        """
        soup = BeautifulSoup(html, "html.parser")

        # Decompose non-content tags
        for tag in soup.find_all([
            "script", "style", "svg", "path", "noscript", "iframe",
            "nav", "footer", "header", "aside", "form"
        ]):
            tag.decompose()

        # Remove HTML comments
        from bs4 import Comment
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()

        # Strip base64 data URLs from images to save tokens
        for img in soup.find_all("img"):
            src = img.get("src", "")
            if src.startswith("data:"):
                img["src"] = "[inline-data-image]"

        cleaned = str(soup)
        # Collapse excessive whitespace
        import re
        cleaned = re.sub(r'\s+', ' ', cleaned)
        return cleaned[:max_chars]

    async def extract_products_with_ai(
        self,
        html: str,
        base_url: str,
        api_key: Optional[str] = None,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract structured product records from HTML using Gemini zero-shot extraction.
        """
        effective_key = self._get_api_key(api_key)
        if not effective_key:
            return {
                "success": False,
                "error": "Gemini API Key is required. Please provide it in the request or configure GEMINI_API_KEY in Settings.",
                "products": [],
            }

        target_model = model or self.default_model
        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{target_model}:generateContent?key={effective_key}"

        cleaned_html = self.clean_html_for_llm(html)

        system_instruction = (
            "You are an expert E-Commerce Web Scraping and Data Extraction engine. "
            "Analyze the provided HTML from an online store and extract all products found. "
            "Return a strictly valid JSON object with a single 'products' array. "
            "Each product object must contain:\n"
            "- name (string): Product title/name\n"
            "- price (number): Current price as a float/number (do not include currency symbols)\n"
            "- original_price (number or null): Strikethrough/previous price if on sale\n"
            "- currency (string): 3-letter currency code (e.g. USD, EUR, GBP, PKR, CAD)\n"
            "- brand (string or null): Manufacturer or brand\n"
            "- category (string or null): Category\n"
            "- in_stock (boolean): true if in stock, false if sold out\n"
            "- image_url (string or null): Image source URL\n"
            "- url (string or null): Link to product details\n"
            "- description (string or null): Brief description or features\n"
            "- rating (number or null): Star rating (0.0 to 5.0)\n"
            "- review_count (number or null): Total reviews\n"
            "- variants (array of objects, optional): all variations (sizes, colors, styles). Each variant must have: "
            "'name' (string, e.g. 'Red / XL'), 'sku' (string or null), 'price' (number or null), "
            "'in_stock' (boolean), 'stock_quantity' (number or null), 'stock_status' (string e.g. 'In Stock', 'Only 3 left', 'Out of Stock'), "
            "'attributes' (object e.g. {'color': 'Red', 'size': 'XL'}), 'image_url' (string or null)"
        )

        prompt = f"Extract all products from this e-commerce page HTML (Base URL: {base_url}):\n\n{cleaned_html}"

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": system_instruction},
                        {"text": prompt}
                    ]
                }
            ],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.1,
            }
        }

        try:
            async with httpx.AsyncClient(timeout=40.0) as client:
                res = await client.post(endpoint, json=payload)
                if res.status_code != 200:
                    err_msg = res.text[:300]
                    logger.error(f"Gemini API returned error {res.status_code}: {err_msg}")
                    return {
                        "success": False,
                        "error": f"Gemini API HTTP {res.status_code}: {err_msg}",
                        "products": [],
                    }

                data = res.json()
                candidates = data.get("candidates", [])
                if not candidates:
                    return {"success": False, "error": "No response returned by Gemini model", "products": []}

                content_parts = candidates[0].get("content", {}).get("parts", [])
                if not content_parts:
                    return {"success": False, "error": "Empty text response from Gemini", "products": []}

                text_response = content_parts[0].get("text", "{}")
                parsed = json.loads(text_response)

                raw_products = parsed.get("products", [])
                if isinstance(parsed, list):
                    raw_products = parsed

                # Normalize URLs
                products = []
                for p in raw_products:
                    if not isinstance(p, dict):
                        continue
                    if p.get("image_url"):
                        p["image_url"] = urljoin(base_url, p["image_url"])
                    if p.get("url"):
                        p["url"] = urljoin(base_url, p["url"])
                    products.append(p)

                return {
                    "success": True,
                    "products": products,
                    "count": len(products),
                    "model": target_model,
                }

        except Exception as e:
            logger.error(f"Error during AI product extraction: {e}")
            return {
                "success": False,
                "error": str(e),
                "products": [],
            }

    async def suggest_selectors_with_ai(
        self,
        html: str,
        base_url: str,
        api_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Ask Gemini to analyze the page HTML and automatically reverse-engineer
        the most optimal, robust CSS selectors for scraping.
        """
        effective_key = self._get_api_key(api_key)
        if not effective_key:
            return {
                "success": False,
                "error": "Gemini API Key is required. Please set GEMINI_API_KEY in Settings or provide an API Key.",
                "selectors": {},
            }

        target_model = self.default_model
        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{target_model}:generateContent?key={effective_key}"

        cleaned_html = self.clean_html_for_llm(html, max_chars=30000)

        system_instruction = (
            "You are an expert Web Scraping Engineer specializing in CSS selectors. "
            "Inspect this e-commerce page HTML and reverse-engineer the most robust, minimal CSS selectors "
            "to scrape product listings. Return a strictly valid JSON object with the following schema:\n"
            "{\n"
            "  \"selectors\": {\n"
            "    \"product_card\": \"CSS selector for each repeating product card/item container (e.g. .product-card, article.product)\",\n"
            "    \"product_name\": \"CSS selector for the product title relative to the card or page\",\n"
            "    \"product_price\": \"CSS selector for the product price element\",\n"
            "    \"product_image\": \"CSS selector for the product image element (e.g. img.product-img)\",\n"
            "    \"product_link\": \"CSS selector for the product link tag (e.g. a.product-link)\",\n"
            "    \"pagination_next\": \"CSS selector for next page pagination link (optional)\"\n"
            "  },\n"
            "  \"confidence\": 0.95,\n"
            "  \"reasoning\": \"Brief explanation of detected patterns\"\n"
            "}"
        )

        prompt = f"Analyze this store HTML and detect optimal CSS selectors:\n\n{cleaned_html}"

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": system_instruction},
                        {"text": prompt}
                    ]
                }
            ],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.1,
            }
        }

        try:
            async with httpx.AsyncClient(timeout=35.0) as client:
                res = await client.post(endpoint, json=payload)
                if res.status_code != 200:
                    return {
                        "success": False,
                        "error": f"Gemini API HTTP {res.status_code}: {res.text[:200]}",
                        "selectors": {},
                    }

                data = res.json()
                candidates = data.get("candidates", [])
                if not candidates:
                    return {"success": False, "error": "No response returned", "selectors": {}}

                text_response = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "{}")
                parsed = json.loads(text_response)

                return {
                    "success": True,
                    "selectors": parsed.get("selectors", {}),
                    "confidence": parsed.get("confidence", 0.9),
                    "reasoning": parsed.get("reasoning", "AI detected DOM structure"),
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "selectors": {},
            }

    async def test_api_key(self, api_key: str) -> Dict[str, Any]:
        """Test if the given Gemini API key is valid by querying the Gemini API."""
        if not api_key or not api_key.strip():
            return {"success": False, "message": "API key is required."}
        clean_key = api_key.strip()
        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{self.default_model}:generateContent?key={clean_key}"
        payload = {
            "contents": [{"parts": [{"text": "Hello, respond with OK."}]}],
            "generationConfig": {"maxOutputTokens": 10}
        }
        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                res = await client.post(endpoint, json=payload)
                if res.status_code == 200:
                    return {
                        "success": True,
                        "message": f"Successfully connected to Google Gemini ({self.default_model})!"
                    }
                try:
                    err_data = res.json()
                    msg = err_data.get("error", {}).get("message", f"HTTP {res.status_code}")
                except Exception:
                    msg = f"HTTP {res.status_code}: {res.text[:150]}"
                return {"success": False, "message": f"Gemini error: {msg}"}
        except Exception as e:
            return {"success": False, "message": f"Connection error: {str(e)}"}


ai_extractor_service = AIExtractorService()
