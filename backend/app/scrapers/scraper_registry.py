"""
Scraper Registry Module
Factory for creating and managing platform-specific scrapers.
"""

from typing import Dict, Type, Optional, List, Any, Tuple
from urllib.parse import urlparse
import re
import logging

from .base_scraper import BaseScraper, ScraperConfig

logger = logging.getLogger(__name__)


class ScraperRegistry:
    """
    Registry for platform-specific scrapers.
    
    Provides:
    - Automatic platform detection
    - Scraper instantiation
    - Platform configuration
    """
    
    _scrapers: Dict[str, Type[BaseScraper]] = {}
    _domain_patterns: Dict[str, str] = {}
    
    @classmethod
    def register(
        cls, 
        platform_name: str, 
        scraper_class: Type[BaseScraper],
        domain_patterns: List[str] = None
    ) -> None:
        """
        Register a scraper for a platform.
        
        Args:
            platform_name: Platform identifier
            scraper_class: Scraper class
            domain_patterns: Regex patterns for domain matching
        """
        cls._scrapers[platform_name.lower()] = scraper_class
        
        if domain_patterns:
            for pattern in domain_patterns:
                cls._domain_patterns[pattern] = platform_name.lower()
        
        # Also register from class attributes
        if hasattr(scraper_class, 'PLATFORM_DOMAINS'):
            for domain in scraper_class.PLATFORM_DOMAINS:
                cls._domain_patterns[re.escape(domain)] = platform_name.lower()
        
        logger.debug(f"Registered scraper: {platform_name}")
    
    @classmethod
    def get_scraper(
        cls, 
        platform: str, 
        config: Optional[ScraperConfig] = None
    ) -> BaseScraper:
        """
        Get a scraper instance for a platform.
        
        Args:
            platform: Platform name
            config: Scraper configuration
        
        Returns:
            Scraper instance
        """
        platform_lower = platform.lower()
        
        if platform_lower not in cls._scrapers:
            # Fall back to generic scraper
            from .generic_scraper import GenericScraper
            logger.warning(f"No scraper for platform '{platform}', using generic")
            return GenericScraper(config)
        
        return cls._scrapers[platform_lower](config)
    
    @classmethod
    def inspect_headers(cls, headers: Optional[Dict[str, str]]) -> Optional[tuple]:
        """
        Inspect HTTP response headers for platform indicators.
        Returns: (platform, indicator_string) or None
        """
        if not headers:
            return None
        
        # Lowercase header keys and values for case-insensitive matching
        h_lower = {str(k).lower(): str(v).lower() for k, v in headers.items()}

        # Shopify headers
        for k in h_lower:
            if "x-shopify" in k or "shopify" in h_lower.get(k, ""):
                return ("shopify", f"header: {k}")
        
        # Magento headers
        for k in h_lower:
            if "x-magento" in k:
                return ("magento", f"header: {k}")

        # Wix headers
        for k in h_lower:
            if "x-wix" in k or "wix" in h_lower.get(k, ""):
                return ("wix", f"header: {k}")

        # BigCommerce headers
        for k in h_lower:
            if "x-bc-" in k or "bigcommerce" in h_lower.get(k, ""):
                return ("bigcommerce", f"header: {k}")

        # X-Powered-By check
        powered_by = h_lower.get("x-powered-by", "")
        if "woocommerce" in powered_by:
            return ("woocommerce", f"x-powered-by: {powered_by}")
        if "magento" in powered_by:
            return ("magento", f"x-powered-by: {powered_by}")
        if "prestashop" in powered_by:
            return ("prestashop", f"x-powered-by: {powered_by}")

        return None

    @classmethod
    def inspect_meta_generator(cls, html: Optional[str]) -> Optional[tuple]:
        """
        Inspect <meta name="generator" content="..."> tags in HTML.
        Returns: (platform, generator_content) or None
        """
        if not html:
            return None

        # Look in first 64KB for performance
        head_chunk = html[:65536]
        
        # Regex matching <meta name="generator" content="..."> or <meta content="..." name="generator">
        patterns = [
            r'<meta[^>]+name=["\']generator["\'][^>]+content=["\']([^"\']+)["\']',
            r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']generator["\']',
        ]
        
        for pat in patterns:
            match = re.search(pat, head_chunk, re.IGNORECASE)
            if match:
                gen_content = match.group(1).strip()
                gen_lower = gen_content.lower()
                
                if "woocommerce" in gen_lower:
                    return ("woocommerce", f"meta generator: {gen_content}")
                if "shopify" in gen_lower:
                    return ("shopify", f"meta generator: {gen_content}")
                if "bigcommerce" in gen_lower:
                    return ("bigcommerce", f"meta generator: {gen_content}")
                if "magento" in gen_lower:
                    return ("magento", f"meta generator: {gen_content}")
                if "squarespace" in gen_lower:
                    return ("squarespace", f"meta generator: {gen_content}")
                if "wix" in gen_lower:
                    return ("wix", f"meta generator: {gen_content}")
                if "prestashop" in gen_lower:
                    return ("prestashop", f"meta generator: {gen_content}")
                if "opencart" in gen_lower:
                    return ("opencart", f"meta generator: {gen_content}")

        return None

    @classmethod
    def inspect_html_signatures(cls, html: Optional[str]) -> Optional[tuple]:
        """
        Inspect HTML script tags, resource URLs, and markup signatures.
        Returns: (platform, indicator_string) or None
        """
        if not html:
            return None

        chunk = html[:131072]  # Inspect first 128KB of document

        signatures = [
            ("shopify", ["cdn.shopify.com", "Shopify.theme", "Shopify.routes", "shopify-features", "window.ShopifyAnalytics"]),
            ("woocommerce", ["wp-content/plugins/woocommerce", "wc-block-", "class=\"woocommerce", "woocommerce-active", "wc-ajax="]),
            ("bigcommerce", ["cdn11.bigcommerce.com", "stencil-utils", "window.BCData", "data-test=\"card\"", "class=\"productGrid\""]),
            ("magento", ["mage/cookies.js", "mage-translation", "data-mage-init", "/frontend/Magento/", "Magento_Ui"]),
            ("squarespace", ["static1.squarespace.com", "<!-- This is Squarespace. -->", "Squarespace.onInitialize", "sqs-money-native"]),
            ("wix", ["static.wixstatic.com", "wix-warmup-data", "data-hook=\"product-item-root\"", "data-hook=\"product-item-name\""]),
            ("etsy", ["etsystatic.com", "v2-listing-card", "data-search-results-listing-card"]),
            ("walmart", ["walmartimages.com", "data-automation-id=\"product-price\"", "data-testid=\"item-stack\""]),
            ("amazon", ["images-na.ssl-images-amazon.com", "data-component-type=\"s-search-result\""]),
            ("ebay", ["ebayimg.com", "class=\"s-item\""]),
        ]

        for platform, indicators in signatures:
            for ind in indicators:
                if ind in chunk:
                    return (platform, f"html signature: {ind}")

        return None

    @classmethod
    def detect_platform_detailed(
        cls,
        url: str,
        html: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        fetch_if_needed: bool = False
    ) -> Dict[str, Any]:
        """
        Perform a thorough platform detection inspecting:
        1. Domain keywords (fast path)
        2. HTTP response headers
        3. <meta name="generator"> tags
        4. HTML script, asset, and DOM signatures
        5. Live page fetch if requested
        """
        indicators = []

        # 1. Check HTTP response headers if provided
        header_match = cls.inspect_headers(headers)
        if header_match:
            plat, ind = header_match
            indicators.append(ind)
            return {
                "platform": plat,
                "confidence": 0.95,
                "indicators": indicators,
                "method": "http_headers"
            }

        # 2. Check <meta name="generator"> in HTML if provided
        meta_match = cls.inspect_meta_generator(html)
        if meta_match:
            plat, ind = meta_match
            indicators.append(ind)
            return {
                "platform": plat,
                "confidence": 0.95,
                "indicators": indicators,
                "method": "meta_generator"
            }

        # 3. Check HTML signatures if provided
        sig_match = cls.inspect_html_signatures(html)
        if sig_match:
            plat, ind = sig_match
            indicators.append(ind)
            return {
                "platform": plat,
                "confidence": 0.9,
                "indicators": indicators,
                "method": "html_signature"
            }

        # 4. Check domain indicators
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            if domain.startswith('www.'):
                domain = domain[4:]

            for pattern, platform in cls._domain_patterns.items():
                if re.search(pattern, domain, re.IGNORECASE):
                    indicators.append(f"domain regex: {pattern}")
                    return {
                        "platform": platform,
                        "confidence": 0.9,
                        "indicators": indicators,
                        "method": "domain_pattern"
                    }

            platform_indicators = {
                'amazon': ['amazon.', 'amzn.'],
                'ebay': ['ebay.'],
                'shopify': ['myshopify.com'],
                'bigcommerce': ['mybigcommerce.com', 'bigcommerce.'],
                'magento': ['magento.'],
                'squarespace': ['squarespace.com'],
                'wix': ['wixsite.com', 'wix.com'],
                'etsy': ['etsy.com'],
                'walmart': ['walmart.'],
                'aliexpress': ['aliexpress.'],
            }

            for platform, ind_list in platform_indicators.items():
                for indicator in ind_list:
                    if indicator in domain:
                        indicators.append(f"domain indicator: {indicator}")
                        return {
                            "platform": platform,
                            "confidence": 0.9,
                            "indicators": indicators,
                            "method": "domain_keyword"
                        }
        except Exception as e:
            logger.debug(f"Error parsing domain for {url}: {e}")

        # 5. Optional live fetch if requested and not detected yet
        if fetch_if_needed and url.startswith(('http://', 'https://')):
            try:
                import httpx
                fetch_headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                }
                with httpx.Client(timeout=6.0, follow_redirects=True) as client:
                    resp = client.get(url, headers=fetch_headers)
                    resp_headers = dict(resp.headers)
                    resp_html = resp.text[:131072]
                    return cls.detect_platform_detailed(
                        url=str(resp.url),
                        html=resp_html,
                        headers=resp_headers,
                        fetch_if_needed=False
                    )
            except Exception as fetch_err:
                logger.debug(f"Live fetch detection error for {url}: {fetch_err}")

        return {
            "platform": "generic",
            "confidence": 0.2,
            "indicators": [],
            "method": "fallback"
        }

    @classmethod
    def detect_platform(
        cls,
        url: str,
        html: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        fetch_if_needed: bool = False
    ) -> str:
        """
        Detect platform from URL, optional HTML, and optional response headers.
        
        Args:
            url: Website URL
            html: Optional HTML page content to inspect meta tags/signatures
            headers: Optional HTTP response headers to inspect
            fetch_if_needed: If True, fetches initial page HTML if domain match fails
        
        Returns:
            Platform name or 'generic'
        """
        result = cls.detect_platform_detailed(
            url=url,
            html=html,
            headers=headers,
            fetch_if_needed=fetch_if_needed
        )
        return result.get("platform", "generic")
    
    @classmethod
    def get_scraper_for_url(
        cls, 
        url: str, 
        config: Optional[ScraperConfig] = None
    ) -> BaseScraper:
        """
        Get appropriate scraper for a URL.
        
        Args:
            url: Website URL
            config: Scraper configuration
        
        Returns:
            Appropriate scraper instance
        """
        platform = cls.detect_platform(url)
        return cls.get_scraper(platform, config)
    
    @classmethod
    def list_platforms(cls) -> List[str]:
        """Get list of registered platforms."""
        return list(cls._scrapers.keys())
    
    @classmethod
    def is_supported(cls, platform: str) -> bool:
        """Check if a platform is supported."""
        return platform.lower() in cls._scrapers


def get_scraper(url_or_platform: str, config: Optional[ScraperConfig] = None) -> BaseScraper:
    """
    Convenience function to get a scraper.
    
    Args:
        url_or_platform: URL or platform name
        config: Scraper configuration
    
    Returns:
        Scraper instance
    """
    if url_or_platform.startswith(('http://', 'https://')):
        return ScraperRegistry.get_scraper_for_url(url_or_platform, config)
    return ScraperRegistry.get_scraper(url_or_platform, config)


def detect_platform(
    url: str,
    html: Optional[str] = None,
    headers: Optional[Dict[str, str]] = None,
    fetch_if_needed: bool = False
) -> str:
    """
    Convenience function to detect platform from URL, optional HTML, or response headers.
    """
    return ScraperRegistry.detect_platform(
        url=url,
        html=html,
        headers=headers,
        fetch_if_needed=fetch_if_needed
    )


def detect_platform_detailed(
    url: str,
    html: Optional[str] = None,
    headers: Optional[Dict[str, str]] = None,
    fetch_if_needed: bool = False
) -> Dict[str, Any]:
    """
    Convenience function to get detailed detection report including confidence,
    detected platform, and specific matched indicators.
    """
    return ScraperRegistry.detect_platform_detailed(
        url=url,
        html=html,
        headers=headers,
        fetch_if_needed=fetch_if_needed
    )


# Auto-register scrapers on module import
def _register_all_scrapers():
    """Register all available scrapers."""
    from .amazon_scraper import AmazonScraper
    from .ebay_scraper import EbayScraper
    from .shopify_scraper import ShopifyScraper
    from .woocommerce_scraper import WooCommerceScraper
    from .magento_scraper import MagentoScraper
    from .bigcommerce_scraper import BigCommerceScraper
    from .squarespace_scraper import SquarespaceScraper
    from .wix_scraper import WixScraper
    from .etsy_scraper import EtsyScraper
    from .walmart_scraper import WalmartScraper
    from .generic_scraper import GenericScraper
    
    ScraperRegistry.register('amazon', AmazonScraper)
    ScraperRegistry.register('ebay', EbayScraper)
    ScraperRegistry.register('shopify', ShopifyScraper)
    ScraperRegistry.register('woocommerce', WooCommerceScraper)
    ScraperRegistry.register('magento', MagentoScraper)
    ScraperRegistry.register('bigcommerce', BigCommerceScraper)
    ScraperRegistry.register('squarespace', SquarespaceScraper)
    ScraperRegistry.register('wix', WixScraper)
    ScraperRegistry.register('etsy', EtsyScraper)
    ScraperRegistry.register('walmart', WalmartScraper)
    ScraperRegistry.register('generic', GenericScraper)


# Register scrapers when module is loaded
try:
    _register_all_scrapers()
except ImportError:
    # Scrapers not yet defined, will be registered later
    pass