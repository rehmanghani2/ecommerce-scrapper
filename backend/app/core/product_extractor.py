"""
product_extractor.py
--------------------
Selector‑driven, generic product extraction engine.

This module is OPTIONAL in the crawl pipeline and only runs when
product selectors are provided.

Design goals:
- Generic across 200+ ecommerce sites
- Selector‑configurable (no hardcoding)
- Safe: never crashes crawler
- Extensible for AI / pattern detection later
"""

from typing import Dict, List, Any

from bs4 import BeautifulSoup

from app.utils.logger import get_logger

logger = get_logger(__name__)


class ProductExtractor:
    """
    Generic product extractor using CSS selectors.

    Expected selector_config example:
    {
        "product_container": ".product-card",
        "fields": {
            "title": ".product-title",
            "price": ".price",
            "url": "a::attr(href)",
            "image": "img::attr(src)"
        }
    }
    """

    def __init__(self, selector_config: Dict[str, Any]):
        self.selector_config = selector_config

    def extract(self, html: str, base_url: str) -> List[Dict[str, Any]]:
        """
        Extract product data from HTML safely.
        Never raises exceptions.
        """
        products: List[Dict[str, Any]] = []

        try:
            soup = BeautifulSoup(html, "lxml")
        except Exception:
            logger.warning("Failed to parse HTML with lxml, using html.parser")
            soup = BeautifulSoup(html, "html.parser")

        container_selector = self.selector_config.get("product_container")
        field_selectors = self.selector_config.get("fields", {})

        if not container_selector or not field_selectors:
            logger.debug("No product selectors provided, skipping extraction")
            return products

        containers = soup.select(container_selector)

        for container in containers:
            product: Dict[str, Any] = {}

            for field, selector in field_selectors.items():
                try:
                    value = self._extract_field(container, selector, base_url)
                    product[field] = value
                except Exception:
                    product[field] = None

            if any(product.values()):
                products.append(product)

        return products

    def _extract_field(self, container, selector: str, base_url: str):
        """
        Extract a single field value from container.
        Supports ::attr() syntax.
        """
        if "::attr(" in selector:
            css, attr = selector.split("::attr(")
            attr = attr.rstrip(")")
            element = container.select_one(css)
            if not element:
                return None
            value = element.get(attr)
        else:
            element = container.select_one(selector)
            if not element:
                return None
            value = element.get_text(strip=True)

        if isinstance(value, str) and value.startswith("/"):
            from urllib.parse import urljoin
            value = urljoin(base_url, value)

        return value














# """
# Product Extractor Module
# Extracts product data from e-commerce web pages.
# """

# import re
# from typing import Dict, List, Any, Optional, Set
# from dataclasses import dataclass, field
# from urllib.parse import urljoin
# from playwright.async_api import Page, ElementHandle, TimeoutError as PlaywrightTimeout
# import logging

# from app.utils.helpers import (
#     extract_domain, 
#     is_valid_product_url
# )
# from app.core.data_cleaner import DataCleaner

# logger = logging.getLogger(__name__)


# @dataclass
# class ExtractionConfig:
#     """Configuration for product extraction."""
    
#     # Selectors for list pages
#     product_container: Optional[str] = None
#     product_card: Optional[str] = None
#     product_link: Optional[str] = None
#     product_name: Optional[str] = None
#     product_price: Optional[str] = None
#     product_image: Optional[str] = None
#     product_brand: Optional[str] = None
    
#     # Selectors for detail pages
#     detail_name: Optional[str] = None
#     detail_price: Optional[str] = None
#     detail_original_price: Optional[str] = None
#     detail_description: Optional[str] = None
#     detail_short_description: Optional[str] = None
#     detail_images: Optional[str] = None
#     detail_sku: Optional[str] = None
#     detail_brand: Optional[str] = None
#     detail_category: Optional[str] = None
#     detail_breadcrumb: Optional[str] = None
#     detail_specifications: Optional[str] = None
#     detail_features: Optional[str] = None
#     detail_availability: Optional[str] = None
#     detail_rating: Optional[str] = None
#     detail_review_count: Optional[str] = None
#     detail_variants: Optional[str] = None
    
#     # Extraction options
#     extract_from_json_ld: bool = True
#     extract_from_meta: bool = True
#     extract_from_microdata: bool = True
#     follow_product_links: bool = True
#     include_variants: bool = True
#     include_images: bool = True
#     include_specifications: bool = True
    
#     # Timeouts
#     wait_for_selector: Optional[str] = None
#     wait_timeout: int = 5000


# @dataclass
# class ExtractionStats:
#     """Statistics for extraction operations."""
#     pages_processed: int = 0
#     products_extracted: int = 0
#     products_from_list: int = 0
#     products_from_detail: int = 0
#     products_from_json_ld: int = 0
#     failed_extractions: int = 0
#     errors: List[str] = field(default_factory=list)


# class ProductExtractor:
#     """
#     Extracts product data from e-commerce web pages.
    
#     Features:
#     - Extract from product listing pages
#     - Extract from product detail pages
#     - JSON-LD structured data extraction
#     - Meta tag extraction
#     - Microdata extraction
#     - Image extraction
#     - Variant extraction
#     - Specification extraction
#     """
    
#     # Default selectors for common elements
#     DEFAULT_SELECTORS = {
#         # List page selectors
#         'product_card': [
#             '.product', '.product-item', '.product-card', '.product-tile',
#             '[data-product]', '.item', '.grid-item', 'article.product',
#             '.product-grid-item', '.collection-product', '.shop-item',
#         ],
#         'product_link': [
#             'a[href*="/product"]', 'a[href*="/p/"]', 'a[href*="/pd/"]',
#             'a[href*="/item"]', '.product-link', '.product-url',
#             'h2 a', 'h3 a', '.product-title a', '.product-name a',
#         ],
#         'product_name': [
#             '.product-name', '.product-title', '.title', '.name',
#             'h2', 'h3', 'h4', '[data-product-name]', '.item-name',
#         ],
#         'product_price': [
#             '.price', '.product-price', '[data-price]', '.amount',
#             '.current-price', '.sale-price', '.regular-price',
#             '.money', 'span.price', '.offer-price',
#         ],
#         'product_image': [
#             '.product-image img', '.product-img img', 'img.product-image',
#             '.image img', '.thumbnail img', '[data-product-image]',
#             'img[data-src]', '.lazy-image', 'picture img',
#         ],
        
#         # Detail page selectors
#         'detail_name': [
#             'h1', '.product-title', '.product-name', '[data-product-title]',
#             '.pdp-title', '.product-detail-title', '#product-name',
#         ],
#         'detail_price': [
#             '.product-price', '.price', '[data-product-price]',
#             '.current-price', '.sale-price', '#product-price',
#             '.pdp-price', '.product-detail-price',
#         ],
#         'detail_original_price': [
#             '.original-price', '.was-price', '.compare-price',
#             '.regular-price', 'del .price', '.price-was', 's .price',
#         ],
#         'detail_description': [
#             '.product-description', '.description', '#description',
#             '[data-product-description]', '.pdp-description',
#             '.product-detail-description', '.product-info',
#         ],
#         'detail_images': [
#             '.product-gallery img', '.product-images img',
#             '.gallery img', '.product-photos img', '.pdp-image',
#             '[data-product-images] img', '.carousel img',
#         ],
#         'detail_sku': [
#             '.sku', '[data-sku]', '.product-sku', '#sku',
#             '[itemprop="sku"]', '.product-code', '.item-number',
#         ],
#         'detail_brand': [
#             '.brand', '.product-brand', '[data-brand]', '[itemprop="brand"]',
#             '.manufacturer', '.vendor', '.product-vendor',
#         ],
#         'detail_breadcrumb': [
#             '.breadcrumb', '.breadcrumbs', 'nav[aria-label="breadcrumb"]',
#             '.product-breadcrumb', '#breadcrumb', '.crumbs',
#         ],
#         'detail_availability': [
#             '.availability', '.stock-status', '[data-availability]',
#             '.in-stock', '.out-of-stock', '.stock', '.product-availability',
#         ],
#         'detail_rating': [
#             '.rating', '.star-rating', '[data-rating]', '.review-rating',
#             '.product-rating', '.stars', '[itemprop="ratingValue"]',
#         ],
#         'detail_specifications': [
#             '.specifications', '.specs', '.product-specs',
#             '.technical-specs', '.product-attributes', 'table.specs',
#             '.spec-table', '#specifications', '.attributes',
#         ],
#     }
    
#     def __init__(
#         self, 
#         config: Optional[ExtractionConfig] = None,
#         base_url: Optional[str] = None
#     ):
#         """
#         Initialize the product extractor.
        
#         Args:
#             config: Extraction configuration
#             base_url: Base URL for the website
#         """
#         self.config = config or ExtractionConfig()
#         self.base_url = base_url
#         self.domain = extract_domain(base_url) if base_url else None
#         self.stats = ExtractionStats()
#         self._data_cleaner = DataCleaner(base_url=base_url)
#         self._extracted_urls: Set[str] = set()
    
#     def set_selectors(self, selectors: Dict[str, str]) -> None:
#         """
#         Set custom selectors for extraction.
        
#         Args:
#             selectors: Dictionary of selector name to CSS selector
#         """
#         for key, value in selectors.items():
#             if hasattr(self.config, key):
#                 setattr(self.config, key, value)
    
#     async def extract_from_listing_page(
#         self, 
#         page: Page,
#         follow_links: bool = True
#     ) -> List[Dict[str, Any]]:
#         """
#         Extract products from a listing/category page.
        
#         Args:
#             page: Playwright page
#             follow_links: Whether to follow product links for details
        
#         Returns:
#             List of extracted products
#         """
#         self.stats.pages_processed += 1
#         products = []
        
#         try:
#             # First try JSON-LD extraction
#             if self.config.extract_from_json_ld:
#                 json_ld_products = await self._extract_json_ld_products(page)
#                 if json_ld_products:
#                     products.extend(json_ld_products)
#                     self.stats.products_from_json_ld += len(json_ld_products)
            
#             # Extract from DOM
#             dom_products = await self._extract_products_from_dom(page)
            
#             # Merge JSON-LD with DOM data
#             products = self._merge_product_data(products, dom_products)
            
#             # Follow product links for details if enabled
#             if follow_links and self.config.follow_product_links:
#                 products = await self._enrich_with_detail_pages(page, products)
            
#             self.stats.products_from_list += len(products)
#             self.stats.products_extracted += len(products)
            
#             logger.info(f"Extracted {len(products)} products from listing page")
            
#         except Exception as e:
#             self.stats.failed_extractions += 1
#             self.stats.errors.append(f"Listing extraction error: {str(e)}")
#             logger.error(f"Failed to extract from listing page: {e}")
        
#         return products
    
#     async def extract_from_detail_page(
#         self, 
#         page: Page,
#         basic_data: Optional[Dict[str, Any]] = None
#     ) -> Optional[Dict[str, Any]]:
#         """
#         Extract detailed product information from a product page.
        
#         Args:
#             page: Playwright page
#             basic_data: Basic product data from listing page
        
#         Returns:
#             Extracted product dict or None
#         """
#         self.stats.pages_processed += 1
#         product = basic_data.copy() if basic_data else {}
        
#         try:
#             # Set URL
#             product['url'] = page.url
            
#             # Wait for content if configured
#             if self.config.wait_for_selector:
#                 try:
#                     await page.wait_for_selector(
#                         self.config.wait_for_selector,
#                         timeout=self.config.wait_timeout
#                     )
#                 except PlaywrightTimeout:
#                     logger.warning(f"Timeout waiting for selector on {page.url}")
            
#             # Extract from JSON-LD first (most reliable)
#             if self.config.extract_from_json_ld:
#                 json_ld_data = await self._extract_json_ld_product(page)
#                 if json_ld_data:
#                     product = self._merge_single_product(product, json_ld_data)
            
#             # Extract from meta tags
#             if self.config.extract_from_meta:
#                 meta_data = await self._extract_meta_product(page)
#                 if meta_data:
#                     product = self._merge_single_product(product, meta_data)
            
#             # Extract from DOM
#             dom_data = await self._extract_detail_from_dom(page)
#             if dom_data:
#                 product = self._merge_single_product(product, dom_data)
            
#             # Extract images
#             if self.config.include_images:
#                 images = await self._extract_images(page)
#                 if images:
#                     product['images'] = images
#                     if not product.get('image_url') and images:
#                         product['image_url'] = images[0].get('url')
            
#             # Extract variants
#             if self.config.include_variants:
#                 variants = await self._extract_variants(page)
#                 if variants:
#                     product['variants'] = variants
            
#             # Extract specifications
#             if self.config.include_specifications:
#                 specs = await self._extract_specifications(page)
#                 if specs:
#                     product['specifications'] = specs
            
#             # Clean the product data
#             cleaned = self._data_cleaner.clean_product(product)
            
#             if cleaned:
#                 self.stats.products_from_detail += 1
#                 self.stats.products_extracted += 1
#                 logger.debug(f"Extracted product: {cleaned.get('name', 'Unknown')}")
#                 return cleaned
            
#         except Exception as e:
#             self.stats.failed_extractions += 1
#             self.stats.errors.append(f"Detail extraction error: {str(e)}")
#             logger.error(f"Failed to extract from detail page {page.url}: {e}")
        
#         return None
    
#     async def _extract_products_from_dom(self, page: Page) -> List[Dict[str, Any]]:
#         """Extract products from DOM elements."""
#         products = []
        
#         # Find product container
#         card_selector = self.config.product_card or await self._find_working_selector(
#             page, self.DEFAULT_SELECTORS['product_card']
#         )
        
#         if not card_selector:
#             logger.warning("No product card selector found")
#             return products
        
#         try:
#             cards = await page.query_selector_all(card_selector)
#             logger.debug(f"Found {len(cards)} product cards with selector: {card_selector}")
            
#             for card in cards:
#                 product = await self._extract_product_from_card(card, page.url)
#                 if product and product.get('name'):
#                     products.append(product)
            
#         except Exception as e:
#             logger.warning(f"Error extracting products from DOM: {e}")
        
#         return products
    
#     async def _extract_product_from_card(
#         self, 
#         card: ElementHandle,
#         page_url: str
#     ) -> Optional[Dict[str, Any]]:
#         """Extract product data from a single product card."""
#         product = {}
        
#         try:
#             # Extract name
#             name_selector = self.config.product_name
#             name_element = None
            
#             if name_selector:
#                 name_element = await card.query_selector(name_selector)
#             else:
#                 for selector in self.DEFAULT_SELECTORS['product_name']:
#                     name_element = await card.query_selector(selector)
#                     if name_element:
#                         break
            
#             if name_element:
#                 product['name'] = await name_element.inner_text()
            
#             # Extract link/URL
#             link_selector = self.config.product_link
#             link_element = None
            
#             if link_selector:
#                 link_element = await card.query_selector(link_selector)
#             else:
#                 for selector in self.DEFAULT_SELECTORS['product_link']:
#                     link_element = await card.query_selector(selector)
#                     if link_element:
#                         break
                
#                 # Fallback: check if card itself is a link
#                 if not link_element:
#                     link_element = await card.query_selector('a')
            
#             if link_element:
#                 href = await link_element.get_attribute('href')
#                 if href:
#                     product['url'] = urljoin(page_url, href)
            
#             # Extract price
#             price_selector = self.config.product_price
#             price_element = None
            
#             if price_selector:
#                 price_element = await card.query_selector(price_selector)
#             else:
#                 for selector in self.DEFAULT_SELECTORS['product_price']:
#                     price_element = await card.query_selector(selector)
#                     if price_element:
#                         break
            
#             if price_element:
#                 product['price'] = await price_element.inner_text()
            
#             # Extract image
#             image_selector = self.config.product_image
#             image_element = None
            
#             if image_selector:
#                 image_element = await card.query_selector(image_selector)
#             else:
#                 for selector in self.DEFAULT_SELECTORS['product_image']:
#                     image_element = await card.query_selector(selector)
#                     if image_element:
#                         break
                
#                 # Fallback: any image
#                 if not image_element:
#                     image_element = await card.query_selector('img')
            
#             if image_element:
#                 img_url = (
#                     await image_element.get_attribute('src') or
#                     await image_element.get_attribute('data-src') or
#                     await image_element.get_attribute('data-lazy-src') or
#                     await image_element.get_attribute('data-original')
#                 )
#                 if img_url:
#                     product['image_url'] = urljoin(page_url, img_url)
            
#             # Extract brand if available
#             brand_selector = self.config.product_brand
#             if brand_selector:
#                 brand_element = await card.query_selector(brand_selector)
#                 if brand_element:
#                     product['brand'] = await brand_element.inner_text()
            
#             # Extract product ID from data attributes
#             product_id = (
#                 await card.get_attribute('data-product-id') or
#                 await card.get_attribute('data-id') or
#                 await card.get_attribute('data-item-id') or
#                 await card.get_attribute('id')
#             )
#             if product_id:
#                 product['product_id'] = product_id
            
#             return product if product.get('name') or product.get('url') else None
            
#         except Exception as e:
#             logger.debug(f"Error extracting from product card: {e}")
#             return None
    
#     async def _extract_detail_from_dom(self, page: Page) -> Dict[str, Any]:
#         """Extract product details from DOM."""
#         product = {}
        
#         try:
#             # Name
#             name = await self._extract_element_text(
#                 page,
#                 self.config.detail_name,
#                 self.DEFAULT_SELECTORS['detail_name']
#             )
#             if name:
#                 product['name'] = name
            
#             # Price
#             price = await self._extract_element_text(
#                 page,
#                 self.config.detail_price,
#                 self.DEFAULT_SELECTORS['detail_price']
#             )
#             if price:
#                 product['price'] = price
            
#             # Original price
#             orig_price = await self._extract_element_text(
#                 page,
#                 self.config.detail_original_price,
#                 self.DEFAULT_SELECTORS['detail_original_price']
#             )
#             if orig_price:
#                 product['original_price'] = orig_price
            
#             # Description
#             description = await self._extract_element_text(
#                 page,
#                 self.config.detail_description,
#                 self.DEFAULT_SELECTORS['detail_description']
#             )
#             if description:
#                 product['description'] = description
            
#             # SKU
#             sku = await self._extract_element_text(
#                 page,
#                 self.config.detail_sku,
#                 self.DEFAULT_SELECTORS['detail_sku']
#             )
#             if sku:
#                 product['sku'] = sku
            
#             # Brand
#             brand = await self._extract_element_text(
#                 page,
#                 self.config.detail_brand,
#                 self.DEFAULT_SELECTORS['detail_brand']
#             )
#             if brand:
#                 product['brand'] = brand
            
#             # Breadcrumb/Category
#             breadcrumb = await self._extract_breadcrumb(page)
#             if breadcrumb:
#                 product['category_path'] = breadcrumb.get('path')
#                 product['category'] = breadcrumb.get('category')
#                 product['subcategory'] = breadcrumb.get('subcategory')
            
#             # Availability
#             availability = await self._extract_element_text(
#                 page,
#                 self.config.detail_availability,
#                 self.DEFAULT_SELECTORS['detail_availability']
#             )
#             if availability:
#                 product['stock_status'] = availability
            
#             # Rating
#             rating = await self._extract_rating(page)
#             if rating:
#                 product['rating'] = rating.get('value')
#                 product['review_count'] = rating.get('count')
            
#         except Exception as e:
#             logger.warning(f"Error extracting detail from DOM: {e}")
        
#         return product
    
#     async def _extract_json_ld_products(self, page: Page) -> List[Dict[str, Any]]:
#         """Extract products from JSON-LD structured data."""
#         products = []
        
#         try:
#             json_ld_data = await page.evaluate('''
#                 () => {
#                     const scripts = document.querySelectorAll('script[type="application/ld+json"]');
#                     const data = [];
#                     scripts.forEach(script => {
#                         try {
#                             data.push(JSON.parse(script.textContent));
#                         } catch (e) {}
#                     });
#                     return data;
#                 }
#             ''')
            
#             for item in json_ld_data:
#                 products.extend(self._parse_json_ld_item(item))
            
#         except Exception as e:
#             logger.debug(f"Error extracting JSON-LD: {e}")
        
#         return products
    
#     async def _extract_json_ld_product(self, page: Page) -> Optional[Dict[str, Any]]:
#         """Extract single product from JSON-LD."""
#         products = await self._extract_json_ld_products(page)
#         return products[0] if products else None
    
#     def _parse_json_ld_item(
#         self, 
#         item: Any, 
#         products: List[Dict[str, Any]] = None
#     ) -> List[Dict[str, Any]]:
#         """Parse JSON-LD item recursively."""
#         if products is None:
#             products = []
        
#         if isinstance(item, list):
#             for sub_item in item:
#                 self._parse_json_ld_item(sub_item, products)
        
#         elif isinstance(item, dict):
#             item_type = item.get('@type', '')
            
#             # Handle Product type
#             if item_type == 'Product' or 'Product' in str(item_type):
#                 product = self._extract_product_from_json_ld(item)
#                 if product:
#                     products.append(product)
            
#             # Handle ItemList with products
#             elif item_type == 'ItemList':
#                 items = item.get('itemListElement', [])
#                 for list_item in items:
#                     if isinstance(list_item, dict):
#                         item_content = list_item.get('item', list_item)
#                         self._parse_json_ld_item(item_content, products)
            
#             # Handle WebPage with main entity
#             elif item_type in ('WebPage', 'CollectionPage', 'SearchResultsPage'):
#                 main_entity = item.get('mainEntity')
#                 if main_entity:
#                     self._parse_json_ld_item(main_entity, products)
            
#             # Check @graph
#             if '@graph' in item:
#                 self._parse_json_ld_item(item['@graph'], products)
        
#         return products
    
#     def _extract_product_from_json_ld(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
#         """Extract product data from JSON-LD Product object."""
#         try:
#             product = {}
            
#             # Basic info
#             product['name'] = data.get('name', '')
#             product['description'] = data.get('description', '')
#             product['url'] = data.get('url', '')
#             product['sku'] = data.get('sku', '')
#             product['product_id'] = data.get('productID') or data.get('identifier', '')
            
#             # Brand
#             brand = data.get('brand')
#             if isinstance(brand, dict):
#                 product['brand'] = brand.get('name', '')
#             elif isinstance(brand, str):
#                 product['brand'] = brand
            
#             # Image
#             image = data.get('image')
#             if isinstance(image, list):
#                 product['image_url'] = image[0] if image else ''
#                 product['images'] = [{'url': img} for img in image]
#             elif isinstance(image, str):
#                 product['image_url'] = image
#             elif isinstance(image, dict):
#                 product['image_url'] = image.get('url', '')
            
#             # Price (from offers)
#             offers = data.get('offers')
#             if offers:
#                 if isinstance(offers, list):
#                     offers = offers[0]
                
#                 if isinstance(offers, dict):
#                     product['price'] = offers.get('price', '')
#                     product['currency'] = offers.get('priceCurrency', 'GBP')
                    
#                     # Availability
#                     availability = offers.get('availability', '')
#                     if 'InStock' in availability:
#                         product['in_stock'] = True
#                     elif 'OutOfStock' in availability:
#                         product['in_stock'] = False
            
#             # Rating
#             rating = data.get('aggregateRating')
#             if rating:
#                 product['rating'] = rating.get('ratingValue')
#                 product['review_count'] = rating.get('reviewCount')
            
#             # Category
#             category = data.get('category')
#             if isinstance(category, list):
#                 product['category_path'] = ' > '.join(category)
#             elif isinstance(category, str):
#                 product['category'] = category
            
#             return product if product.get('name') else None
            
#         except Exception as e:
#             logger.debug(f"Error parsing JSON-LD product: {e}")
#             return None
    
#     async def _extract_meta_product(self, page: Page) -> Optional[Dict[str, Any]]:
#         """Extract product data from meta tags."""
#         try:
#             meta_data = await page.evaluate('''
#                 () => {
#                     const getMeta = (name) => {
#                         const el = document.querySelector(
#                             `meta[property="${name}"], meta[name="${name}"]`
#                         );
#                         return el ? el.getAttribute('content') : null;
#                     };
                    
#                     return {
#                         name: getMeta('og:title') || getMeta('twitter:title'),
#                         description: getMeta('og:description') || getMeta('description'),
#                         image_url: getMeta('og:image') || getMeta('twitter:image'),
#                         url: getMeta('og:url'),
#                         price: getMeta('product:price:amount') || getMeta('og:price:amount'),
#                         currency: getMeta('product:price:currency') || getMeta('og:price:currency'),
#                         availability: getMeta('product:availability'),
#                         brand: getMeta('product:brand'),
#                         sku: getMeta('product:sku') || getMeta('product:retailer_item_id'),
#                     };
#                 }
#             ''')
            
#             # Filter out None values
#             return {k: v for k, v in meta_data.items() if v} or None
            
#         except Exception as e:
#             logger.debug(f"Error extracting meta tags: {e}")
#             return None
    
#     async def _extract_images(self, page: Page) -> List[Dict[str, Any]]:
#         """Extract product images."""
#         images = []
#         seen_urls = set()
        
#         try:
#             # Find gallery images
#             selector = self.config.detail_images
#             if selector:
#                 elements = await page.query_selector_all(selector)
#             else:
#                 elements = []
#                 for sel in self.DEFAULT_SELECTORS['detail_images']:
#                     elements = await page.query_selector_all(sel)
#                     if elements:
#                         break
            
#             # Also check for thumbnails
#             if not elements:
#                 elements = await page.query_selector_all(
#                     '.product-image img, .product-photo img, [data-zoom-image]'
#                 )
            
#             for i, element in enumerate(elements):
#                 try:
#                     # Get various image sources
#                     url = (
#                         await element.get_attribute('data-zoom-image') or
#                         await element.get_attribute('data-large') or
#                         await element.get_attribute('data-src') or
#                         await element.get_attribute('src')
#                     )
                    
#                     if url and url not in seen_urls:
#                         full_url = urljoin(page.url, url)
                        
#                         # Skip tiny images and icons
#                         if not self._is_valid_product_image(full_url):
#                             continue
                        
#                         alt = await element.get_attribute('alt') or ''
                        
#                         images.append({
#                             'url': full_url,
#                             'alt_text': alt,
#                             'position': i,
#                             'is_primary': i == 0
#                         })
#                         seen_urls.add(url)
                        
#                 except Exception:
#                     continue
            
#         except Exception as e:
#             logger.debug(f"Error extracting images: {e}")
        
#         return images[:20]  # Limit to 20 images
    
#     async def _extract_variants(self, page: Page) -> List[Dict[str, Any]]:
#         """Extract product variants."""
#         variants = []
        
#         try:
#             # Try to find variant data in JavaScript
#             variant_data = await page.evaluate('''
#                 () => {
#                     // Shopify style
#                     if (window.ShopifyAnalytics && window.ShopifyAnalytics.meta) {
#                         return window.ShopifyAnalytics.meta.product;
#                     }
                    
#                     // Look for variant JSON
#                     const scripts = document.querySelectorAll('script');
#                     for (const script of scripts) {
#                         const text = script.textContent;
#                         if (text.includes('variants') && text.includes('price')) {
#                             const match = text.match(/variants['"\\s]*:[\\s]*(\[[\s\S]*?\])/);
#                             if (match) {
#                                 try {
#                                     return { variants: JSON.parse(match[1]) };
#                                 } catch (e) {}
#                             }
#                         }
#                     }
                    
#                     return null;
#                 }
#             ''')
            
#             if variant_data and variant_data.get('variants'):
#                 for v in variant_data['variants']:
#                     variant = {
#                         'variant_id': str(v.get('id', '')),
#                         'name': v.get('title') or v.get('name', ''),
#                         'sku': v.get('sku', ''),
#                         'price': v.get('price'),
#                         'in_stock': v.get('available', True),
#                         'attributes': {}
#                     }
                    
#                     # Extract option values
#                     for i in range(1, 4):
#                         option_key = f'option{i}'
#                         if v.get(option_key):
#                             variant['attributes'][f'option{i}'] = v[option_key]
                    
#                     if variant.get('name') or variant.get('sku'):
#                         variants.append(variant)
            
#             # DOM-based variant extraction
#             if not variants:
#                 variants = await self._extract_variants_from_dom(page)
            
#         except Exception as e:
#             logger.debug(f"Error extracting variants: {e}")
        
#         return variants
    
#     async def _extract_variants_from_dom(self, page: Page) -> List[Dict[str, Any]]:
#         """Extract variants from DOM elements."""
#         variants = []
        
#         try:
#             # Find variant selectors
#             selectors = await page.query_selector_all(
#                 'select[name*="variant"], select[name*="option"], '
#                 '[data-variant-option], .variant-option'
#             )
            
#             for selector in selectors:
#                 options = await selector.query_selector_all('option')
#                 for option in options:
#                     value = await option.get_attribute('value')
#                     text = await option.inner_text()
                    
#                     if value and text and text.strip():
#                         variants.append({
#                             'variant_id': value,
#                             'name': text.strip(),
#                             'attributes': {'option': text.strip()}
#                         })
            
#             # Check for swatch/button variants
#             if not variants:
#                 swatches = await page.query_selector_all(
#                     '[data-variant-id], .swatch-option, .variant-button'
#                 )
                
#                 for swatch in swatches:
#                     variant_id = await swatch.get_attribute('data-variant-id')
#                     name = (
#                         await swatch.get_attribute('data-value') or
#                         await swatch.get_attribute('title') or
#                         await swatch.inner_text()
#                     )
                    
#                     if name:
#                         variants.append({
#                             'variant_id': variant_id or '',
#                             'name': name.strip(),
#                             'attributes': {}
#                         })
            
#         except Exception as e:
#             logger.debug(f"Error extracting variants from DOM: {e}")
        
#         return variants
    
#     async def _extract_specifications(self, page: Page) -> Dict[str, str]:
#         """Extract product specifications."""
#         specs = {}
        
#         try:
#             # Find specification table/list
#             spec_container = None
            
#             selector = self.config.detail_specifications
#             if selector:
#                 spec_container = await page.query_selector(selector)
#             else:
#                 for sel in self.DEFAULT_SELECTORS['detail_specifications']:
#                     spec_container = await page.query_selector(sel)
#                     if spec_container:
#                         break
            
#             if spec_container:
#                 # Try table format
#                 rows = await spec_container.query_selector_all('tr')
#                 if rows:
#                     for row in rows:
#                         cells = await row.query_selector_all('td, th')
#                         if len(cells) >= 2:
#                             key = await cells[0].inner_text()
#                             value = await cells[1].inner_text()
#                             if key and value:
#                                 specs[key.strip()] = value.strip()
                
#                 # Try definition list format
#                 if not specs:
#                     dts = await spec_container.query_selector_all('dt')
#                     dds = await spec_container.query_selector_all('dd')
                    
#                     for dt, dd in zip(dts, dds):
#                         key = await dt.inner_text()
#                         value = await dd.inner_text()
#                         if key and value:
#                             specs[key.strip()] = value.strip()
                
#                 # Try list format
#                 if not specs:
#                     items = await spec_container.query_selector_all('li')
#                     for item in items:
#                         text = await item.inner_text()
#                         if ':' in text:
#                             parts = text.split(':', 1)
#                             specs[parts[0].strip()] = parts[1].strip()
            
#         except Exception as e:
#             logger.debug(f"Error extracting specifications: {e}")
        
#         return specs
    
#     async def _extract_breadcrumb(self, page: Page) -> Optional[Dict[str, Any]]:
#         """Extract breadcrumb/category information."""
#         try:
#             breadcrumb_container = None
            
#             for sel in self.DEFAULT_SELECTORS['detail_breadcrumb']:
#                 breadcrumb_container = await page.query_selector(sel)
#                 if breadcrumb_container:
#                     break
            
#             if not breadcrumb_container:
#                 return None
            
#             # Get breadcrumb items
#             items = await breadcrumb_container.query_selector_all('a, span, li')
#             categories = []
            
#             for item in items:
#                 text = await item.inner_text()
#                 text = text.strip()
                
#                 # Skip separators and home
#                 if text and text not in ('>', '/', '›', '»', 'Home', 'home'):
#                     categories.append(text)
            
#             if categories:
#                 return {
#                     'path': ' > '.join(categories),
#                     'category': categories[0] if categories else None,
#                     'subcategory': categories[1] if len(categories) > 1 else None,
#                     'categories': categories
#                 }
            
#         except Exception as e:
#             logger.debug(f"Error extracting breadcrumb: {e}")
        
#         return None
    
#     async def _extract_rating(self, page: Page) -> Optional[Dict[str, Any]]:
#         """Extract product rating."""
#         try:
#             rating_container = None
            
#             for sel in self.DEFAULT_SELECTORS['detail_rating']:
#                 rating_container = await page.query_selector(sel)
#                 if rating_container:
#                     break
            
#             if not rating_container:
#                 return None
            
#             result = {}
            
#             # Try to get rating value
#             rating_value = await rating_container.get_attribute('data-rating')
#             if not rating_value:
#                 # Look for aria-label
#                 aria_label = await rating_container.get_attribute('aria-label')
#                 if aria_label:
#                     match = re.search(r'(\d+(?:\.\d+)?)', aria_label)
#                     if match:
#                         rating_value = match.group(1)
            
#             if not rating_value:
#                 # Get text content
#                 text = await rating_container.inner_text()
#                 match = re.search(r'(\d+(?:\.\d+)?)', text)
#                 if match:
#                     rating_value = match.group(1)
            
#             if rating_value:
#                 result['value'] = float(rating_value)
            
#             # Try to get review count
#             review_count_el = await page.query_selector(
#                 '.review-count, .reviews-count, [itemprop="reviewCount"]'
#             )
#             if review_count_el:
#                 text = await review_count_el.inner_text()
#                 match = re.search(r'(\d+)', text.replace(',', ''))
#                 if match:
#                     result['count'] = int(match.group(1))
            
#             return result if result else None
            
#         except Exception as e:
#             logger.debug(f"Error extracting rating: {e}")
#             return None
    
#     async def _extract_element_text(
#         self,
#         page: Page,
#         custom_selector: Optional[str],
#         default_selectors: List[str]
#     ) -> Optional[str]:
#         """Extract text from an element using provided selectors."""
#         try:
#             element = None
            
#             if custom_selector:
#                 element = await page.query_selector(custom_selector)
#             else:
#                 for selector in default_selectors:
#                     element = await page.query_selector(selector)
#                     if element:
#                         break
            
#             if element:
#                 text = await element.inner_text()
#                 return text.strip() if text else None
            
#         except Exception:
#             pass
        
#         return None
    
#     async def _find_working_selector(
#         self, 
#         page: Page, 
#         selectors: List[str]
#     ) -> Optional[str]:
#         """Find the first selector that matches elements."""
#         for selector in selectors:
#             try:
#                 elements = await page.query_selector_all(selector)
#                 if elements:
#                     return selector
#             except Exception:
#                 continue
#         return None
    
#     async def _enrich_with_detail_pages(
#         self,
#         page: Page,
#         products: List[Dict[str, Any]]
#     ) -> List[Dict[str, Any]]:
#         """Enrich products by visiting their detail pages."""
#         enriched = []
        
#         for product in products:
#             url = product.get('url')
            
#             if not url or url in self._extracted_urls:
#                 enriched.append(product)
#                 continue
            
#             if not is_valid_product_url(url, self.domain):
#                 enriched.append(product)
#                 continue
            
#             try:
#                 # Navigate to detail page
#                 await page.goto(url, wait_until='domcontentloaded')
#                 await page.wait_for_timeout(1000)
                
#                 # Extract detailed data
#                 detailed = await self.extract_from_detail_page(page, product)
                
#                 if detailed:
#                     enriched.append(detailed)
#                     self._extracted_urls.add(url)
#                 else:
#                     enriched.append(product)
                    
#             except Exception as e:
#                 logger.warning(f"Failed to enrich product from {url}: {e}")
#                 enriched.append(product)
        
#         return enriched
    
#     def _merge_product_data(
#         self,
#         primary: List[Dict[str, Any]],
#         secondary: List[Dict[str, Any]]
#     ) -> List[Dict[str, Any]]:
#         """Merge two lists of products, preferring primary data."""
#         if not primary:
#             return secondary
#         if not secondary:
#             return primary
        
#         # Create lookup by URL
#         primary_by_url = {p.get('url', ''): p for p in primary if p.get('url')}
        
#         merged = list(primary)
        
#         for product in secondary:
#             url = product.get('url', '')
#             if url and url in primary_by_url:
#                 # Merge into existing product
#                 existing = primary_by_url[url]
#                 for key, value in product.items():
#                     if value and not existing.get(key):
#                         existing[key] = value
#             elif product.get('name'):
#                 # Add as new product
#                 merged.append(product)
        
#         return merged
    
#     def _merge_single_product(
#         self,
#         primary: Dict[str, Any],
#         secondary: Dict[str, Any]
#     ) -> Dict[str, Any]:
#         """Merge two product dicts, preferring primary data."""
#         result = primary.copy()
        
#         for key, value in secondary.items():
#             if value and not result.get(key):
#                 result[key] = value
        
#         return result
    
#     def _is_valid_product_image(self, url: str) -> bool:
#         """Check if URL is a valid product image."""
#         if not url:
#             return False
        
#         url_lower = url.lower()
        
#         # Skip common non-product images
#         invalid_patterns = [
#             'logo', 'icon', 'placeholder', 'spacer', 'blank',
#             'loading', 'spinner', 'pixel', 'tracking', 'badge',
#             '1x1', '2x2', 'transparent'
#         ]
        
#         for pattern in invalid_patterns:
#             if pattern in url_lower:
#                 return False
        
#         # Check file extension
#         valid_extensions = ['.jpg', '.jpeg', '.png', '.webp', '.gif']
#         has_valid_ext = any(ext in url_lower for ext in valid_extensions)
        
#         return has_valid_ext or '/images/' in url_lower or '/photos/' in url_lower
    
#     async def test_selectors(
#         self, 
#         url: str, 
#         selectors: Dict[str, str]
#     ) -> Dict[str, Any]:
#         """
#         Test custom selectors on a page.
        
#         Args:
#             url: URL to test on
#             selectors: Custom selectors to test
        
#         Returns:
#             Test results with matched elements
#         """
#         from app.utils.browser_manager import get_browser_manager
        
#         browser_manager = await get_browser_manager()
        
#         async with browser_manager.get_page(domain=extract_domain(url)) as page:
#             await page.goto(url, wait_until='networkidle')
            
#             results = {}
            
#             for name, selector in selectors.items():
#                 try:
#                     elements = await page.query_selector_all(selector)
                    
#                     sample_data = []
#                     for el in elements[:5]:
#                         text = await el.inner_text()
#                         sample_data.append(text[:100] if text else '')
                    
#                     results[name] = {
#                         'selector': selector,
#                         'count': len(elements),
#                         'valid': len(elements) > 0,
#                         'samples': sample_data
#                     }
                    
#                 except Exception as e:
#                     results[name] = {
#                         'selector': selector,
#                         'count': 0,
#                         'valid': False,
#                         'error': str(e)
#                     }
            
#             # Try to extract sample products
#             self.set_selectors(selectors)
#             sample_products = await self._extract_products_from_dom(page)
            
#             return {
#                 'matched_elements': results,
#                 'sample_data': sample_products[:5]
#             }
    
#     def get_stats(self) -> Dict[str, Any]:
#         """Get extraction statistics."""
#         return {
#             'pages_processed': self.stats.pages_processed,
#             'products_extracted': self.stats.products_extracted,
#             'products_from_list': self.stats.products_from_list,
#             'products_from_detail': self.stats.products_from_detail,
#             'products_from_json_ld': self.stats.products_from_json_ld,
#             'failed_extractions': self.stats.failed_extractions,
#             'errors': self.stats.errors[:10]
#         }
    
#     def reset_stats(self) -> None:
#         """Reset extraction statistics."""
#         self.stats = ExtractionStats()
#         self._extracted_urls.clear()