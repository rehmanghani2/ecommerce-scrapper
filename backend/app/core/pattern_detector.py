"""
pattern_detector.py
-------------------
Heuristic-based page type detection for a generic ecommerce crawler.

Purpose:
- Classify pages into: PRODUCT, CATEGORY/LISTING, PAGINATION, OTHER
- Enable conditional logic in scraper_engine without hardcoding sites
- Work across 200+ ecommerce websites

Design principles:
- Heuristic + signal based (not ML yet)
- Non-blocking: never crashes crawler
- Explainable rules (easy to tune)
"""

from enum import Enum
from typing import Dict, Any

from bs4 import BeautifulSoup

from app.utils.logger import get_logger

logger = get_logger(__name__)


class PageType(str, Enum):
    PRODUCT = "product"
    CATEGORY = "category"
    PAGINATION = "pagination"
    OTHER = "other"


class PatternDetector:
    """
    Detect page type using structural and semantic signals.
    """

    def __init__(self, *, confidence_threshold: float = 0.6):
        self.confidence_threshold = confidence_threshold

    def detect(self, html: str, url: str) -> Dict[str, Any]:
        """
        Analyze page HTML and return detected page type and signals.

        Returns:
        {
            "type": PageType,
            "confidence": float,
            "signals": { ... }
        }
        """

        try:
            soup = BeautifulSoup(html, "lxml")
        except Exception:
            soup = BeautifulSoup(html, "html.parser")

        signals = {
            "product_schema": self._has_product_schema(soup),
            "price_elements": self._count_price_elements(soup),
            "add_to_cart": self._has_add_to_cart(soup),
            "product_links": self._count_product_links(soup),
            "pagination_links": self._count_pagination_links(soup),
        }

        scores = {
            PageType.PRODUCT: 0.0,
            PageType.CATEGORY: 0.0,
            PageType.PAGINATION: 0.0,
        }

        # PRODUCT signals
        if signals["product_schema"]:
            scores[PageType.PRODUCT] += 0.4
        if signals["price_elements"] >= 1:
            scores[PageType.PRODUCT] += 0.3
        if signals["add_to_cart"]:
            scores[PageType.PRODUCT] += 0.3

        # CATEGORY signals
        if signals["product_links"] >= 5:
            scores[PageType.CATEGORY] += 0.6
        if signals["pagination_links"] >= 1:
            scores[PageType.CATEGORY] += 0.2

        # PAGINATION signals
        if signals["pagination_links"] >= 2:
            scores[PageType.PAGINATION] += 0.7

        # Choose best type
        page_type = PageType.OTHER
        confidence = 0.0

        for t, score in scores.items():
            if score > confidence:
                page_type = t
                confidence = score

        if confidence < self.confidence_threshold:
            page_type = PageType.OTHER

        return {
            "type": page_type,
            "confidence": confidence,
            "signals": signals,
        }

    # --------------------
    # Signal detectors
    # --------------------

    def _has_product_schema(self, soup: BeautifulSoup) -> bool:
        return bool(
            soup.find("script", type="application/ld+json", string=lambda s: s and "Product" in s)
        )

    def _count_price_elements(self, soup: BeautifulSoup) -> int:
        price_keywords = ("price", "amount", "cost", "sale")
        count = 0
        for el in soup.find_all(text=True):
            text = el.strip().lower()
            if any(k in text for k in price_keywords) and any(c.isdigit() for c in text):
                count += 1
                if count >= 3:
                    break
        return count

    def _has_add_to_cart(self, soup: BeautifulSoup) -> bool:
        keywords = ("add to cart", "add to basket", "buy now")
        for btn in soup.find_all(["button", "a"], text=True):
            if any(k in btn.get_text(strip=True).lower() for k in keywords):
                return True
        return False

    def _count_product_links(self, soup: BeautifulSoup) -> int:
        # Heuristic: many links containing /product or similar
        count = 0
        for a in soup.find_all("a", href=True):
            href = a["href"].lower()
            if any(k in href for k in ("/product", "/item", "/sku")):
                count += 1
                if count >= 5:
                    break
        return count

    def _count_pagination_links(self, soup: BeautifulSoup) -> int:
        keywords = ("page=", "?p=", "?pg=", "/page/")
        count = 0
        for a in soup.find_all("a", href=True):
            if any(k in a["href"].lower() for k in keywords):
                count += 1
                if count >= 3:
                    break
        return count















# """
# Pattern Detector Module
# Automatically detects e-commerce platform and product selectors.
# """

# from typing import Dict, List, Any, Optional
# from dataclasses import dataclass, field
# from playwright.async_api import Page
# import logging

# from app.utils.browser_manager import get_browser_manager
# from app.utils.helpers import extract_domain

# logger = logging.getLogger(__name__)


# @dataclass
# class PlatformSignature:
#     """Signature for detecting e-commerce platforms."""
#     name: str
#     indicators: List[str]  # HTML/JS patterns to look for
#     selectors: Dict[str, str]  # Default selectors for this platform
#     confidence_threshold: float = 0.6


# @dataclass
# class DetectionResult:
#     """Result of platform/selector detection."""
#     platform: Optional[str] = None
#     confidence: float = 0.0
#     selectors: Dict[str, str] = field(default_factory=dict)
#     sample_products: List[Dict[str, Any]] = field(default_factory=list)
#     indicators_found: List[str] = field(default_factory=list)
#     page_type: str = "unknown"  # category, product, search, home


# class PatternDetector:
#     """
#     Detects e-commerce platform and auto-discovers product selectors.
    
#     Supports:
#     - Shopify
#     - WooCommerce
#     - Magento
#     - BigCommerce
#     - PrestaShop
#     - OpenCart
#     - Custom/Generic sites
#     """
    
#     # Platform signatures
#     PLATFORMS = {
#         "shopify": PlatformSignature(
#             name="Shopify",
#             indicators=[
#                 "Shopify.theme",
#                 "cdn.shopify.com",
#                 "shopify-section",
#                 "/collections/",
#                 "myshopify.com",
#                 "shopify.com/s/files",
#                 "ShopifyBuy",
#                 "window.ShopifyAnalytics",
#             ],
#             selectors={
#                 "product_container": ".collection-products, .product-list, #product-grid",
#                 "product_card": ".product-card, .product-item, .grid-product, .product",
#                 "product_link": "a[href*='/products/']",
#                 "product_name": ".product-card__title, .product-title, .product__title, h2 a, h3 a",
#                 "product_price": ".product-price, .price, .money, [data-product-price]",
#                 "product_image": ".product-card__image img, .product__image img",
#                 "pagination_next": ".pagination__next, a[rel='next'], .next",
#                 "category_links": ".collection-list a, .nav-link[href*='/collections/']",
#             }
#         ),
#         "woocommerce": PlatformSignature(
#             name="WooCommerce",
#             indicators=[
#                 "woocommerce",
#                 "wc-block",
#                 "wp-content/plugins/woocommerce",
#                 "add_to_cart",
#                 "wc-add-to-cart",
#                 "is-woocommerce",
#                 "woocommerce-page",
#             ],
#             selectors={
#                 "product_container": ".products, .woocommerce-products, ul.products",
#                 "product_card": ".product, .type-product, li.product",
#                 "product_link": ".woocommerce-LoopProduct-link, a.product-link, h2 a",
#                 "product_name": ".woocommerce-loop-product__title, .product-title, h2",
#                 "product_price": ".price, .woocommerce-Price-amount",
#                 "product_image": ".attachment-woocommerce_thumbnail, .wp-post-image",
#                 "pagination_next": ".woocommerce-pagination a.next, a.next.page-numbers",
#                 "category_links": ".product-categories a, .widget_product_categories a",
#             }
#         ),
#         "magento": PlatformSignature(
#             name="Magento",
#             indicators=[
#                 "Magento_",
#                 "mage/",
#                 "magento",
#                 "/pub/static/",
#                 "requirejs/require",
#                 "catalog-product",
#                 "catalogsearch",
#             ],
#             selectors={
#                 "product_container": ".products-grid, .product-items, .products.list",
#                 "product_card": ".product-item, .item.product",
#                 "product_link": ".product-item-link, .product-item-info a",
#                 "product_name": ".product-item-name, .product-name",
#                 "product_price": ".price-box .price, .special-price .price",
#                 "product_image": ".product-image-photo",
#                 "pagination_next": ".pages-item-next a, a.next",
#                 "category_links": ".categories-menu a, .nav-sections a",
#             }
#         ),
#         "bigcommerce": PlatformSignature(
#             name="BigCommerce",
#             indicators=[
#                 "bigcommerce",
#                 "cdn11.bigcommerce.com",
#                 "stencil",
#                 "cornerstone",
#                 "bc-sf-filter",
#             ],
#             selectors={
#                 "product_container": ".productGrid, .product-listing",
#                 "product_card": ".product, .card",
#                 "product_link": ".card-figure__link, .product-link",
#                 "product_name": ".card-title, .product-title",
#                 "product_price": ".price, .price--withTax",
#                 "product_image": ".card-image, .product-image",
#                 "pagination_next": ".pagination-item--next a",
#                 "category_links": ".navList a, .navPages-action",
#             }
#         ),
#         "prestashop": PlatformSignature(
#             name="PrestaShop",
#             indicators=[
#                 "prestashop",
#                 "PrestaShop",
#                 "modules/ps_",
#                 "/module/",
#                 "presta",
#                 "id_product",
#             ],
#             selectors={
#                 "product_container": ".products, #js-product-list",
#                 "product_card": ".product-miniature, .product-container",
#                 "product_link": ".product-thumbnail, .product-title a",
#                 "product_name": ".product-title, h2 a",
#                 "product_price": ".price, .product-price",
#                 "product_image": ".product-thumbnail img",
#                 "pagination_next": ".next a, a.next",
#                 "category_links": "#_desktop_top_menu a, .category-sub-link",
#             }
#         ),
#     }
    
#     # Common product selectors to try
#     GENERIC_SELECTORS = {
#         "product_container": [
#             ".products", ".product-list", ".product-grid", ".items",
#             "#products", "[data-products]", ".catalog", ".shop-items",
#             ".collection", ".category-products", ".search-results",
#         ],
#         "product_card": [
#             ".product", ".product-item", ".product-card", ".item",
#             ".grid-item", ".col-product", "[data-product]", ".card",
#             "article.product", "li.product", ".thumbnail",
#         ],
#         "product_link": [
#             "a[href*='product']", "a[href*='item']", "a[href*='/p/']",
#             "a[href*='/pd/']", ".product-link", ".product a",
#             "h2 a", "h3 a", ".title a", ".name a",
#         ],
#         "product_name": [
#             ".product-name", ".product-title", ".title", ".name",
#             "h2", "h3", "h4", "[data-name]", ".item-name",
#             ".product-info h2", ".product-info h3",
#         ],
#         "product_price": [
#             ".price", ".product-price", ".amount", "[data-price]",
#             ".cost", ".value", ".sale-price", ".regular-price",
#             ".current-price", ".offer-price", "span.price",
#         ],
#         "product_image": [
#             ".product-image img", ".product-img img", ".image img",
#             ".thumbnail img", ".photo img", "[data-image]", ".lazy",
#             "img.product", "img.item", ".product img:first-child",
#         ],
#         "pagination_next": [
#             ".next", "a.next", ".pagination .next", "[rel='next']",
#             ".page-next", "a[aria-label='Next']", ".arrow-right",
#             "button.next", ".load-more", "#load-more",
#         ],
#     }
    
#     def __init__(self):
#         """Initialize the pattern detector."""
#         self._browser_manager = None
    
#     async def _get_browser_manager(self):
#         """Lazy load browser manager."""
#         if self._browser_manager is None:
#             self._browser_manager = await get_browser_manager()
#         return self._browser_manager
    
#     async def detect_platform(self, url: str) -> Dict[str, Any]:
#         """
#         Detect the e-commerce platform of a website.
        
#         Args:
#             url: Website URL to analyze
        
#         Returns:
#             Detection result with platform info
#         """
#         browser_manager = await self._get_browser_manager()
        
#         async with browser_manager.get_page(domain=extract_domain(url)) as page:
#             try:
#                 await page.goto(url, wait_until="domcontentloaded")
#                 await page.wait_for_timeout(2000)
                
#                 # Get page content
#                 html = await page.content()
                
#                 # Check each platform
#                 results = {}
#                 for platform_id, signature in self.PLATFORMS.items():
#                     found_indicators = []
#                     for indicator in signature.indicators:
#                         if indicator.lower() in html.lower():
#                             found_indicators.append(indicator)
                    
#                     confidence = len(found_indicators) / len(signature.indicators)
#                     results[platform_id] = {
#                         "confidence": confidence,
#                         "indicators": found_indicators
#                     }
                
#                 # Find best match
#                 best_match = max(results.items(), key=lambda x: x[1]["confidence"])
                
#                 if best_match[1]["confidence"] >= self.PLATFORMS[best_match[0]].confidence_threshold:
#                     return {
#                         "platform": best_match[0],
#                         "platform_name": self.PLATFORMS[best_match[0]].name,
#                         "confidence": best_match[1]["confidence"],
#                         "indicators": best_match[1]["indicators"]
#                     }
                
#                 return {
#                     "platform": "generic",
#                     "platform_name": "Generic/Custom",
#                     "confidence": 0.0,
#                     "indicators": []
#                 }
                
#             except Exception as e:
#                 logger.error(f"Platform detection failed: {e}")
#                 return {
#                     "platform": "unknown",
#                     "platform_name": "Unknown",
#                     "confidence": 0.0,
#                     "error": str(e)
#                 }
    
#     async def analyze_page(self, url: str) -> Dict[str, Any]:
#         """
#         Analyze a page and detect product selectors.
        
#         Args:
#             url: URL to analyze
        
#         Returns:
#             Detection result with selectors and sample products
#         """
#         browser_manager = await self._get_browser_manager()
        
#         result = DetectionResult()
        
#         async with browser_manager.get_page(domain=extract_domain(url)) as page:
#             try:
#                 await page.goto(url, wait_until="networkidle")
#                 await page.wait_for_timeout(2000)
                
#                 # Detect platform
#                 html = await page.content()
#                 platform_result = await self._detect_platform_from_html(html)
#                 result.platform = platform_result.get("platform")
#                 result.indicators_found = platform_result.get("indicators", [])
                
#                 # Detect page type
#                 result.page_type = await self._detect_page_type(page, url)
                
#                 # Get selectors based on platform
#                 if result.platform and result.platform in self.PLATFORMS:
#                     result.selectors = self.PLATFORMS[result.platform].selectors.copy()
#                 else:
#                     result.selectors = {}
                
#                 # Auto-detect and validate selectors
#                 detected_selectors = await self._auto_detect_selectors(page)
#                 result.selectors.update(detected_selectors)
                
#                 # Extract sample products
#                 result.sample_products = await self._extract_sample_products(
#                     page, result.selectors
#                 )
                
#                 # Calculate confidence based on sample quality
#                 if result.sample_products:
#                     valid_products = sum(
#                         1 for p in result.sample_products
#                         if p.get("name") and (p.get("price") or p.get("url"))
#                     )
#                     result.confidence = valid_products / len(result.sample_products)
                
#                 return {
#                     "platform": result.platform,
#                     "confidence": result.confidence,
#                     "page_type": result.page_type,
#                     "selectors": result.selectors,
#                     "sample_products": result.sample_products[:5],
#                     "indicators": result.indicators_found
#                 }
                
#             except Exception as e:
#                 logger.error(f"Page analysis failed: {e}")
#                 return {
#                     "platform": None,
#                     "confidence": 0.0,
#                     "selectors": {},
#                     "sample_products": [],
#                     "error": str(e)
#                 }
    
#     async def _detect_platform_from_html(self, html: str) -> Dict[str, Any]:
#         """Detect platform from HTML content."""
#         results = {}
#         for platform_id, signature in self.PLATFORMS.items():
#             found = [i for i in signature.indicators if i.lower() in html.lower()]
#             confidence = len(found) / len(signature.indicators)
#             results[platform_id] = {"confidence": confidence, "indicators": found}
        
#         best = max(results.items(), key=lambda x: x[1]["confidence"])
#         if best[1]["confidence"] >= 0.3:
#             return {"platform": best[0], **best[1]}
#         return {"platform": "generic", "confidence": 0, "indicators": []}
    
#     async def _detect_page_type(self, page: Page, url: str) -> str:
#         """Detect the type of page (category, product, search, home)."""
#         url_lower = url.lower()
        
#         # URL-based detection
#         if any(x in url_lower for x in ['/product/', '/products/', '/item/', '/p/', '/pd/']):
#             return "product"
#         if any(x in url_lower for x in ['/category/', '/categories/', '/collection/', '/c/']):
#             return "category"
#         if any(x in url_lower for x in ['/search', '?q=', '?s=', 'search=']):
#             return "search"
        
#         # Content-based detection
#         try:
#             # Check for product grid
#             product_elements = await page.query_selector_all(
#                 ".product, .product-item, .product-card, [data-product]"
#             )
#             if len(product_elements) > 3:
#                 return "category"
            
#             # Check for single product indicators
#             add_to_cart = await page.query_selector(
#                 "button[name='add'], .add-to-cart, #add-to-cart, [data-action='add-to-cart']"
#             )
#             if add_to_cart:
#                 return "product"
            
#         except Exception:
#             pass
        
#         return "unknown"
    
#     async def _auto_detect_selectors(self, page: Page) -> Dict[str, str]:
#         """Auto-detect working selectors for the page."""
#         detected = {}
        
#         for selector_type, candidates in self.GENERIC_SELECTORS.items():
#             best_selector = None
#             best_count = 0
            
#             for selector in candidates:
#                 try:
#                     elements = await page.query_selector_all(selector)
#                     count = len(elements)
                    
#                     # For product containers, we want exactly 1
#                     if selector_type == "product_container":
#                         if count == 1:
#                             best_selector = selector
#                             break
#                     # For product cards, we want multiple
#                     elif selector_type == "product_card":
#                         if count > best_count and count >= 3:
#                             best_selector = selector
#                             best_count = count
#                     # For pagination, we want at least 1
#                     elif selector_type == "pagination_next":
#                         if count >= 1:
#                             best_selector = selector
#                             break
#                     # For others, prefer more matches
#                     else:
#                         if count > best_count:
#                             best_selector = selector
#                             best_count = count
                            
#                 except Exception:
#                     continue
            
#             if best_selector:
#                 detected[selector_type] = best_selector
        
#         return detected
    
#     async def _extract_sample_products(
#         self, 
#         page: Page, 
#         selectors: Dict[str, str]
#     ) -> List[Dict[str, Any]]:
#         """Extract sample products using detected selectors."""
#         products = []
        
#         product_card_selector = selectors.get("product_card")
#         if not product_card_selector:
#             return products
        
#         try:
#             cards = await page.query_selector_all(product_card_selector)
            
#             for card in cards[:10]:  # Limit to 10 samples
#                 product = {}
                
#                 # Extract name
#                 name_selector = selectors.get("product_name")
#                 if name_selector:
#                     name_el = await card.query_selector(name_selector)
#                     if name_el:
#                         product["name"] = (await name_el.inner_text()).strip()
                
#                 # Extract price
#                 price_selector = selectors.get("product_price")
#                 if price_selector:
#                     price_el = await card.query_selector(price_selector)
#                     if price_el:
#                         product["price"] = (await price_el.inner_text()).strip()
                
#                 # Extract URL
#                 link_selector = selectors.get("product_link")
#                 if link_selector:
#                     link_el = await card.query_selector(link_selector)
#                     if link_el:
#                         product["url"] = await link_el.get_attribute("href")
                
#                 # Extract image
#                 image_selector = selectors.get("product_image")
#                 if image_selector:
#                     img_el = await card.query_selector(image_selector)
#                     if img_el:
#                         product["image"] = (
#                             await img_el.get_attribute("src") or 
#                             await img_el.get_attribute("data-src")
#                         )
                
#                 if product.get("name"):
#                     products.append(product)
        
#         except Exception as e:
#             logger.warning(f"Failed to extract sample products: {e}")
        
#         return products
    
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
#         browser_manager = await self._get_browser_manager()
        
#         async with browser_manager.get_page(domain=extract_domain(url)) as page:
#             await page.goto(url, wait_until="networkidle")
            
#             results = {}
#             for name, selector in selectors.items():
#                 try:
#                     elements = await page.query_selector_all(selector)
#                     results[name] = {
#                         "selector": selector,
#                         "count": len(elements),
#                         "valid": len(elements) > 0
#                     }
#                 except Exception as e:
#                     results[name] = {
#                         "selector": selector,
#                         "count": 0,
#                         "valid": False,
#                         "error": str(e)
#                     }
            
#             # Extract sample with provided selectors
#             sample_products = await self._extract_sample_products(page, selectors)
            
#             return {
#                 "matched_elements": results,
#                 "sample_data": sample_products
#             }