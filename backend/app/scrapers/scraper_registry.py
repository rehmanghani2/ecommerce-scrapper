"""
Scraper Registry Module
Factory for creating and managing platform-specific scrapers.
"""

from typing import Dict, Type, Optional, List
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
    def detect_platform(cls, url: str) -> str:
        """
        Detect platform from URL.
        
        Args:
            url: Website URL
        
        Returns:
            Platform name or 'generic'
        """
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # Remove www prefix
            if domain.startswith('www.'):
                domain = domain[4:]
            
            # Check domain patterns
            for pattern, platform in cls._domain_patterns.items():
                if re.search(pattern, domain, re.IGNORECASE):
                    logger.debug(f"Detected platform '{platform}' for {domain}")
                    return platform
            
            # Check for common platform indicators in domain
            platform_indicators = {
                'amazon': ['amazon.', 'amzn.'],
                'ebay': ['ebay.'],
                'shopify': ['myshopify.com'],
                'etsy': ['etsy.com'],
                'walmart': ['walmart.'],
                'aliexpress': ['aliexpress.'],
            }
            
            for platform, indicators in platform_indicators.items():
                for indicator in indicators:
                    if indicator in domain:
                        return platform
            
            return 'generic'
            
        except Exception as e:
            logger.warning(f"Error detecting platform for {url}: {e}")
            return 'generic'
    
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


def detect_platform(url: str) -> str:
    """
    Convenience function to detect platform.
    
    Args:
        url: Website URL
    
    Returns:
        Platform name
    """
    return ScraperRegistry.detect_platform(url)


# Auto-register scrapers on module import
def _register_all_scrapers():
    """Register all available scrapers."""
    from .amazon_scraper import AmazonScraper
    from .ebay_scraper import EbayScraper
    from .shopify_scraper import ShopifyScraper
    from .woocommerce_scraper import WooCommerceScraper
    from .magento_scraper import MagentoScraper
    from .generic_scraper import GenericScraper
    
    ScraperRegistry.register('amazon', AmazonScraper)
    ScraperRegistry.register('ebay', EbayScraper)
    ScraperRegistry.register('shopify', ShopifyScraper)
    ScraperRegistry.register('woocommerce', WooCommerceScraper)
    ScraperRegistry.register('magento', MagentoScraper)
    ScraperRegistry.register('generic', GenericScraper)


# Register scrapers when module is loaded
try:
    _register_all_scrapers()
except ImportError:
    # Scrapers not yet defined, will be registered later
    pass