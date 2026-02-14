"""
WooCommerce Scraper Module
Specialized scraper for WooCommerce stores.
"""

import re
from typing import Optional, List, Dict, Any
from urllib.parse import urljoin
import logging

from playwright.async_api import Page

from .base_scraper import (
    BaseScraper, 
    ProductData, 
    ScraperResult
)
from app.utils.helpers import clean_text, clean_price

logger = logging.getLogger(__name__)


class WooCommerceScraper(BaseScraper):
    """
    Scraper optimized for WooCommerce stores.
    
    Features:
    - Standard WooCommerce selectors
    - Variable product support
    - Product gallery extraction
    - Category/attribute extraction
    """
    
    PLATFORM_NAME = "woocommerce"
    PLATFORM_DOMAINS = []  # WooCommerce is self-hosted, no specific domains
    
    REQUIRES_STEALTH = False
    
    SELECTORS = {
        # Listing page
        "product_container": ".products .product, ul.products li.product, .product-grid .product",
        "product_link": ".woocommerce-LoopProduct-link, a.product-link, .product-title a",
        "product_title": ".woocommerce-loop-product__title, .product-title, h2.title",
        "product_price": ".price, .woocommerce-Price-amount",
        "product_sale_price": ".price ins .woocommerce-Price-amount",
        "product_regular_price": ".price del .woocommerce-Price-amount",
        "product_image": ".attachment-woocommerce_thumbnail, .wp-post-image",
        "product_rating": ".star-rating",
        "product_category": ".product-category a",
        "next_page": ".woocommerce-pagination a.next, a.next.page-numbers",
        
        # Product page
        "detail_title": ".product_title, h1.entry-title",
        "detail_price": ".summary .price .woocommerce-Price-amount",
        "detail_sale_price": ".summary .price ins .woocommerce-Price-amount",
        "detail_regular_price": ".summary .price del .woocommerce-Price-amount",
        "detail_description": ".woocommerce-product-details__short-description, .product-short-description",
        "detail_full_description": "#tab-description, .woocommerce-Tabs-panel--description",
        "detail_sku": ".sku_wrapper .sku, .product_meta .sku",
        "detail_categories": ".posted_in a, .product_meta .product-categories a",
        "detail_tags": ".tagged_as a, .product_meta .product-tags a",
        "detail_images": ".woocommerce-product-gallery__image img, .product-gallery img",
        "detail_attributes": ".woocommerce-product-attributes tr",
        "detail_variations": "form.variations_form",
        "detail_variation_select": ".variations select",
        "detail_stock": ".stock, .in-stock, .out-of-stock",
        "detail_rating": ".woocommerce-product-rating .star-rating",
        "detail_review_count": ".woocommerce-review-link",
    }
    
    async def scrape_listing_page(
        self, 
        page: Page, 
        url: str
    ) -> ScraperResult:
        """Scrape WooCommerce shop/category page."""
        products = []
        product_urls = []
        errors = []
        
        try:
            await self.wait_for_content(page, self.SELECTORS["product_container"], timeout=10000)
            
            containers = await page.query_selector_all(self.SELECTORS["product_container"])
            
            for container in containers:
                try:
                    product = await self._extract_listing_product(container, url)
                    if product and product.name:
                        products.append(product)
                        if product.url:
                            product_urls.append(product.url)
                except Exception as e:
                    logger.debug(f"Error extracting WooCommerce product: {e}")
            
            logger.info(f"Extracted {len(products)} products from WooCommerce listing")
            
        except Exception as e:
            logger.error(f"Error scraping WooCommerce listing: {e}")
            errors.append(str(e))
        
        return ScraperResult(
            success=len(products) > 0,
            products=products,
            total_products=len(products),
            pages_scraped=1,
            errors=errors,
            product_urls=product_urls,
        )
    
    async def _extract_listing_product(
        self, 
        container, 
        base_url: str
    ) -> Optional[ProductData]:
        """Extract product from listing container."""
        product = ProductData(source_platform=self.PLATFORM_NAME)
        
        # Product ID from class
        classes = await container.get_attribute("class") or ""
        id_match = re.search(r'post-(\d+)', classes)
        if id_match:
            product.product_id = id_match.group(1)
        
        # Link
        link = await container.query_selector(self.SELECTORS["product_link"])
        if link:
            href = await link.get_attribute("href")
            if href:
                product.url = urljoin(base_url, href)
        
        # Title
        title_el = await container.query_selector(self.SELECTORS["product_title"])
        if title_el:
            product.name = clean_text(await title_el.inner_text())
        
        # Prices
        sale_price_el = await container.query_selector(self.SELECTORS["product_sale_price"])
        regular_price_el = await container.query_selector(self.SELECTORS["product_regular_price"])
        
        if sale_price_el:
            product.price = clean_price(await sale_price_el.inner_text())
            if regular_price_el:
                product.original_price = clean_price(await regular_price_el.inner_text())
        elif regular_price_el:
            product.price = clean_price(await regular_price_el.inner_text())
        else:
            price_el = await container.query_selector(self.SELECTORS["product_price"])
            if price_el:
                price_text = await price_el.inner_text()
                # Handle price ranges
                prices = re.findall(r'[\d,.]+', price_text.replace(",", ""))
                if prices:
                    product.price = float(prices[0])
        
        # Image
        img_el = await container.query_selector(self.SELECTORS["product_image"])
        if img_el:
            src = (await img_el.get_attribute("src") or 
                   await img_el.get_attribute("data-src") or
                   await img_el.get_attribute("data-lazy-src"))
            if src:
                product.image_url = src
        
        # Rating
        rating_el = await container.query_selector(self.SELECTORS["product_rating"])
        if rating_el:
            width = await rating_el.evaluate("el => getComputedStyle(el.querySelector('span')).width")
            if width:
                width_val = float(re.search(r'[\d.]+', width).group())
                product.rating = round((width_val / 100) * 5, 1)
        
        # Category
        cat_el = await container.query_selector(self.SELECTORS["product_category"])
        if cat_el:
            product.category = clean_text(await cat_el.inner_text())
        
        # Sale badge
        sale_badge = await container.query_selector(".onsale, .sale-badge")
        if sale_badge:
            product.attributes["on_sale"] = True
        
        return product if product.name else None
    
    async def scrape_product_page(
        self, 
        page: Page, 
        url: str
    ) -> Optional[ProductData]:
        """Scrape WooCommerce product page."""
        try:
            await self.wait_for_content(page, self.SELECTORS["detail_title"], timeout=10000)
            
            product = ProductData(
                url=url,
                source_platform=self.PLATFORM_NAME
            )
            
            # Product ID from body class
            body_class = await page.evaluate("document.body.className")
            id_match = re.search(r'postid-(\d+)', body_class)
            if id_match:
                product.product_id = id_match.group(1)
            
            # Title
            product.name = await self.extract_text(page, self.SELECTORS["detail_title"])
            
            # Prices
            sale_text = await self.extract_text(page, self.SELECTORS["detail_sale_price"])
            regular_text = await self.extract_text(page, self.SELECTORS["detail_regular_price"])
            
            if sale_text:
                product.price = clean_price(sale_text)
                if regular_text:
                    product.original_price = clean_price(regular_text)
            elif regular_text:
                product.price = clean_price(regular_text)
            else:
                price_text = await self.extract_text(page, self.SELECTORS["detail_price"])
                product.price = clean_price(price_text)
            
            # Descriptions
            product.short_description = await self.extract_text(
                page, self.SELECTORS["detail_description"]
            )
            product.description = await self.extract_text(
                page, self.SELECTORS["detail_full_description"]
            )
            
            # SKU
            sku_text = await self.extract_text(page, self.SELECTORS["detail_sku"])
            if sku_text:
                product.sku = sku_text.replace("SKU:", "").strip()
            
            # Categories
            categories = await self.extract_all_text(page, self.SELECTORS["detail_categories"])
            if categories:
                product.categories = categories
                product.category_path = " > ".join(categories)
                product.category = categories[-1] if categories else None
            
            # Tags
            tags = await self.extract_all_text(page, self.SELECTORS["detail_tags"])
            if tags:
                product.attributes["tags"] = tags
            
            # Stock status
            stock_el = await page.query_selector(self.SELECTORS["detail_stock"])
            if stock_el:
                stock_text = await stock_el.inner_text()
                classes = await stock_el.get_attribute("class") or ""
                
                product.in_stock = "in-stock" in classes or "in stock" in stock_text.lower()
                product.stock_status = clean_text(stock_text)
                
                # Try to extract quantity
                qty_match = re.search(r'(\d+)\s*in stock', stock_text, re.IGNORECASE)
                if qty_match:
                    product.stock_quantity = int(qty_match.group(1))
            
            # Rating
            rating_el = await page.query_selector(self.SELECTORS["detail_rating"])
            if rating_el:
                rating_attr = await rating_el.evaluate(
                    "el => el.querySelector('span')?.style.width || getComputedStyle(el.querySelector('span')).width"
                )
                if rating_attr:
                    width = float(re.search(r'[\d.]+', rating_attr).group())
                    product.rating = round((width / 100) * 5, 1)
            
            # Review count
            review_el = await page.query_selector(self.SELECTORS["detail_review_count"])
            if review_el:
                review_text = await review_el.inner_text()
                match = re.search(r'(\d+)', review_text)
                if match:
                    product.review_count = int(match.group(1))
            
            # Images
            product.images = await self._extract_images(page)
            if product.images:
                product.image_url = product.images[0].get("url")
            
            # Attributes/Specifications
            if self.config.include_specifications:
                product.specifications = await self._extract_attributes(page)
            
            # Variations
            if self.config.include_variants:
                product.variants = await self._extract_variations(page)
            
            # Extract from JSON-LD
            json_ld = await self.extract_json_ld(page)
            self._enrich_from_json_ld(product, json_ld)
            
            return product if product.name else None
            
        except Exception as e:
            logger.error(f"Error scraping WooCommerce product page {url}: {e}")
            return None
    
    async def _extract_images(self, page: Page) -> List[Dict[str, Any]]:
        """Extract product gallery images."""
        images = []
        seen = set()
        
        try:
            img_elements = await page.query_selector_all(self.SELECTORS["detail_images"])
            
            for i, img in enumerate(img_elements):
                # Try various src attributes
                src = (await img.get_attribute("data-large_image") or
                       await img.get_attribute("data-src") or
                       await img.get_attribute("src"))
                
                if src and src not in seen and "placeholder" not in src.lower():
                    images.append({
                        "url": src,
                        "is_primary": i == 0,
                        "alt_text": await img.get_attribute("alt") or ""
                    })
                    seen.add(src)
                    
        except Exception as e:
            logger.debug(f"Error extracting images: {e}")
        
        return images
    
    async def _extract_attributes(self, page: Page) -> Dict[str, str]:
        """Extract product attributes table."""
        attrs = {}
        
        try:
            rows = await page.query_selector_all(self.SELECTORS["detail_attributes"])
            
            for row in rows:
                th = await row.query_selector("th, .woocommerce-product-attributes-item__label")
                td = await row.query_selector("td, .woocommerce-product-attributes-item__value")
                
                if th and td:
                    key = clean_text(await th.inner_text())
                    value = clean_text(await td.inner_text())
                    if key and value:
                        attrs[key] = value
                        
        except Exception as e:
            logger.debug(f"Error extracting attributes: {e}")
        
        return attrs
    
    async def _extract_variations(self, page: Page) -> List[Dict[str, Any]]:
        """Extract product variations."""
        variants = []
        
        try:
            # Check for variations form
            form = await page.query_selector(self.SELECTORS["detail_variations"])
            if not form:
                return variants
            
            # Get variations data from page
            variations_data = await page.evaluate('''
                () => {
                    const form = document.querySelector('form.variations_form');
                    if (form) {
                        const data = form.getAttribute('data-product_variations');
                        if (data) {
                            try {
                                return JSON.parse(data);
                            } catch (e) {}
                        }
                    }
                    return [];
                }
            ''')
            
            for v in variations_data:
                variant = {
                    "variant_id": str(v.get("variation_id", "")),
                    "sku": v.get("sku", ""),
                    "price": clean_price(v.get("display_price", 0)),
                    "in_stock": v.get("is_in_stock", True),
                    "image_url": v.get("image", {}).get("url", ""),
                    "attributes": v.get("attributes", {}),
                }
                
                # Build name from attributes
                attr_values = [str(val) for val in v.get("attributes", {}).values()]
                variant["name"] = " / ".join(attr_values) if attr_values else ""
                
                variants.append(variant)
                
        except Exception as e:
            logger.debug(f"Error extracting variations: {e}")
        
        return variants
    
    def _enrich_from_json_ld(self, product: ProductData, json_ld: List[Dict]) -> None:
        """Enrich product from JSON-LD data."""
        for item in json_ld:
            if isinstance(item, dict):
                item_type = item.get("@type", "")
                
                if "Product" in str(item_type):
                    if not product.brand:
                        brand = item.get("brand", {})
                        if isinstance(brand, dict):
                            product.brand = brand.get("name", "")
                        elif isinstance(brand, str):
                            product.brand = brand
                    
                    if not product.sku:
                        product.sku = item.get("sku", "")
                    
                    offers = item.get("offers", {})
                    if isinstance(offers, dict):
                        if not product.currency:
                            product.currency = offers.get("priceCurrency", "GBP")
                    
                    rating = item.get("aggregateRating", {})
                    if isinstance(rating, dict):
                        if not product.rating:
                            product.rating = rating.get("ratingValue")
                        if not product.review_count:
                            product.review_count = rating.get("reviewCount")
    
    async def get_next_page_url(self, page: Page) -> Optional[str]:
        """Get next page URL."""
        try:
            next_link = await page.query_selector(self.SELECTORS["next_page"])
            if next_link:
                href = await next_link.get_attribute("href")
                if href:
                    return href
        except Exception:
            pass
        return None