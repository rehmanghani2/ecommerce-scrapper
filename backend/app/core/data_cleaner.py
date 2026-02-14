"""
data_cleaner.py
---------------
Data normalization and cleaning utilities for extracted ecommerce data.

Purpose:
- Normalize prices (symbols, commas, ranges)
- Detect and standardize currency
- Clean text fields
- Canonicalize URLs
- Deduplicate products safely

This module runs AFTER ProductExtractor and BEFORE persistence/export.
"""

import re
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse, urlunparse

from app.utils.logger import get_logger

logger = get_logger(__name__)


class DataCleaner:
    """
    Generic data cleaner for ecommerce product records.
    """

    CURRENCY_MAP = {
        "$": "USD",
        "€": "EUR",
        "£": "GBP",
        "₹": "INR",
        "¥": "JPY",
    }

    PRICE_REGEX = re.compile(r"([£$€₹¥])?\s*([0-9,.]+)")

    def clean_products(self, products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Clean and normalize a list of product dictionaries.
        """
        cleaned = []
        seen = set()

        for product in products:
            clean = self.clean_product(product)
            if not clean:
                continue

            fingerprint = self._fingerprint(clean)
            if fingerprint in seen:
                continue

            seen.add(fingerprint)
            cleaned.append(clean)

        return cleaned

    def clean_product(self, product: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Clean a single product safely.
        """
        try:
            cleaned = {}

            for key, value in product.items():
                if isinstance(value, str):
                    cleaned[key] = self._clean_text(value)
                else:
                    cleaned[key] = value

            if "price" in cleaned:
                price, currency = self._parse_price(cleaned.get("price"))
                cleaned["price"] = price
                cleaned["currency"] = currency

            if "url" in cleaned:
                cleaned["url"] = self._canonicalize_url(cleaned.get("url"))

            return cleaned
        except Exception:
            logger.exception("Failed to clean product")
            return None

    # ------------------------
    # Helpers
    # ------------------------

    def _clean_text(self, text: str) -> str:
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def _parse_price(self, price_text: Optional[str]):
        if not price_text:
            return None, None

        match = self.PRICE_REGEX.search(price_text)
        if not match:
            return None, None

        symbol, amount = match.groups()

        try:
            value = float(amount.replace(",", ""))
        except ValueError:
            value = None

        currency = self.CURRENCY_MAP.get(symbol)

        return value, currency

    def _canonicalize_url(self, url: Optional[str]) -> Optional[str]:
        if not url:
            return None

        try:
            parsed = urlparse(url)
            return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))
        except Exception:
            return url

    def _fingerprint(self, product: Dict[str, Any]) -> str:
        """
        Generate a stable fingerprint for deduplication.
        """
        key = f"{product.get('title')}|{product.get('price')}|{product.get('url')}"
        return key.lower()















# """
# Data Cleaner Module
# Cleans, normalizes, and validates scraped product data.
# """

# import re
# import html
# from typing import Dict, Any, Optional, List, Union
# from dataclasses import dataclass, field
# from decimal import Decimal, InvalidOperation
# from urllib.parse import urljoin, urlparse
# import logging

# logger = logging.getLogger(__name__)


# @dataclass
# class CleaningStats:
#     """Statistics about data cleaning operations."""
#     total_products: int = 0
#     cleaned_products: int = 0
#     invalid_products: int = 0
#     prices_cleaned: int = 0
#     urls_normalized: int = 0
#     descriptions_cleaned: int = 0
#     duplicates_removed: int = 0
#     errors: List[str] = field(default_factory=list)


# class DataCleaner:
#     """
#     Cleans and normalizes scraped product data.
    
#     Features:
#     - Price extraction and normalization
#     - URL validation and normalization
#     - Text cleaning and HTML removal
#     - Duplicate detection
#     - Data validation
#     - Category normalization
#     """
    
#     # Currency patterns
#     CURRENCY_PATTERNS = {
#         'GBP': [r'£', r'GBP', r'gbp'],
#         'USD': [r'\$', r'USD', r'usd', r'US\$'],
#         'EUR': [r'€', r'EUR', r'eur'],
#         'JPY': [r'¥', r'JPY', r'jpy'],
#         'INR': [r'₹', r'INR', r'inr', r'Rs\.?'],
#         'CAD': [r'CAD', r'C\$', r'CA\$'],
#         'AUD': [r'AUD', r'A\$', r'AU\$'],
#     }
    
#     # Common stock status phrases
#     STOCK_PATTERNS = {
#         True: [
#             r'in\s*stock', r'available', r'add\s*to\s*cart', r'buy\s*now',
#             r'ships?\s*today', r'ready\s*to\s*ship', r'in\s*store',
#             r'\d+\s*available', r'\d+\s*left', r'\d+\s*in\s*stock',
#         ],
#         False: [
#             r'out\s*of\s*stock', r'sold\s*out', r'unavailable',
#             r'coming\s*soon', r'pre-?order', r'notify\s*me',
#             r'back\s*order', r'temporarily\s*unavailable',
#             r'currently\s*unavailable', r'not\s*available',
#         ]
#     }
    
#     # Invalid product name patterns
#     INVALID_NAME_PATTERNS = [
#         r'^add\s*to\s*cart$',
#         r'^buy\s*now$',
#         r'^view\s*details?$',
#         r'^click\s*here$',
#         r'^learn\s*more$',
#         r'^read\s*more$',
#         r'^\d+$',
#         r'^$',
#     ]
    
#     def __init__(self, base_url: Optional[str] = None, default_currency: str = "GBP"):
#         """
#         Initialize the data cleaner.
        
#         Args:
#             base_url: Base URL for resolving relative URLs
#             default_currency: Default currency code
#         """
#         self.base_url = base_url
#         self.default_currency = default_currency
#         self.stats = CleaningStats()
#         self._seen_products: set = set()
    
#     def clean_product(self, raw_product: Dict[str, Any]) -> Optional[Dict[str, Any]]:
#         """
#         Clean and normalize a single product.
        
#         Args:
#             raw_product: Raw scraped product data
        
#         Returns:
#             Cleaned product dict or None if invalid
#         """
#         self.stats.total_products += 1
        
#         try:
#             cleaned = {}
            
#             # Clean name (required)
#             name = self.clean_text(raw_product.get('name') or raw_product.get('title', ''))
#             if not self._is_valid_name(name):
#                 self.stats.invalid_products += 1
#                 return None
#             cleaned['name'] = name
            
#             # Clean URL (required)
#             url = self.clean_url(raw_product.get('url', ''))
#             if not url:
#                 self.stats.invalid_products += 1
#                 return None
#             cleaned['url'] = url
            
#             # Check for duplicates
#             product_key = self._generate_product_key(name, url)
#             if product_key in self._seen_products:
#                 self.stats.duplicates_removed += 1
#                 return None
#             self._seen_products.add(product_key)
            
#             # Clean prices
#             price_data = self.clean_price(
#                 raw_product.get('price') or raw_product.get('price_text', '')
#             )
#             cleaned['price'] = price_data['price']
#             cleaned['currency'] = price_data['currency']
#             cleaned['price_text'] = price_data['original']
            
#             if price_data['price']:
#                 self.stats.prices_cleaned += 1
            
#             # Clean original/sale prices
#             if raw_product.get('original_price'):
#                 orig_price_data = self.clean_price(raw_product['original_price'])
#                 cleaned['original_price'] = orig_price_data['price']
            
#             if raw_product.get('sale_price'):
#                 sale_price_data = self.clean_price(raw_product['sale_price'])
#                 cleaned['sale_price'] = sale_price_data['price']
            
#             # Calculate discount if applicable
#             if cleaned.get('original_price') and cleaned.get('price'):
#                 if cleaned['original_price'] > cleaned['price']:
#                     discount = ((cleaned['original_price'] - cleaned['price']) / 
#                                cleaned['original_price'] * 100)
#                     cleaned['discount_percentage'] = round(discount, 1)
            
#             # Clean description
#             description = self.clean_description(
#                 raw_product.get('description') or raw_product.get('short_description', '')
#             )
#             if description:
#                 cleaned['description'] = description
#                 self.stats.descriptions_cleaned += 1
            
#             # Clean short description
#             short_desc = raw_product.get('short_description')
#             if short_desc:
#                 cleaned['short_description'] = self.clean_text(short_desc)[:500]
            
#             # Clean images
#             cleaned['image_url'] = self.clean_url(raw_product.get('image_url', ''))
#             cleaned['thumbnail_url'] = self.clean_url(raw_product.get('thumbnail_url', ''))
            
#             # Handle multiple images
#             images = raw_product.get('images', [])
#             if images:
#                 cleaned['images'] = [
#                     {'url': self.clean_url(img.get('url', '') if isinstance(img, dict) else img)}
#                     for img in images
#                     if self.clean_url(img.get('url', '') if isinstance(img, dict) else img)
#                 ]
            
#             # Clean categories
#             cleaned['category'] = self.clean_text(raw_product.get('category', ''))
#             cleaned['subcategory'] = self.clean_text(raw_product.get('subcategory', ''))
#             cleaned['category_path'] = self.clean_category_path(
#                 raw_product.get('category_path') or raw_product.get('categories', [])
#             )
            
#             # Clean brand/manufacturer
#             cleaned['brand'] = self.clean_text(raw_product.get('brand', ''))
#             cleaned['manufacturer'] = self.clean_text(raw_product.get('manufacturer', ''))
            
#             # Clean SKU/identifiers
#             cleaned['product_id'] = self.clean_sku(raw_product.get('product_id', ''))
#             cleaned['sku'] = self.clean_sku(raw_product.get('sku', ''))
#             cleaned['upc'] = self.clean_sku(raw_product.get('upc', ''))
#             cleaned['ean'] = self.clean_sku(raw_product.get('ean', ''))
            
#             # Clean availability
#             stock_info = self.clean_stock_status(
#                 raw_product.get('stock_status') or raw_product.get('availability', ''),
#                 raw_product.get('stock_quantity')
#             )
#             cleaned['in_stock'] = stock_info['in_stock']
#             cleaned['stock_quantity'] = stock_info['quantity']
#             cleaned['stock_status'] = stock_info['status_text']
            
#             # Clean specifications
#             specs = raw_product.get('specifications', {})
#             if specs:
#                 cleaned['specifications'] = self.clean_specifications(specs)
            
#             # Clean features
#             features = raw_product.get('features', [])
#             if features:
#                 cleaned['features'] = [
#                     self.clean_text(f) for f in features if self.clean_text(f)
#                 ]
            
#             # Clean rating
#             rating = raw_product.get('rating')
#             if rating:
#                 cleaned['rating'] = self.clean_rating(rating)
            
#             review_count = raw_product.get('review_count')
#             if review_count:
#                 cleaned['review_count'] = self.clean_number(review_count)
            
#             # Clean variants
#             variants = raw_product.get('variants', [])
#             if variants:
#                 cleaned['variants'] = [
#                     self.clean_variant(v) for v in variants
#                     if self.clean_variant(v)
#                 ]
            
#             # Store raw data
#             cleaned['raw_data'] = raw_product
            
#             self.stats.cleaned_products += 1
#             return cleaned
            
#         except Exception as e:
#             self.stats.invalid_products += 1
#             self.stats.errors.append(f"Error cleaning product: {e}")
#             logger.warning(f"Failed to clean product: {e}")
#             return None
    
#     def clean_products(self, products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
#         """
#         Clean a list of products.
        
#         Args:
#             products: List of raw product dicts
        
#         Returns:
#             List of cleaned product dicts
#         """
#         # Reset stats
#         self.stats = CleaningStats()
#         self._seen_products.clear()
        
#         cleaned = []
#         for product in products:
#             cleaned_product = self.clean_product(product)
#             if cleaned_product:
#                 cleaned.append(cleaned_product)
        
#         logger.info(
#             f"Cleaned {self.stats.cleaned_products}/{self.stats.total_products} products, "
#             f"{self.stats.invalid_products} invalid, {self.stats.duplicates_removed} duplicates"
#         )
        
#         return cleaned
    
#     def clean_text(self, text: Optional[str]) -> str:
#         """
#         Clean and normalize text.
        
#         Args:
#             text: Text to clean
        
#         Returns:
#             Cleaned text
#         """
#         if not text:
#             return ""
        
#         # Convert to string
#         text = str(text)
        
#         # Decode HTML entities
#         text = html.unescape(text)
        
#         # Remove HTML tags
#         text = re.sub(r'<[^>]+>', ' ', text)
        
#         # Remove script/style content that might have leaked
#         text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
#         text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
        
#         # Normalize whitespace
#         text = re.sub(r'\s+', ' ', text)
        
#         # Remove leading/trailing whitespace
#         text = text.strip()
        
#         # Remove null characters
#         text = text.replace('\x00', '')
        
#         # Remove zero-width characters
#         text = re.sub(r'[\u200b\u200c\u200d\ufeff]', '', text)
        
#         return text
    
#     def clean_description(self, text: Optional[str]) -> str:
#         """
#         Clean product description.
        
#         Args:
#             text: Description text
        
#         Returns:
#             Cleaned description
#         """
#         if not text:
#             return ""
        
#         # Basic cleaning
#         text = self.clean_text(text)
        
#         # Remove common boilerplate
#         boilerplate_patterns = [
#             r'free\s+shipping.*?(?=\.|$)',
#             r'click\s+here\s+to.*?(?=\.|$)',
#             r'javascript:.*?(?=\s|$)',
#             r'var\s+\w+\s*=.*?(?=\s|$)',
#         ]
        
#         for pattern in boilerplate_patterns:
#             text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
#         # Limit length
#         if len(text) > 10000:
#             text = text[:10000] + '...'
        
#         return text.strip()
    
#     def clean_price(self, price_input: Any) -> Dict[str, Any]:
#         """
#         Extract and clean price information.
        
#         Args:
#             price_input: Price value (string, number, or dict)
        
#         Returns:
#             Dict with price, currency, and original text
#         """
#         result = {
#             'price': None,
#             'currency': self.default_currency,
#             'original': str(price_input) if price_input else ''
#         }
        
#         if not price_input:
#             return result
        
#         # Handle dict input
#         if isinstance(price_input, dict):
#             if 'amount' in price_input:
#                 price_input = price_input['amount']
#             elif 'value' in price_input:
#                 price_input = price_input['value']
#             else:
#                 price_input = str(price_input)
        
#         # Handle numeric input
#         if isinstance(price_input, (int, float, Decimal)):
#             result['price'] = float(price_input)
#             return result
        
#         # Convert to string
#         price_str = str(price_input).strip()
#         result['original'] = price_str
        
#         # Detect currency
#         for currency, patterns in self.CURRENCY_PATTERNS.items():
#             for pattern in patterns:
#                 if re.search(pattern, price_str, re.IGNORECASE):
#                     result['currency'] = currency
#                     break
        
#         # Remove currency symbols and text
#         price_str = re.sub(r'[£$€¥₹]', '', price_str)
#         price_str = re.sub(
#             r'\b(GBP|USD|EUR|JPY|INR|CAD|AUD|from|From|starting|Starting|was|Was|now|Now|only|Only)\b',
#             '', price_str, flags=re.IGNORECASE
#         )
        
#         # Handle price ranges - take the first/lower price
#         range_match = re.search(r'(\d[\d,]*\.?\d*)\s*[-–—to]\s*(\d[\d,]*\.?\d*)', price_str)
#         if range_match:
#             price_str = range_match.group(1)
        
#         # Remove thousand separators (commas)
#         price_str = price_str.replace(',', '')
        
#         # Extract numeric value
#         match = re.search(r'(\d+(?:\.\d{1,2})?)', price_str)
#         if match:
#             try:
#                 result['price'] = float(match.group(1))
#             except (ValueError, InvalidOperation):
#                 pass
        
#         return result
    
#     def clean_url(self, url: Optional[str]) -> str:
#         """
#         Clean and normalize a URL.
        
#         Args:
#             url: URL to clean
        
#         Returns:
#             Cleaned absolute URL or empty string
#         """
#         if not url:
#             return ""
        
#         url = str(url).strip()
        
#         # Remove whitespace and newlines
#         url = re.sub(r'\s+', '', url)
        
#         # Handle data URLs (skip them)
#         if url.startswith('data:'):
#             return ""
        
#         # Handle javascript URLs (skip them)
#         if url.startswith('javascript:'):
#             return ""
        
#         # Handle protocol-relative URLs
#         if url.startswith('//'):
#             url = 'https:' + url
        
#         # Handle relative URLs
#         if self.base_url and not url.startswith(('http://', 'https://')):
#             url = urljoin(self.base_url, url)
        
#         # Validate URL
#         try:
#             parsed = urlparse(url)
#             if not parsed.scheme or not parsed.netloc:
#                 return ""
            
#             # Ensure scheme is http or https
#             if parsed.scheme not in ('http', 'https'):
#                 return ""
            
#             self.stats.urls_normalized += 1
#             return url
            
#         except Exception:
#             return ""
    
#     def clean_stock_status(
#         self, 
#         status_text: Optional[str],
#         quantity: Optional[Any] = None
#     ) -> Dict[str, Any]:
#         """
#         Clean and normalize stock status.
        
#         Args:
#             status_text: Stock status text
#             quantity: Stock quantity
        
#         Returns:
#             Dict with in_stock, quantity, and status_text
#         """
#         result = {
#             'in_stock': True,  # Default to in stock
#             'quantity': None,
#             'status_text': ''
#         }
        
#         # Parse quantity
#         if quantity is not None:
#             try:
#                 qty = int(re.sub(r'[^\d]', '', str(quantity)))
#                 result['quantity'] = qty
#                 result['in_stock'] = qty > 0
#             except (ValueError, TypeError):
#                 pass
        
#         # Parse status text
#         if status_text:
#             status_text = str(status_text).lower().strip()
#             result['status_text'] = self.clean_text(status_text)
            
#             # Check for out of stock patterns
#             for pattern in self.STOCK_PATTERNS[False]:
#                 if re.search(pattern, status_text, re.IGNORECASE):
#                     result['in_stock'] = False
#                     break
            
#             # Check for in stock patterns (if not already out of stock)
#             if result['in_stock']:
#                 for pattern in self.STOCK_PATTERNS[True]:
#                     if re.search(pattern, status_text, re.IGNORECASE):
#                         result['in_stock'] = True
#                         break
            
#             # Extract quantity from text if not provided
#             if result['quantity'] is None:
#                 qty_match = re.search(r'(\d+)\s*(?:in\s*stock|left|available)', status_text)
#                 if qty_match:
#                     result['quantity'] = int(qty_match.group(1))
        
#         return result
    
#     def clean_specifications(self, specs: Dict[str, Any]) -> Dict[str, str]:
#         """
#         Clean product specifications.
        
#         Args:
#             specs: Raw specifications dict
        
#         Returns:
#             Cleaned specifications dict
#         """
#         cleaned = {}
        
#         for key, value in specs.items():
#             # Clean key
#             clean_key = self.clean_text(key)
#             if not clean_key:
#                 continue
            
#             # Clean value
#             if isinstance(value, (list, tuple)):
#                 value = ', '.join(str(v) for v in value)
#             clean_value = self.clean_text(str(value))
            
#             if clean_value:
#                 cleaned[clean_key] = clean_value
        
#         return cleaned
    
#     def clean_category_path(
#         self, 
#         category_input: Union[str, List[str], None]
#     ) -> str:
#         """
#         Clean and normalize category path.
        
#         Args:
#             category_input: Category string or list
        
#         Returns:
#             Cleaned category path (e.g., "Electronics > Phones > iPhone")
#         """
#         if not category_input:
#             return ""
        
#         # Handle list input
#         if isinstance(category_input, list):
#             categories = [self.clean_text(c) for c in category_input if c]
#         else:
#             # Split by common separators
#             category_str = str(category_input)
#             categories = re.split(r'\s*[>/»→|]\s*', category_str)
#             categories = [self.clean_text(c) for c in categories if c]
        
#         # Remove duplicates while preserving order
#         seen = set()
#         unique_categories = []
#         for cat in categories:
#             if cat and cat.lower() not in seen:
#                 seen.add(cat.lower())
#                 unique_categories.append(cat)
        
#         return ' > '.join(unique_categories)
    
#     def clean_sku(self, sku: Optional[str]) -> str:
#         """
#         Clean SKU/product identifier.
        
#         Args:
#             sku: SKU string
        
#         Returns:
#             Cleaned SKU
#         """
#         if not sku:
#             return ""
        
#         sku = str(sku).strip()
        
#         # Remove common prefixes
#         sku = re.sub(r'^(sku|SKU|item|ITEM|product|PRODUCT)[:\s#-]*', '', sku)
        
#         # Keep only valid SKU characters
#         sku = re.sub(r'[^\w\-.]', '', sku)
        
#         return sku.upper() if sku else ""
    
#     def clean_rating(self, rating: Any) -> Optional[float]:
#         """
#         Clean and normalize rating.
        
#         Args:
#             rating: Rating value
        
#         Returns:
#             Normalized rating (0-5 scale) or None
#         """
#         if rating is None:
#             return None
        
#         try:
#             # Handle string ratings
#             if isinstance(rating, str):
#                 # Extract number from strings like "4.5 out of 5"
#                 match = re.search(r'(\d+(?:\.\d+)?)', rating)
#                 if not match:
#                     return None
#                 rating = float(match.group(1))
#             else:
#                 rating = float(rating)
            
#             # Normalize to 5-star scale
#             if rating > 5:
#                 if rating <= 10:
#                     rating = rating / 2  # 10-point scale
#                 elif rating <= 100:
#                     rating = rating / 20  # Percentage scale
            
#             # Clamp to valid range
#             rating = max(0, min(5, rating))
            
#             return round(rating, 1)
            
#         except (ValueError, TypeError):
#             return None
    
#     def clean_number(self, value: Any) -> Optional[int]:
#         """
#         Extract integer from various formats.
        
#         Args:
#             value: Number value
        
#         Returns:
#             Cleaned integer or None
#         """
#         if value is None:
#             return None
        
#         try:
#             if isinstance(value, int):
#                 return value
            
#             # Extract digits from string
#             value_str = str(value)
#             digits = re.sub(r'[^\d]', '', value_str)
            
#             if digits:
#                 return int(digits)
            
#         except (ValueError, TypeError):
#             pass
        
#         return None
    
#     def clean_variant(self, variant: Dict[str, Any]) -> Optional[Dict[str, Any]]:
#         """
#         Clean product variant data.
        
#         Args:
#             variant: Raw variant dict
        
#         Returns:
#             Cleaned variant dict or None
#         """
#         if not variant:
#             return None
        
#         cleaned = {}
        
#         # Name is required
#         name = self.clean_text(variant.get('name', ''))
#         if not name:
#             # Try to construct name from attributes
#             attrs = variant.get('attributes', {})
#             if attrs:
#                 name = ' / '.join(str(v) for v in attrs.values())
        
#         if not name:
#             return None
        
#         cleaned['name'] = name
#         cleaned['variant_id'] = self.clean_sku(variant.get('variant_id', ''))
#         cleaned['sku'] = self.clean_sku(variant.get('sku', ''))
        
#         # Clean price
#         price_data = self.clean_price(variant.get('price', ''))
#         cleaned['price'] = price_data['price']
        
#         if variant.get('original_price'):
#             orig_price = self.clean_price(variant['original_price'])
#             cleaned['original_price'] = orig_price['price']
        
#         # Clean stock
#         stock_info = self.clean_stock_status(
#             variant.get('stock_status', ''),
#             variant.get('stock_quantity')
#         )
#         cleaned['in_stock'] = stock_info['in_stock']
#         cleaned['stock_quantity'] = stock_info['quantity']
        
#         # Clean attributes
#         attrs = variant.get('attributes', {})
#         if attrs:
#             cleaned['attributes'] = self.clean_specifications(attrs)
        
#         # Clean image
#         cleaned['image_url'] = self.clean_url(variant.get('image_url', ''))
        
#         return cleaned
    
#     def _is_valid_name(self, name: str) -> bool:
#         """Check if a product name is valid."""
#         if not name or len(name) < 2:
#             return False
        
#         # Check against invalid patterns
#         for pattern in self.INVALID_NAME_PATTERNS:
#             if re.match(pattern, name, re.IGNORECASE):
#                 return False
        
#         return True
    
#     def _generate_product_key(self, name: str, url: str) -> str:
#         """Generate a unique key for deduplication."""
#         import hashlib
#         content = f"{name.lower().strip()}|{url.lower().strip()}"
#         return hashlib.md5(content.encode()).hexdigest()
    
#     def get_stats(self) -> Dict[str, Any]:
#         """Get cleaning statistics."""
#         return {
#             'total_products': self.stats.total_products,
#             'cleaned_products': self.stats.cleaned_products,
#             'invalid_products': self.stats.invalid_products,
#             'duplicates_removed': self.stats.duplicates_removed,
#             'prices_cleaned': self.stats.prices_cleaned,
#             'urls_normalized': self.stats.urls_normalized,
#             'descriptions_cleaned': self.stats.descriptions_cleaned,
#             'success_rate': (
#                 self.stats.cleaned_products / self.stats.total_products * 100
#                 if self.stats.total_products > 0 else 0
#             ),
#             'errors': self.stats.errors[:10]  # Limit errors
#         }