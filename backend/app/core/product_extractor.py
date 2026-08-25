"""
Product Extractor Module
------------------------
Responsible for extracting product data from HTML pages using CSS selectors.
"""

import logging
from typing import Dict, List, Any, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin

logger = logging.getLogger(__name__)


class ProductExtractor:
    """
    Generic product extractor using CSS selectors.
    """

    def __init__(self, selector_config: Optional[Dict[str, Any]] = None):
        # Default selectors for common e-commerce elements if none provided
        self.selector_config = selector_config or {
            "product_container": ".product, .product-item, .product-card, .product-tile, [data-product]",
            "fields": {
                "name": ".product-title, .product-name, .title, .name, h2, h3",
                "price": ".price, .product-price, .amount, .current-price, .money",
                "image_url": "img::attr(src), .product-image img::attr(src)",
                "url": "a::attr(href), .product-link::attr(href)"
            }
        }
        
        # Support alias 'product_card' for 'product_container' from UI/Schema
        if not self.selector_config.get("product_container") and self.selector_config.get("product_card"):
            self.selector_config["product_container"] = self.selector_config["product_card"]

    def extract(self, html: str, base_url: str) -> List[Dict[str, Any]]:
        """
        Extract product data from HTML safely.
        """
        products: List[Dict[str, Any]] = []

        try:
            soup = BeautifulSoup(html, "lxml")
        except Exception:
            logger.warning("Failed to parse HTML with lxml, falling back to html.parser")
            soup = BeautifulSoup(html, "html.parser")

        container_selector = self.selector_config.get("product_container")
        field_selectors = self.selector_config.get("fields", {})

        if not container_selector:
            return products

        containers = soup.select(container_selector)
        logger.debug(f"Found {len(containers)} potential product containers with {container_selector}")

        for container in containers:
            product: Dict[str, Any] = {}
            found_data = False

            for field, selector in field_selectors.items():
                try:
                    value = self._extract_field(container, selector, base_url)
                    if value:
                        product[field] = value
                        found_data = True
                except Exception as e:
                    logger.debug(f"Field extraction error for {field}: {e}")
                    product[field] = None

            # Only add if we found at least a name or price
            if found_data and (product.get("name") or product.get("price")):
                # Ensure URL is absolute
                if product.get("url"):
                    product["url"] = urljoin(base_url, product["url"])
                else:
                    product["url"] = base_url  # Fallback
                
                products.append(product)

        return products

    def _extract_field(self, container, selector: str, base_url: str):
        """
        Extract a single field value from container.
        Supports ::attr() syntax.
        """
        if not selector:
            return None

        # Handle multiple selectors separated by comma
        selectors = [s.strip() for s in selector.split(",")]
        
        for s in selectors:
            try:
                if "::attr(" in s:
                    css, attr = s.split("::attr(")
                    attr = attr.rstrip(")")
                    
                    if css:
                        element = container.select_one(css)
                    else:
                        element = container # Use container itself if no CSS provided
                        
                    if element:
                        value = element.get(attr)
                        if value: return value
                else:
                    element = container.select_one(s)
                    if element:
                        value = element.get_text(strip=True)
                        if value: return value
            except Exception:
                continue
                
        return None