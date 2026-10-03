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
        "mybigcommerce.com": "bigcommerce",
        "squarespace.com": "squarespace",
        "wixsite.com": "wix",
        "wix.com": "wix",
        "etsy.com": "etsy",
        "walmart.com": "walmart",
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
        },
        "bigcommerce": {
            "name": "BigCommerce",
            "indicators": ["cdn11.bigcommerce.com", "stencil-utils", "bigcommerce", "productGrid"],
            "selectors": {
                "product_card": "article.card, .productGrid .product",
                "product_name": ".card-title a, .card-title",
                "product_price": ".price--withoutTax, .price--main, .price",
                "product_image": ".card-img-container img, img",
                "product_link": ".card-title a, a.card-figure__link"
            }
        },
        "magento": {
            "name": "Magento",
            "indicators": ["mage/cookies.js", "Magento_", "mage-translation", "data-mage-init"],
            "selectors": {
                "product_card": ".item.product.product-item, .product-item",
                "product_name": "strong.product-item-name a, a.product-item-link",
                "product_price": "[data-price-type='finalPrice'] .price, .special-price .price, .price",
                "product_image": "img.product-image-photo, img",
                "product_link": "a.product-item-link, a"
            }
        },
        "squarespace": {
            "name": "Squarespace",
            "indicators": ["static1.squarespace.com", "Squarespace", "sqs-money-native"],
            "selectors": {
                "product_card": ".grid-item, .ProductList-item, article.ProductItem",
                "product_name": ".grid-title, .ProductList-title, .product-title",
                "product_price": ".product-price, .sqs-money-native, .price",
                "product_image": "img.grid-item-image, .ProductList-image img, img",
                "product_link": "a.grid-item-link, a"
            }
        },
        "wix": {
            "name": "Wix",
            "indicators": ["static.wixstatic.com", "wix-warmup-data", "data-hook=\"product-item-root\""],
            "selectors": {
                "product_card": "[data-hook='product-item-root'], li[data-hook='product-list-item']",
                "product_name": "[data-hook='product-item-name'], [data-hook='product-title']",
                "product_price": "[data-hook='product-item-price-to-pay'], [data-hook='formatted-primary-price'], .price",
                "product_image": "[data-hook='product-item-images'] img, img",
                "product_link": "a[data-hook='product-item-container'], a"
            }
        },
        "etsy": {
            "name": "Etsy",
            "indicators": ["etsystatic.com", "v2-listing-card", "etsy.com"],
            "selectors": {
                "product_card": "div.v2-listing-card, li.wt-list-unstyled .v2-listing-card",
                "product_name": "h3.v2-listing-card__title, h3",
                "product_price": ".currency-value, span.currency-value",
                "product_image": "img.wt-width-full, img",
                "product_link": "a.listing-link, a"
            }
        },
        "walmart": {
            "name": "Walmart",
            "indicators": ["walmartimages.com", "data-automation-id=\"product-price\"", "walmart.com"],
            "selectors": {
                "product_card": "div[data-item-id], div[data-testid='product-card']",
                "product_name": "span[data-automation-id='product-title'], [data-testid='product-title']",
                "product_price": "div[data-automation-id='product-price'] .w_iDh7, [data-testid='product-price']",
                "product_image": "img[data-testid='productTileImage'], img",
                "product_link": "a[link-identifier], a[data-automation-id='product-title-link']"
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

    async def detect_platform(
        self,
        url: str,
        html: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Detect platform inspecting HTTP headers, <meta name="generator">,
        HTML signatures, and domain patterns.
        """
        from app.scrapers.scraper_registry import ScraperRegistry
        return ScraperRegistry.detect_platform_detailed(
            url=url,
            html=html,
            headers=headers,
            fetch_if_needed=True
        )