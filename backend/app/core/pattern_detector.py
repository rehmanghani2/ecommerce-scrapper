"""
Pattern Detector Module
-----------------------
Automatically detects e-commerce platforms and discovers product selectors.
"""

import logging
from typing import Dict, List, Any, Optional
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class PatternDetector:
    """
    Detects e-commerce platforms and auto-discovers product selectors using heuristics.
    """

    # Domain keywords → platform mapping (for instant no-fetch detection)
    DOMAIN_PATTERNS = {
        "rs-online.com": "rs_online",
        "shopify.com": "shopify",
        "myshopify.com": "shopify",
        "woocommerce.com": "woocommerce",
        "magento.com": "magento",
        "bigcommerce.com": "bigcommerce",
        "prestashop.com": "prestashop",
        "amazon": "amazon",
        "ebay": "ebay",
        "daraz": "daraz",
    }

    PLATFORMS = {
        "shopify": {
            "name": "Shopify",
            "indicators": ["cdn.shopify.com", "shopify-section", "/collections/", "Shopify.theme"],
            "selectors": {
                "product_card": ".product-card, .product-item, .grid-product",
                "product_name": ".product-card__title, .product-title, h2, h3",
                "product_price": ".product-price, .price, .money",
                "product_image": "img::attr(src)",
                "product_link": "a::attr(href)"
            }
        },
        "woocommerce": {
            "name": "WooCommerce",
            "indicators": ["woocommerce", "wc-block", "wp-content/plugins/woocommerce"],
            "selectors": {
                "product_card": ".product, .type-product, li.product",
                "product_name": ".woocommerce-loop-product__title, .product-title, h2",
                "product_price": ".price, .woocommerce-Price-amount",
                "product_image": ".wp-post-image::attr(src)",
                "product_link": "a::attr(href)"
            }
        },
        "rs_online": {
            "name": "RS Online",
            "indicators": ["uk.rs-online.com", "data-testid=\"product-card\""],
            "selectors": {
                "product_card": "div[data-testid=\"product-card\"]",
                "product_name": "a[data-testid=\"product-card-title-link\"]",
                "product_price": ".items-baseline span.font-bold",
                "product_image": "img::attr(src)",
                "product_link": "a[data-testid=\"product-card-title-link\"]::attr(href)"
            }
        },
        "amazon": {
            "name": "Amazon",
            "indicators": ["amazon.com", "amazon.co.uk", "amazon.de"],
            "selectors": {
                "product_card": "div[data-component-type='s-search-result']",
                "product_name": "h2 a.a-link-normal span",
                "product_price": "span.a-price span.a-offscreen",
                "product_image": "img.s-image::attr(src)",
                "product_link": "h2 a.a-link-normal::attr(href)"
            }
        },
        "ebay": {
            "name": "eBay",
            "indicators": ["ebay.com", "ebay.co.uk", "ebay.de"],
            "selectors": {
                "product_card": ".s-item, li.s-item",
                "product_name": ".s-item__title",
                "product_price": ".s-item__price",
                "product_image": "img::attr(src)",
                "product_link": "a.s-item__link::attr(href)"
            }
        },
        "daraz": {
            "name": "Daraz",
            "indicators": ["daraz.pk", "daraz.com.np", "daraz.lk"],
            "selectors": {
                "product_card": "div[data-qa-locator='product-item']",
                "product_name": "a[title], div[class*='title']",
                "product_price": "span[class*='price']",
                "product_image": "img::attr(src)",
                "product_link": "a::attr(href)"
            }
        }
    }

    GENERIC_SELECTORS = {
        "product_card": ".product, .product-item, .product-card, .item, .card",
        "product_name": "h2, h3, .name, .title, .product-title",
        "product_price": ".price, .amount, .product-price",
        "product_image": "img::attr(src)",
        "product_link": "a::attr(href)"
    }

    async def analyze_page(self, html: str, url: str) -> Dict[str, Any]:
        """
        Analyze page HTML to detect platform and selectors.
        """
        # 1. Detect Platform
        platform_id = "unknown"
        platform_name = "Unknown"
        confidence = 0.0
        selectors = {}

        for pid, info in self.PLATFORMS.items():
            found_indicators = [i for i in info["indicators"] if i in html]
            if found_indicators:
                platform_id = pid
                platform_name = info["name"]
                confidence = len(found_indicators) / len(info["indicators"])
                selectors = info["selectors"]
                break

        # 2. Fallback to Generic if unknown or low confidence
        if platform_id == "unknown":
            selectors = self.GENERIC_SELECTORS
            confidence = 0.3 

        # 3. Try to extract sample products to verify selectors
        from app.core.product_extractor import ProductExtractor
        
        # Convert flat selectors to ProductExtractor format
        extractor_config = {
            "product_container": selectors.get("product_card"),
            "fields": {
                "name": selectors.get("product_name"),
                "price": selectors.get("product_price"),
                "image_url": selectors.get("product_image"),
                "url": selectors.get("product_link")
            }
        }
        
        extractor = ProductExtractor(extractor_config)
        sample_products = extractor.extract(html, url)

        # 4. Refine confidence based on results
        if sample_products:
            confidence = max(confidence, 0.8)
        
        return {
            "platform": platform_name,
            "confidence": confidence,
            "selectors": selectors,
            "sample_products": sample_products[:5]
        }

    def detect_by_domain(self, url: str) -> dict:
        """
        Instantly detect platform by checking the URL against known domain patterns.
        Returns selectors without fetching any page — works for known platforms
        like RS Online that require JavaScript rendering.
        """
        from urllib.parse import urlparse
        domain = urlparse(url).netloc.lower()

        for domain_key, platform_id in self.DOMAIN_PATTERNS.items():
            if domain_key in domain:
                info = self.PLATFORMS.get(platform_id, {})
                return {
                    "platform": info.get("name", platform_id),
                    "confidence": 0.9,
                    "selectors": info.get("selectors", self.GENERIC_SELECTORS),
                }

        return {
            "platform": "Unknown",
            "confidence": 0.0,
            "selectors": self.GENERIC_SELECTORS,
        }

    def get_generic_selectors(self) -> dict:
        """Return generic selectors as a fallback for unknown platforms."""
        return self.GENERIC_SELECTORS