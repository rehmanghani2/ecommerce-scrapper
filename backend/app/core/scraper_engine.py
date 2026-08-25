"""
scraper_engine.py
-----------------
Refactored orchestration layer for the Generic E-commerce Crawler.

IMPORTANT:
- This is an OPTION-A SAFE REFACTOR
- Public API & method signatures are preserved
- No API route or service import will break

Role of this module:
- Coordinate crawl jobs
- Wire together frontier, scheduler, fetcher, extractor
- Update job state & emit progress

This file does NOT:
- Parse products
- Hardcode selectors
- Contain Playwright low-level logic
"""

from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.url_frontier import URLFrontier
from app.core.crawl_scheduler import CrawlScheduler
from app.core.page_fetcher import PageFetcher
from app.core.link_extractor import LinkExtractor
from app.core.product_extractor import ProductExtractor
from app.core.browser_manager import BrowserManager

from app.services.job_service import JobService

from app.services.job_event_notifier import JobEventNotifier
from app.utils.logger import get_logger
logger = get_logger(__name__)
# logger = logging.getLogger(__name__)

class ScraperEngine:
    """
    Job-level orchestration engine.
    One instance = one crawl job.
    """

    def __init__(self, db: AsyncSession, job_id: int, start_url: str, *, max_depth: int = 3, max_pages: int = 500):
        self.db = db
        self.job_id = job_id
        self.start_url = start_url
        self.max_depth = max_depth
        self.max_pages = max_pages

        self._job_service = JobService(db)
        self._browser_manager: Optional[BrowserManager] = None
        self._scheduler: Optional[CrawlScheduler] = None
        
        self._notifier = JobEventNotifier()

    async def start(self):
        """
        Entry point called by API / worker.
        SAFE: preserves existing behaviour.
        """
        logger.info(f"[Job {self.job_id}] Starting scraper engine")
        await self._notifier.connect()
        
        from app.models.job import JobStatus
        await self._job_service.update_job_status(self.job_id, JobStatus.RUNNING)
        
        await self._notifier.publish(
            f"job:{self.job_id}",
            {
                "event": "job_started",
                "status": "running"
            }
        )

        try:
            await self._run()
            from app.models.job import JobStatus
            await self._job_service.update_job_status(self.job_id, JobStatus.COMPLETED)
            await self._notifier.publish(
                f"job:{self.job_id}",
                {
                    "event": "job_completed",
                    "status": "completed"
                }
            )
            logger.info(f"[Job {self.job_id}] Completed successfully")
        except Exception as exc:
            import traceback
            error_trace = traceback.format_exc()
            logger.error(f"[Job {self.job_id}] Failed: {exc}\n{error_trace}")
            
            from app.models.job import JobStatus
            error_msg = str(exc) or "Unknown internal error in ScraperEngine"
            await self._job_service.update_job_status(self.job_id, JobStatus.FAILED, error_msg)
            
            # Also try to update the trace if the model supports it
            try:
                job = await self.db.get(Job, self.job_id)
                if job:
                    job.error_trace = error_trace
                    await self.db.commit()
            except Exception:
                pass
            await self._notifier.publish(
                f"job:{self.job_id}",
                {
                    "event": "job_failed",
                    "status": "failed",
                    "error": str(exc)
                }
            )
        finally:
            await self._shutdown()

    async def _run(self):
        """
        Internal orchestration logic.
        """
        logger.info(f"[Job {self.job_id}] Step 1: Starting BrowserManager")
        self._browser_manager = BrowserManager()
        await self._browser_manager.start()
        logger.info(f"[Job {self.job_id}] Step 2: Browser started OK")

        page = await self._browser_manager.new_page()
        logger.info(f"[Job {self.job_id}] Step 3: New page created")

        frontier = URLFrontier(
            start_url=self.start_url,
            max_depth=self.max_depth,
            max_pages=self.max_pages,
        )
        logger.info(f"[Job {self.job_id}] Step 4: URLFrontier created for {self.start_url}")

        fetcher = PageFetcher(page)
        extractor = LinkExtractor(frontier.allowed_domain)
        product_extractor = ProductExtractor()
        logger.info(f"[Job {self.job_id}] Step 5: Fetcher/Extractor/ProductExtractor ready")

        self._scheduler = CrawlScheduler(
            frontier=frontier,
            fetcher=fetcher,
            extractor=extractor,
            product_extractor=product_extractor,
            on_page_crawled=self._on_page_crawled,
            on_products_found=self._on_products_found,
        )
        logger.info(f"[Job {self.job_id}] Step 6: CrawlScheduler created, starting run...")

        await self._scheduler.run()
        logger.info(f"[Job {self.job_id}] Step 7: CrawlScheduler.run() returned")

    async def _on_products_found(self, products_data: List[Dict[str, Any]]):
        """
        Callback from scheduler when products are found on a page.
        Saves products to database.
        """
        from app.models.product import Product
        import re

        saved_count = 0
        for data in products_data:
            try:
                # Basic cleaning of price
                price_val = None
                if data.get("price"):
                    price_str = str(data["price"])
                    # Extract numeric value from string like "£12.34"
                    price_match = re.search(r"(\d+\.?\d*)", price_str)
                    if price_match:
                        price_val = float(price_match.group(1))

                product = Product(
                    job_id=self.job_id,
                    name=data.get("name", "Unknown Product"),
                    url=data.get("url"),
                    price=price_val,
                    price_text=data.get("price"),
                    image_url=data.get("image_url"),
                    source_domain=self.start_url.split("//")[-1].split("/")[0]
                )
                self.db.add(product)
                saved_count += 1
            except Exception as e:
                logger.warning(f"Failed to prepare product for saving: {e}")

        if saved_count > 0:
            logger.info(f"[Job {self.job_id}] Saving {saved_count} products...")
            await self.db.commit()
            logger.info(f"[Job {self.job_id}] Successfully saved {saved_count} products to database")
            
            # Notify progress
            await self._notifier.publish(
                f"job:{self.job_id}",
                {
                    "event": "products_found",
                    "count": saved_count
                }
            )

    async def _on_page_crawled(self, url: str, success: bool):
        """
        Callback from scheduler after each page.
        Used for progress reporting.
        """
        pages = await self._job_service.increment_pages(self.job_id)

        logger.debug(f"[Job {self.job_id}] Crawled: {url} | success={success}")
        await self._notifier.publish(
            f"job:{self.job_id}",
            {
                "event": "page_crawled",
                "url": url,
                "success": success,
                "pages_crawled": pages
            }
        )    

    async def _shutdown(self):
        """
        Graceful shutdown of resources.
        """
        if self._scheduler:
            await self._scheduler.stop()

        if self._browser_manager:
            await self._browser_manager.close()
        
        await self._notifier.close()













# """
# Scraper Engine Module
# Main orchestration for the e-commerce scraping platform.
# """

# import asyncio
# import re
# import time
# from typing import Dict, List, Any, Optional, Set, Callable
# from dataclasses import dataclass, field
# from datetime import datetime
# from urllib.parse import urlparse, urljoin
# from playwright.async_api import Page, TimeoutError as PlaywrightTimeout
# from sqlalchemy.ext.asyncio import AsyncSession
# import logging

# from app.models.job import Job, JobStatus
# from app.models.product import Product, ProductImage, ProductVariant
# from app.utils.browser_manager import BrowserManager, get_browser_manager
# from app.utils.rate_limiter import AdaptiveRateLimiter
# from app.utils.helpers import (
#     extract_domain, normalize_url, is_valid_product_url
# )
# from app.core.pattern_detector import PatternDetector
# from app.core.product_extractor import ProductExtractor, ExtractionConfig
# from app.core.pagination_handler import PaginationHandler, PaginationConfig
# from app.core.data_cleaner import DataCleaner

# logger = logging.getLogger(__name__)


# @dataclass
# class ScraperConfig:
#     """Configuration for the scraper engine."""
    
#     # Crawling settings
#     max_pages: int = 100
#     max_products: int = 10000
#     max_depth: int = 5
#     follow_product_links: bool = True
#     follow_category_links: bool = True
    
#     # Performance settings
#     concurrent_requests: int = 3
#     request_delay: int = 1000  # ms
#     page_timeout: int = 30000  # ms
#     navigation_timeout: int = 60000  # ms
    
#     # Retry settings
#     max_retries: int = 3
#     retry_delay: int = 5  # seconds
    
#     # Content settings
#     include_images: bool = True
#     include_variants: bool = True
#     include_specifications: bool = True
    
#     # Selectors (optional - auto-detect if not provided)
#     selectors: Optional[Dict[str, str]] = None
    
#     # Pagination
#     pagination: Optional[Dict[str, Any]] = None
    
#     # Filters
#     url_patterns: Optional[List[str]] = None
#     exclude_patterns: Optional[List[str]] = None
#     category_filter: Optional[List[str]] = None
    
#     # Platform-specific
#     platform: Optional[str] = None  # shopify, woocommerce, etc.


# @dataclass
# class CrawlState:
#     """State tracking for the crawl operation."""
#     visited_urls: Set[str] = field(default_factory=set)
#     product_urls: Set[str] = field(default_factory=set)
#     category_urls: Set[str] = field(default_factory=set)
#     failed_urls: Set[str] = field(default_factory=set)
    
#     products_scraped: int = 0
#     pages_scraped: int = 0
#     pages_failed: int = 0
    
#     current_depth: int = 0
#     start_time: float = 0.0
    
#     is_paused: bool = False
#     is_cancelled: bool = False
    
#     errors: List[Dict[str, Any]] = field(default_factory=list)
#     logs: List[Dict[str, Any]] = field(default_factory=list)


# @dataclass 
# class ScrapedPage:
#     """Result of scraping a single page."""
#     url: str
#     page_type: str  # category, product, search, other
#     products: List[Dict[str, Any]] = field(default_factory=list)
#     category_links: List[str] = field(default_factory=list)
#     product_links: List[str] = field(default_factory=list)
#     next_page_url: Optional[str] = None
#     error: Optional[str] = None
#     duration: float = 0.0


# class ScraperEngine:
#     """
#     Main scraping engine that orchestrates the entire scraping process.
    
#     Features:
#     - Full site crawling
#     - Category-based scraping
#     - Product detail extraction
#     - Automatic platform detection
#     - Intelligent pagination handling
#     - Rate limiting
#     - Progress tracking
#     - Error recovery
#     """
    
#     # URL patterns to exclude
#     DEFAULT_EXCLUDE_PATTERNS = [
#         r'/cart', r'/checkout', r'/account', r'/login', r'/register',
#         r'/wishlist', r'/compare', r'/contact', r'/about', r'/faq',
#         r'/help', r'/privacy', r'/terms', r'/returns', r'/shipping',
#         r'/blog', r'/news', r'/press', r'/careers', r'/sitemap',
#         r'/feed', r'/rss', r'\.pdf$', r'\.xml$', r'/cdn-cgi/',
#         r'/wp-admin', r'/admin', r'/api/', r'#', r'javascript:',
#         r'mailto:', r'tel:', r'/tag/', r'/author/',
#     ]
    
#     # Patterns that indicate category/listing pages
#     CATEGORY_PATTERNS = [
#         r'/category/', r'/categories/', r'/collection/', r'/collections/',
#         r'/shop/', r'/products/', r'/catalog/', r'/c/', r'/dept/',
#         r'/browse/', r'/search', r'\?.*category', r'/brand/',
#     ]
    
#     # Patterns that indicate product pages
#     PRODUCT_PATTERNS = [
#         r'/product/', r'/products/[^/]+$', r'/item/', r'/p/',
#         r'/pd/', r'/dp/', r'-p-\d+', r'/goods/', r'[?&]product',
#         r'/[^/]+-\d+\.html$', r'/[^/]+\.html$',
#     ]
    
#     def __init__(
#         self,
#         config: Optional[ScraperConfig] = None
#     ):
#         """
#         Initialize the scraper engine.
        
#         Args:
#             config: Scraper configuration
#         """
#         self.config = config or ScraperConfig()
#         self.state = CrawlState()
        
#         # Components (initialized lazily)
#         self._browser_manager: Optional[BrowserManager] = None
#         self._rate_limiter: Optional[AdaptiveRateLimiter] = None
#         self._pattern_detector: Optional[PatternDetector] = None
#         self._product_extractor: Optional[ProductExtractor] = None
#         self._pagination_handler: Optional[PaginationHandler] = None
#         self._data_cleaner: Optional[DataCleaner] = None
        
#         # Job tracking
#         self._job: Optional[Job] = None
#         self._db: Optional[AsyncSession] = None
#         self._progress_callback: Optional[Callable] = None
        
#         # Domain info
#         self._base_url: str = ""
#         self._domain: str = ""
    
#     async def initialize(self, base_url: str) -> None:
#         """
#         Initialize scraper components for a specific website.
        
#         Args:
#             base_url: The base URL of the website to scrape
#         """
#         self._base_url = base_url
#         self._domain = extract_domain(base_url)
        
#         logger.info(f"Initializing scraper for {self._domain}")
        
#         # Initialize browser manager
#         self._browser_manager = await get_browser_manager()
        
#         # Initialize rate limiter
#         self._rate_limiter = AdaptiveRateLimiter(
#             initial_rate=2.0,
#             min_rate=0.2,
#             max_rate=5.0
#         )
        
#         # Initialize pattern detector
#         self._pattern_detector = PatternDetector()
        
#         # Initialize data cleaner
#         self._data_cleaner = DataCleaner(
#             base_url=base_url,
#             default_currency="GBP"
#         )
        
#         # Detect platform and get selectors
#         if not self.config.selectors:
#             await self._detect_platform_and_selectors()
        
#         # Initialize product extractor
#         extraction_config = ExtractionConfig(
#             follow_product_links=self.config.follow_product_links,
#             include_images=self.config.include_images,
#             include_variants=self.config.include_variants,
#             include_specifications=self.config.include_specifications,
#         )
        
#         if self.config.selectors:
#             for key, value in self.config.selectors.items():
#                 if hasattr(extraction_config, key):
#                     setattr(extraction_config, key, value)
        
#         self._product_extractor = ProductExtractor(
#             config=extraction_config,
#             base_url=base_url
#         )
        
#         # Initialize pagination handler
#         pagination_config = PaginationConfig(
#             max_pages=self.config.max_pages,
#             wait_time=self.config.request_delay,
#         )
        
#         if self.config.pagination:
#             for key, value in self.config.pagination.items():
#                 if hasattr(pagination_config, key):
#                     setattr(pagination_config, key, value)
        
#         self._pagination_handler = PaginationHandler(config=pagination_config)
        
#         self.state.start_time = time.time()
        
#         self._log("info", f"Scraper initialized for {self._domain}")
    
#     async def _detect_platform_and_selectors(self) -> None:
#         """Detect the e-commerce platform and get appropriate selectors."""
#         try:
#             result = await self._pattern_detector.analyze_page(self._base_url)
            
#             if result.get('platform'):
#                 self.config.platform = result['platform']
#                 self._log("info", f"Detected platform: {result['platform']}")
            
#             if result.get('selectors'):
#                 self.config.selectors = result['selectors']
#                 self._log("info", f"Auto-detected {len(result['selectors'])} selectors")
            
#             if result.get('sample_products'):
#                 self._log("info", f"Found {len(result['sample_products'])} sample products")
                
#         except Exception as e:
#             self._log("warning", f"Platform detection failed: {e}")
    
#     async def run(
#         self,
#         job_id: int,
#         start_url: str,
#         config: Optional[ScraperConfig] = None,
#         db: Optional[AsyncSession] = None,
#         progress_callback: Optional[Callable] = None
#     ) -> Dict[str, Any]:
#         """
#         Run the scraping job.
        
#         Args:
#             job_id: Database job ID
#             start_url: Starting URL for scraping
#             config: Optional configuration override
#             db: Database session
#             progress_callback: Callback for progress updates
        
#         Returns:
#             Scraping results summary
#         """
#         if config:
#             self.config = config
        
#         self._db = db
#         self._progress_callback = progress_callback
        
#         try:
#             # Load job from database
#             if db:
#                 self._job = await db.get(Job, job_id)
#                 if self._job:
#                     self._job.status = JobStatus.RUNNING
#                     self._job.started_at = datetime.utcnow()
#                     await db.commit()
            
#             # Initialize scraper
#             await self.initialize(start_url)
            
#             self._log("info", f"Starting scrape from {start_url}")
            
#             # Start crawling
#             await self._crawl(start_url)
            
#             # Finalize
#             result = await self._finalize()
            
#             return result
            
#         except asyncio.CancelledError:
#             self._log("info", "Scraping cancelled")
#             self.state.is_cancelled = True
#             return await self._finalize(status="cancelled")
            
#         except Exception as e:
#             self._log("error", f"Scraping failed: {e}")
#             return await self._finalize(status="failed", error=str(e))
    
#     async def _crawl(self, start_url: str) -> None:
#         """
#         Main crawling loop.
        
#         Args:
#             start_url: URL to start crawling from
#         """
#         # Initialize URL queues
#         urls_to_visit = [start_url]
#         self.state.current_depth = 0
        
#         while urls_to_visit and not self._should_stop():
#             # Get next batch of URLs
#             batch_size = min(self.config.concurrent_requests, len(urls_to_visit))
#             batch = urls_to_visit[:batch_size]
#             urls_to_visit = urls_to_visit[batch_size:]
            
#             # Process batch concurrently
#             tasks = [self._process_url(url) for url in batch]
#             results = await asyncio.gather(*tasks, return_exceptions=True)
            
#             # Process results
#             for result in results:
#                 if isinstance(result, Exception):
#                     self._log("error", f"Batch processing error: {result}")
#                     continue
                
#                 if isinstance(result, ScrapedPage):
#                     # Add discovered URLs to queue
#                     for url in result.category_links:
#                         if self._should_visit_url(url):
#                             urls_to_visit.append(url)
#                             self.state.category_urls.add(url)
                    
#                     for url in result.product_links:
#                         if self._should_visit_url(url):
#                             self.state.product_urls.add(url)
            
#             # Process product URLs
#             if not urls_to_visit and self.state.product_urls:
#                 # Get unvisited product URLs
#                 product_batch = [
#                     url for url in self.state.product_urls 
#                     if url not in self.state.visited_urls
#                 ][:self.config.max_pages - self.state.pages_scraped]
                
#                 urls_to_visit.extend(product_batch)
#                 self.state.product_urls -= set(product_batch)
            
#             # Update progress
#             await self._update_progress()
            
#             # Check for pause
#             while self.state.is_paused and not self.state.is_cancelled:
#                 await asyncio.sleep(1)
        
#         self._log("info", f"Crawling complete. Visited {len(self.state.visited_urls)} URLs")
    
#     async def _process_url(self, url: str) -> ScrapedPage:
#         """
#         Process a single URL.
        
#         Args:
#             url: URL to process
        
#         Returns:
#             ScrapedPage result
#         """
#         url = normalize_url(url, self._base_url)
        
#         if url in self.state.visited_urls:
#             return ScrapedPage(url=url, page_type="skipped")
        
#         self.state.visited_urls.add(url)
#         start_time = time.time()
        
#         result = ScrapedPage(url=url, page_type="unknown")
        
#         try:
#             # Rate limiting
#             await self._rate_limiter.wait(self._domain)
            
#             async with self._browser_manager.get_page(
#                 context_id=f"scraper_{self._domain}",
#                 domain=self._domain
#             ) as page:
#                 # Navigate to page
#                 response = await self._navigate_with_retry(page, url)
                
#                 if not response or response.status >= 400:
#                     raise Exception(f"HTTP {response.status if response else 'No response'}")
                
#                 # Determine page type
#                 result.page_type = self._determine_page_type(url, page)
                
#                 # Extract based on page type
#                 if result.page_type == "category":
#                     await self._process_category_page(page, result)
                    
#                 elif result.page_type == "product":
#                     await self._process_product_page(page, result)
                    
#                 else:
#                     # Try to extract any products
#                     await self._process_generic_page(page, result)
                
#                 # Report success to rate limiter
#                 self._rate_limiter.report_success(self._domain)
                
#                 self.state.pages_scraped += 1
                
#         except PlaywrightTimeout as e:
#             self._log("warning", f"Timeout on {url}")
#             result.error = "Timeout"
#             self.state.pages_failed += 1
#             self.state.failed_urls.add(url)
#             self._rate_limiter.report_error(self._domain)
            
#         except Exception as e:
#             self._log("warning", f"Error on {url}: {e}")
#             result.error = str(e)
#             self.state.pages_failed += 1
#             self.state.failed_urls.add(url)
            
#             # Check for rate limiting
#             if "429" in str(e) or "too many" in str(e).lower():
#                 self._rate_limiter.report_error(self._domain, is_rate_limit=True)
        
#         result.duration = time.time() - start_time
#         return result
    
#     async def _navigate_with_retry(
#         self, 
#         page: Page, 
#         url: str
#     ):
#         """Navigate to URL with retry logic."""
#         last_error = None
        
#         for attempt in range(self.config.max_retries):
#             try:
#                 response = await page.goto(
#                     url,
#                     wait_until="domcontentloaded",
#                     timeout=self.config.navigation_timeout
#                 )
                
#                 # Wait for page to stabilize
#                 await page.wait_for_timeout(self.config.request_delay)
                
#                 return response
                
#             except Exception as e:
#                 last_error = e
#                 if attempt < self.config.max_retries - 1:
#                     delay = self.config.retry_delay * (attempt + 1)
#                     self._log("debug", f"Retry {attempt + 1} for {url} after {delay}s")
#                     await asyncio.sleep(delay)
        
#         raise last_error
    
#     def _determine_page_type(self, url: str, page: Page) -> str:
#         """Determine the type of page."""
#         url_lower = url.lower()
        
#         # Check URL patterns
#         for pattern in self.PRODUCT_PATTERNS:
#             if re.search(pattern, url_lower):
#                 return "product"
        
#         for pattern in self.CATEGORY_PATTERNS:
#             if re.search(pattern, url_lower):
#                 return "category"
        
#         # Default to category for listing pages
#         return "category"
    
#     async def _process_category_page(
#         self, 
#         page: Page, 
#         result: ScrapedPage
#     ) -> None:
#         """Process a category/listing page."""
#         self._log("debug", f"Processing category page: {result.url}")
        
#         # Extract products from the listing
#         products = await self._product_extractor.extract_from_listing_page(
#             page,
#             follow_links=False  # We'll handle product links separately
#         )
        
#         # Clean and save products
#         for product in products:
#             cleaned = self._data_cleaner.clean_product(product)
#             if cleaned:
#                 result.products.append(cleaned)
#                 await self._save_product(cleaned)
        
#         # Extract category links
#         if self.config.follow_category_links:
#             result.category_links = await self._extract_category_links(page)
        
#         # Extract product links
#         result.product_links = await self._extract_product_links(page)
        
#         # Handle pagination
#         if self._pagination_handler:
#             next_url = await self._pagination_handler.get_next_page_url(page)
#             if next_url:
#                 result.next_page_url = next_url
#                 if self._should_visit_url(next_url):
#                     result.category_links.append(next_url)
        
#         self._log("info", f"Extracted {len(result.products)} products from category page")
    
#     async def _process_product_page(
#         self, 
#         page: Page, 
#         result: ScrapedPage
#     ) -> None:
#         """Process a product detail page."""
#         self._log("debug", f"Processing product page: {result.url}")
        
#         # Extract product details
#         product = await self._product_extractor.extract_from_detail_page(page)
        
#         if product:
#             result.products.append(product)
#             await self._save_product(product)
#             self._log("debug", f"Extracted product: {product.get('name', 'Unknown')}")
        
#         # Extract related product links
#         result.product_links = await self._extract_product_links(page)
    
#     async def _process_generic_page(
#         self, 
#         page: Page, 
#         result: ScrapedPage
#     ) -> None:
#         """Process a generic page (try to extract products)."""
#         self._log("debug", f"Processing generic page: {result.url}")
        
#         # Try to extract products
#         products = await self._product_extractor.extract_from_listing_page(
#             page,
#             follow_links=False
#         )
        
#         for product in products:
#             cleaned = self._data_cleaner.clean_product(product)
#             if cleaned:
#                 result.products.append(cleaned)
#                 await self._save_product(cleaned)
        
#         # Extract links
#         result.category_links = await self._extract_category_links(page)
#         result.product_links = await self._extract_product_links(page)
    
#     async def _extract_category_links(self, page: Page) -> List[str]:
#         """Extract category/navigation links from page."""
#         links = []
        
#         try:
#             # Common category link selectors
#             selectors = [
#                 'nav a[href*="/category"]',
#                 'nav a[href*="/collection"]',
#                 'nav a[href*="/shop"]',
#                 '.category-menu a',
#                 '.nav-menu a',
#                 '.categories a',
#                 '[data-category] a',
#                 '.sidebar a[href*="/"]',
#             ]
            
#             for selector in selectors:
#                 try:
#                     elements = await page.query_selector_all(selector)
#                     for element in elements:
#                         href = await element.get_attribute('href')
#                         if href:
#                             full_url = urljoin(self._base_url, href)
#                             if self._is_same_domain(full_url):
#                                 links.append(full_url)
#                 except Exception:
#                     continue
            
#         except Exception as e:
#             self._log("debug", f"Error extracting category links: {e}")
        
#         return list(set(links))
    
#     async def _extract_product_links(self, page: Page) -> List[str]:
#         """Extract product links from page."""
#         links = []
        
#         try:
#             # Common product link selectors
#             selectors = [
#                 'a[href*="/product"]',
#                 'a[href*="/products/"]',
#                 'a[href*="/item"]',
#                 'a[href*="/p/"]',
#                 '.product a',
#                 '.product-card a',
#                 '.product-item a',
#                 '[data-product] a',
#             ]
            
#             for selector in selectors:
#                 try:
#                     elements = await page.query_selector_all(selector)
#                     for element in elements:
#                         href = await element.get_attribute('href')
#                         if href:
#                             full_url = urljoin(self._base_url, href)
#                             if (self._is_same_domain(full_url) and 
#                                 is_valid_product_url(full_url, self._domain)):
#                                 links.append(full_url)
#                 except Exception:
#                     continue
            
#         except Exception as e:
#             self._log("debug", f"Error extracting product links: {e}")
        
#         return list(set(links))
    
#     async def _save_product(self, product_data: Dict[str, Any]) -> Optional[int]:
#         """Save a product to the database."""
#         if not self._db or not self._job:
#             self.state.products_scraped += 1
#             return None
        
#         try:
#             # Check if product already exists
#             existing = None
#             if product_data.get('url'):
#                 from sqlalchemy import select
#                 query = select(Product).where(
#                     Product.url == product_data['url'],
#                     Product.job_id == self._job.id
#                 )
#                 result = await self._db.execute(query)
#                 existing = result.scalar_one_or_none()
            
#             if existing:
#                 # Update existing product
#                 for key, value in product_data.items():
#                     if value and hasattr(existing, key):
#                         setattr(existing, key, value)
#                 await self._db.commit()
#                 return existing.id
            
#             # Create new product
#             product = Product(
#                 job_id=self._job.id,
#                 source_domain=self._domain,
#                 product_id=product_data.get('product_id'),
#                 sku=product_data.get('sku'),
#                 upc=product_data.get('upc'),
#                 ean=product_data.get('ean'),
#                 name=product_data.get('name', ''),
#                 title=product_data.get('title'),
#                 description=product_data.get('description'),
#                 short_description=product_data.get('short_description'),
#                 price=product_data.get('price'),
#                 original_price=product_data.get('original_price'),
#                 sale_price=product_data.get('sale_price'),
#                 currency=product_data.get('currency', 'GBP'),
#                 price_text=product_data.get('price_text'),
#                 discount_percentage=product_data.get('discount_percentage'),
#                 in_stock=product_data.get('in_stock', True),
#                 stock_quantity=product_data.get('stock_quantity'),
#                 stock_status=product_data.get('stock_status'),
#                 url=product_data.get('url', ''),
#                 image_url=product_data.get('image_url'),
#                 thumbnail_url=product_data.get('thumbnail_url'),
#                 category=product_data.get('category'),
#                 subcategory=product_data.get('subcategory'),
#                 category_path=product_data.get('category_path'),
#                 categories=product_data.get('categories', []),
#                 brand=product_data.get('brand'),
#                 manufacturer=product_data.get('manufacturer'),
#                 vendor=product_data.get('vendor'),
#                 specifications=product_data.get('specifications', {}),
#                 features=product_data.get('features', []),
#                 tags=product_data.get('tags', []),
#                 attributes=product_data.get('attributes', {}),
#                 rating=product_data.get('rating'),
#                 review_count=product_data.get('review_count', 0),
#                 meta_title=product_data.get('meta_title'),
#                 meta_description=product_data.get('meta_description'),
#                 raw_data=product_data.get('raw_data', {}),
#             )
            
#             self._db.add(product)
#             await self._db.flush()
            
#             # Save images
#             images = product_data.get('images', [])
#             for i, img_data in enumerate(images):
#                 if isinstance(img_data, dict) and img_data.get('url'):
#                     image = ProductImage(
#                         product_id=product.id,
#                         url=img_data['url'],
#                         alt_text=img_data.get('alt_text'),
#                         position=img_data.get('position', i),
#                         is_primary=img_data.get('is_primary', i == 0),
#                     )
#                     self._db.add(image)
            
#             # Save variants
#             variants = product_data.get('variants', [])
#             for var_data in variants:
#                 if isinstance(var_data, dict) and var_data.get('name'):
#                     variant = ProductVariant(
#                         product_id=product.id,
#                         variant_id=var_data.get('variant_id'),
#                         sku=var_data.get('sku'),
#                         name=var_data['name'],
#                         attributes=var_data.get('attributes', {}),
#                         price=var_data.get('price'),
#                         original_price=var_data.get('original_price'),
#                         in_stock=var_data.get('in_stock', True),
#                         stock_quantity=var_data.get('stock_quantity'),
#                         image_url=var_data.get('image_url'),
#                     )
#                     self._db.add(variant)
            
#             await self._db.commit()
            
#             self.state.products_scraped += 1
            
#             # Update job stats periodically
#             if self.state.products_scraped % 10 == 0:
#                 await self._update_job_stats()
            
#             return product.id
            
#         except Exception as e:
#             self._log("error", f"Failed to save product: {e}")
#             await self._db.rollback()
#             return None
    
#     async def _update_progress(self) -> None:
#         """Update scraping progress."""
#         if not self._job or not self._db:
#             return
        
#         try:
#             # Calculate progress
#             if self.config.max_pages > 0:
#                 progress = min(100, (self.state.pages_scraped / self.config.max_pages) * 100)
#             elif self.config.max_products > 0:
#                 progress = min(100, (self.state.products_scraped / self.config.max_products) * 100)
#             else:
#                 progress = 0
            
#             # Update job
#             self._job.progress = progress
#             self._job.scraped_pages = self.state.pages_scraped
#             self._job.total_products = self.state.products_scraped
#             self._job.failed_pages = self.state.pages_failed
            
#             await self._db.commit()
            
#             # Call progress callback
#             if self._progress_callback:
#                 await self._progress_callback({
#                     'progress': progress,
#                     'pages_scraped': self.state.pages_scraped,
#                     'products_scraped': self.state.products_scraped,
#                     'pages_failed': self.state.pages_failed,
#                 })
                
#         except Exception as e:
#             self._log("debug", f"Failed to update progress: {e}")
    
#     async def _update_job_stats(self) -> None:
#         """Update job statistics in database."""
#         if not self._job or not self._db:
#             return
        
#         try:
#             self._job.scraped_pages = self.state.pages_scraped
#             self._job.total_products = self.state.products_scraped
#             self._job.failed_pages = self.state.pages_failed
#             await self._db.commit()
#         except Exception:
#             pass
    
#     async def _finalize(
#         self, 
#         status: str = "completed",
#         error: Optional[str] = None
#     ) -> Dict[str, Any]:
#         """Finalize the scraping job."""
#         duration = time.time() - self.state.start_time
        
#         # Update job in database
#         if self._job and self._db:
#             try:
#                 self._job.status = JobStatus(status)
#                 self._job.completed_at = datetime.utcnow()
#                 self._job.progress = 100 if status == "completed" else self._job.progress
#                 self._job.scraped_pages = self.state.pages_scraped
#                 self._job.total_products = self.state.products_scraped
#                 self._job.failed_pages = self.state.pages_failed
                
#                 if error:
#                     self._job.error_message = error
                
#                 self._job.logs = self.state.logs[-100]  # Keep last 100 logs
                
#                 await self._db.commit()
                
#             except Exception as e:
#                 self._log("error", f"Failed to update job: {e}")
        
#         # Compile results
#         result = {
#             "status": status,
#             "job_id": self._job.job_id if self._job else None,
#             "url": self._base_url,
#             "domain": self._domain,
#             "platform": self.config.platform,
#             "duration_seconds": round(duration, 2),
#             "pages_scraped": self.state.pages_scraped,
#             "pages_failed": self.state.pages_failed,
#             "products_scraped": self.state.products_scraped,
#             "urls_visited": len(self.state.visited_urls),
#             "product_urls_found": len(self.state.product_urls),
#             "category_urls_found": len(self.state.category_urls),
#             "errors": self.state.errors[-10],  # Last 10 errors
#             "extraction_stats": self._product_extractor.get_stats() if self._product_extractor else {},
#             "cleaning_stats": self._data_cleaner.get_stats() if self._data_cleaner else {},
#         }
        
#         if error:
#             result["error"] = error
        
#         self._log("info", f"Scraping completed: {self.state.products_scraped} products in {duration:.2f}s")
        
#         return result
    
#     def _should_stop(self) -> bool:
#         """Check if scraping should stop."""
#         if self.state.is_cancelled:
#             return True
        
#         if self.state.pages_scraped >= self.config.max_pages:
#             self._log("info", f"Reached max pages limit: {self.config.max_pages}")
#             return True
        
#         if self.state.products_scraped >= self.config.max_products:
#             self._log("info", f"Reached max products limit: {self.config.max_products}")
#             return True
        
#         return False
    
#     def _should_visit_url(self, url: str) -> bool:
#         """Check if a URL should be visited."""
#         # Normalize URL
#         url = normalize_url(url, self._base_url)
        
#         # Already visited
#         if url in self.state.visited_urls:
#             return False
        
#         # Not same domain
#         if not self._is_same_domain(url):
#             return False
        
#         # Check exclude patterns
#         url_lower = url.lower()
#         for pattern in self.DEFAULT_EXCLUDE_PATTERNS:
#             if re.search(pattern, url_lower):
#                 return False
        
#         # Check custom exclude patterns
#         if self.config.exclude_patterns:
#             for pattern in self.config.exclude_patterns:
#                 if re.search(pattern, url_lower):
#                     return False
        
#         # Check URL patterns (if specified, URL must match)
#         if self.config.url_patterns:
#             matches = False
#             for pattern in self.config.url_patterns:
#                 if re.search(pattern, url_lower):
#                     matches = True
#                     break
#             if not matches:
#                 return False
        
#         return True
    
#     def _is_same_domain(self, url: str) -> bool:
#         """Check if URL is on the same domain."""
#         try:
#             parsed = urlparse(url)
#             url_domain = parsed.netloc.lower()
            
#             # Remove www prefix for comparison
#             if url_domain.startswith("www."):
#                 url_domain = url_domain[4:]
            
#             base_domain = self._domain
#             if base_domain.startswith("www."):
#                 base_domain = base_domain[4:]
            
#             return url_domain == base_domain
            
#         except Exception:
#             return False
    
#     def _log(self, level: str, message: str) -> None:
#         """Add a log entry."""
#         log_entry = {
#             "timestamp": datetime.utcnow().isoformat(),
#             "level": level,
#             "message": message
#         }
        
#         self.state.logs.append(log_entry)
        
#         # Also log to logger
#         log_method = getattr(logger, level, logger.info)
#         log_method(f"[{self._domain}] {message}")
        
#         # Store errors separately
#         if level == "error":
#             self.state.errors.append(log_entry)
    
#     def pause(self) -> None:
#         """Pause the scraping job."""
#         self.state.is_paused = True
#         self._log("info", "Scraping paused")
    
#     def resume(self) -> None:
#         """Resume the scraping job."""
#         self.state.is_paused = False
#         self._log("info", "Scraping resumed")
    
#     def cancel(self) -> None:
#         """Cancel the scraping job."""
#         self.state.is_cancelled = True
#         self._log("info", "Scraping cancelled")
    
#     def get_state(self) -> Dict[str, Any]:
#         """Get current scraper state."""
#         return {
#             "pages_scraped": self.state.pages_scraped,
#             "pages_failed": self.state.pages_failed,
#             "products_scraped": self.state.products_scraped,
#             "urls_visited": len(self.state.visited_urls),
#             "is_paused": self.state.is_paused,
#             "is_cancelled": self.state.is_cancelled,
#             "duration": time.time() - self.state.start_time if self.state.start_time else 0,
#             "current_depth": self.state.current_depth,
#         }


# class ScraperFactory:
#     """Factory for creating scrapers with platform-specific configurations."""
    
#     PLATFORM_CONFIGS = {
#         "shopify": ScraperConfig(
#             follow_product_links=True,
#             selectors={
#                 "product_card": ".product-card, .grid-product, .product-item",
#                 "product_link": "a[href*='/products/']",
#                 "product_name": ".product-card__title, .product-title",
#                 "product_price": ".price, .money",
#             }
#         ),
#         "woocommerce": ScraperConfig(
#             follow_product_links=True,
#             selectors={
#                 "product_card": ".product, .type-product",
#                 "product_link": ".woocommerce-LoopProduct-link",
#                 "product_name": ".woocommerce-loop-product__title",
#                 "product_price": ".price",
#             }
#         ),
#         "magento": ScraperConfig(
#             follow_product_links=True,
#             selectors={
#                 "product_card": ".product-item",
#                 "product_link": ".product-item-link",
#                 "product_name": ".product-item-name",
#                 "product_price": ".price-box .price",
#             }
#         ),
#     }
    
#     @classmethod
#     def create(
#         cls,
#         platform: Optional[str] = None,
#         config: Optional[ScraperConfig] = None
#     ) -> ScraperEngine:
#         """
#         Create a scraper engine with platform-specific configuration.
        
#         Args:
#             platform: E-commerce platform (shopify, woocommerce, etc.)
#             config: Custom configuration override
        
#         Returns:
#             Configured ScraperEngine
#         """
#         if config:
#             return ScraperEngine(config)
        
#         if platform and platform in cls.PLATFORM_CONFIGS:
#             return ScraperEngine(cls.PLATFORM_CONFIGS[platform])
        
#         return ScraperEngine()


# # Convenience function for simple scraping
# async def scrape_website(
#     url: str,
#     max_pages: int = 100,
#     max_products: int = 10000,
#     **kwargs
# ) -> Dict[str, Any]:
#     """
#     Simple function to scrape a website.
    
#     Args:
#         url: Website URL to scrape
#         max_pages: Maximum pages to scrape
#         max_products: Maximum products to extract
#         **kwargs: Additional config options
    
#     Returns:
#         Scraping results
#     """
#     config = ScraperConfig(
#         max_pages=max_pages,
#         max_products=max_products,
#         **kwargs
#     )
    
#     engine = ScraperEngine(config)
    
#     # Generate a temporary job ID
#     job_id = 0  # No database
    
#     result = await engine.run(
#         job_id=job_id,
#         start_url=url,
#         config=config
#     )
    
#     return result