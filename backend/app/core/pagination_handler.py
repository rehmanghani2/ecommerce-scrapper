"""
Pagination Handler Module
Handles various pagination patterns in e-commerce websites.
"""

import re
from typing import Optional, List, Dict, Any, AsyncGenerator, Callable, Set
from dataclasses import dataclass, field
from enum import Enum
from urllib.parse import urlparse, urljoin, parse_qs, urlencode, urlunparse
from playwright.async_api import Page, ElementHandle, TimeoutError as PlaywrightTimeout
import logging

logger = logging.getLogger(__name__)


class PaginationType(str, Enum):
    """Types of pagination patterns."""
    NUMBERED = "numbered"           # Page 1, 2, 3...
    NEXT_BUTTON = "next_button"     # Next/Previous buttons
    LOAD_MORE = "load_more"         # Load more button
    INFINITE_SCROLL = "infinite_scroll"  # Scroll to load
    URL_PARAMETER = "url_parameter"  # ?page=1, ?p=2
    CURSOR = "cursor"               # Cursor-based (API)
    NONE = "none"                   # No pagination
    UNKNOWN = "unknown"


@dataclass
class PaginationConfig:
    """Configuration for pagination handling."""
    type: PaginationType = PaginationType.UNKNOWN
    max_pages: int = 100
    wait_time: int = 2000  # ms
    
    # Selectors
    next_button_selector: Optional[str] = None
    page_number_selector: Optional[str] = None
    load_more_selector: Optional[str] = None
    product_container_selector: Optional[str] = None
    
    # URL parameters
    page_param: str = "page"
    start_page: int = 1
    
    # Infinite scroll
    scroll_delay: int = 1500  # ms
    max_scroll_attempts: int = 50
    scroll_distance: int = 1000  # pixels
    
    # Detection
    auto_detect: bool = True


@dataclass
class PaginationState:
    """Current state of pagination."""
    current_page: int = 1
    total_pages: Optional[int] = None
    has_next: bool = True
    items_count: int = 0
    visited_urls: Set[str] = field(default_factory=set)
    scroll_position: int = 0
    last_item_count: int = 0
    stale_count: int = 0  # Count of pages with no new items


class PaginationHandler:
    """
    Handles various pagination patterns for web scraping.
    
    Supports:
    - Numbered pagination (1, 2, 3...)
    - Next/Previous buttons
    - Load More buttons
    - Infinite scroll
    - URL parameter pagination
    - Cursor-based pagination
    """
    
    # Common pagination selectors
    NEXT_BUTTON_SELECTORS = [
        'a[rel="next"]',
        '.pagination a.next',
        '.pagination .next a',
        '.pagination-next a',
        'a.next-page',
        'a[aria-label="Next"]',
        'a[aria-label="Next page"]',
        'button.next',
        '.pager-next a',
        'a.page-next',
        'li.next a',
        '.nav-next a',
        'a:has-text("Next")',
        'a:has-text("→")',
        'a:has-text(">")',
        '[class*="next"] a',
        '[class*="Next"] a',
    ]
    
    LOAD_MORE_SELECTORS = [
        'button.load-more',
        '.load-more button',
        'a.load-more',
        '#load-more',
        '[data-action="load-more"]',
        'button:has-text("Load More")',
        'button:has-text("Show More")',
        'button:has-text("View More")',
        'a:has-text("Load More")',
        '.show-more button',
        '.view-more button',
    ]
    
    PAGE_NUMBER_SELECTORS = [
        '.pagination a',
        '.pagination li a',
        '.pager a',
        '.pages a',
        'nav[aria-label="pagination"] a',
        '.page-numbers a',
        '.paginate a',
    ]
    
    def __init__(self, config: Optional[PaginationConfig] = None):
        """
        Initialize the pagination handler.
        
        Args:
            config: Pagination configuration
        """
        self.config = config or PaginationConfig()
        self.state = PaginationState()
        self._detected_type: Optional[PaginationType] = None
    
    async def detect_pagination_type(self, page: Page) -> PaginationType:
        """
        Detect the type of pagination used on the page.
        
        Args:
            page: Playwright page
        
        Returns:
            Detected pagination type
        """
        if self._detected_type:
            return self._detected_type
        
        logger.debug("Detecting pagination type...")
        
        # Check for infinite scroll indicators
        if await self._has_infinite_scroll(page):
            self._detected_type = PaginationType.INFINITE_SCROLL
            logger.info("Detected pagination type: INFINITE_SCROLL")
            return self._detected_type
        
        # Check for load more button
        load_more = await self._find_load_more_button(page)
        if load_more:
            self._detected_type = PaginationType.LOAD_MORE
            self.config.load_more_selector = await self._get_selector(load_more)
            logger.info("Detected pagination type: LOAD_MORE")
            return self._detected_type
        
        # Check for next button
        next_button = await self._find_next_button(page)
        if next_button:
            self._detected_type = PaginationType.NEXT_BUTTON
            self.config.next_button_selector = await self._get_selector(next_button)
            logger.info("Detected pagination type: NEXT_BUTTON")
            return self._detected_type
        
        # Check for numbered pagination
        page_numbers = await self._find_page_numbers(page)
        if page_numbers:
            self._detected_type = PaginationType.NUMBERED
            logger.info("Detected pagination type: NUMBERED")
            return self._detected_type
        
        # Check URL for page parameter
        url = page.url
        if self._has_page_parameter(url):
            self._detected_type = PaginationType.URL_PARAMETER
            logger.info("Detected pagination type: URL_PARAMETER")
            return self._detected_type
        
        # No pagination detected
        self._detected_type = PaginationType.NONE
        logger.info("No pagination detected")
        return self._detected_type
    
    async def _has_infinite_scroll(self, page: Page) -> bool:
        """Check if page uses infinite scroll."""
        # Check for common infinite scroll indicators
        indicators = [
            '[data-infinite-scroll]',
            '[data-infinite]',
            '.infinite-scroll',
            '.infinite-loader',
        ]
        
        for selector in indicators:
            if await page.query_selector(selector):
                return True
        
        # Check if scrolling loads more content
        try:
            initial_height = await page.evaluate('document.body.scrollHeight')
            await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            await page.wait_for_timeout(1000)
            new_height = await page.evaluate('document.body.scrollHeight')
            
            # Scroll back up
            await page.evaluate('window.scrollTo(0, 0)')
            
            return new_height > initial_height
        except Exception:
            return False
    
    async def _find_next_button(self, page: Page) -> Optional[ElementHandle]:
        """Find the next button element."""
        for selector in self.NEXT_BUTTON_SELECTORS:
            try:
                element = await page.query_selector(selector)
                if element:
                    # Verify it's visible and clickable
                    is_visible = await element.is_visible()
                    is_enabled = await element.is_enabled()
                    if is_visible and is_enabled:
                        return element
            except Exception:
                continue
        return None
    
    async def _find_load_more_button(self, page: Page) -> Optional[ElementHandle]:
        """Find the load more button element."""
        for selector in self.LOAD_MORE_SELECTORS:
            try:
                element = await page.query_selector(selector)
                if element:
                    is_visible = await element.is_visible()
                    if is_visible:
                        return element
            except Exception:
                continue
        return None
    
    async def _find_page_numbers(self, page: Page) -> List[ElementHandle]:
        """Find numbered pagination elements."""
        for selector in self.PAGE_NUMBER_SELECTORS:
            try:
                elements = await page.query_selector_all(selector)
                if len(elements) >= 2:  # At least 2 page numbers
                    return elements
            except Exception:
                continue
        return []
    
    def _has_page_parameter(self, url: str) -> bool:
        """Check if URL has a page parameter."""
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        page_params = ['page', 'p', 'pg', 'paged', 'offset', 'start']
        return any(param in params for param in page_params)
    
    async def _get_selector(self, element: ElementHandle) -> str:
        """Get a CSS selector for an element."""
        try:
            # Try to get a unique selector
            selector = await element.evaluate('''
                (el) => {
                    if (el.id) return '#' + el.id;
                    if (el.className) {
                        const classes = el.className.split(' ').filter(c => c).join('.');
                        if (classes) return el.tagName.toLowerCase() + '.' + classes;
                    }
                    return el.tagName.toLowerCase();
                }
            ''')
            return selector
        except Exception:
            return ""
    
    async def get_next_page_url(self, page: Page) -> Optional[str]:
        """
        Get the URL of the next page.
        
        Args:
            page: Current Playwright page
        
        Returns:
            Next page URL or None
        """
        pagination_type = await self.detect_pagination_type(page)
        
        if pagination_type == PaginationType.NEXT_BUTTON:
            return await self._get_next_button_url(page)
        
        elif pagination_type == PaginationType.NUMBERED:
            return await self._get_numbered_next_url(page)
        
        elif pagination_type == PaginationType.URL_PARAMETER:
            return self._get_parameter_next_url(page.url)
        
        return None
    
    async def _get_next_button_url(self, page: Page) -> Optional[str]:
        """Get URL from next button."""
        next_button = await self._find_next_button(page)
        if next_button:
            href = await next_button.get_attribute('href')
            if href:
                return urljoin(page.url, href)
        return None
    
    async def _get_numbered_next_url(self, page: Page) -> Optional[str]:
        """Get URL for next numbered page."""
        current_page = self.state.current_page
        next_page = current_page + 1
        
        page_numbers = await self._find_page_numbers(page)
        for element in page_numbers:
            try:
                text = await element.inner_text()
                if text.strip() == str(next_page):
                    href = await element.get_attribute('href')
                    if href:
                        return urljoin(page.url, href)
            except Exception:
                continue
        
        return None
    
    def _get_parameter_next_url(self, current_url: str) -> str:
        """Get URL with incremented page parameter."""
        parsed = urlparse(current_url)
        params = parse_qs(parsed.query)
        
        # Find and increment page parameter
        page_params = ['page', 'p', 'pg', 'paged']
        for param in page_params:
            if param in params:
                current_page = int(params[param][0])
                params[param] = [str(current_page + 1)]
                break
        else:
            # Add page parameter if not present
            params[self.config.page_param] = [str(self.state.current_page + 1)]
        
        # Rebuild URL
        new_query = urlencode(params, doseq=True)
        new_url = urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            new_query,
            parsed.fragment
        ))
        
        return new_url
    
    async def go_to_next_page(self, page: Page) -> bool:
        """
        Navigate to the next page.
        
        Args:
            page: Playwright page
        
        Returns:
            True if successfully navigated to next page
        """
        if not self.state.has_next:
            return False
        
        if self.state.current_page >= self.config.max_pages:
            logger.info(f"Reached max pages limit: {self.config.max_pages}")
            self.state.has_next = False
            return False
        
        pagination_type = await self.detect_pagination_type(page)
        
        success = False
        
        if pagination_type == PaginationType.NEXT_BUTTON:
            success = await self._click_next_button(page)
        
        elif pagination_type == PaginationType.LOAD_MORE:
            success = await self._click_load_more(page)
        
        elif pagination_type == PaginationType.INFINITE_SCROLL:
            success = await self._scroll_for_more(page)
        
        elif pagination_type == PaginationType.NUMBERED:
            success = await self._go_to_numbered_page(page)
        
        elif pagination_type == PaginationType.URL_PARAMETER:
            success = await self._go_to_url_page(page)
        
        else:
            self.state.has_next = False
            return False
        
        if success:
            self.state.current_page += 1
            self.state.visited_urls.add(page.url)
            await page.wait_for_timeout(self.config.wait_time)
        
        return success
    
    async def _click_next_button(self, page: Page) -> bool:
        """Click the next page button."""
        try:
            next_button = await self._find_next_button(page)
            if not next_button:
                self.state.has_next = False
                return False
            
            # Check if button is disabled
            is_disabled = await next_button.get_attribute('disabled')
            aria_disabled = await next_button.get_attribute('aria-disabled')
            classes = await next_button.get_attribute('class') or ''
            
            if is_disabled or aria_disabled == 'true' or 'disabled' in classes:
                self.state.has_next = False
                return False
            
            # Get current URL for comparison
            current_url = page.url
            
            # Click the button
            await next_button.click()
            
            # Wait for navigation or content change
            try:
                await page.wait_for_load_state('networkidle', timeout=10000)
            except PlaywrightTimeout:
                pass
            
            # Verify page changed
            new_url = page.url
            if new_url != current_url or pagination_type == PaginationType.LOAD_MORE:
                return True
            
            # Check if content changed
            await page.wait_for_timeout(1000)
            return True
            
        except Exception as e:
            logger.warning(f"Failed to click next button: {e}")
            return False
    
    async def _click_load_more(self, page: Page) -> bool:
        """Click the load more button."""
        try:
            # Count items before clicking
            product_selector = self.config.product_container_selector or '.product, .product-item'
            items_before = len(await page.query_selector_all(product_selector))
            
            # Find and click load more
            load_more = await self._find_load_more_button(page)
            if not load_more:
                self.state.has_next = False
                return False
            
            await load_more.click()
            
            # Wait for new content
            await page.wait_for_timeout(self.config.wait_time)
            
            # Check if new items loaded
            items_after = len(await page.query_selector_all(product_selector))
            
            if items_after > items_before:
                self.state.items_count = items_after
                self.state.stale_count = 0
                return True
            else:
                self.state.stale_count += 1
                if self.state.stale_count >= 3:
                    self.state.has_next = False
                return False
            
        except Exception as e:
            logger.warning(f"Failed to click load more: {e}")
            return False
    
    async def _scroll_for_more(self, page: Page) -> bool:
        """Scroll down to load more content."""
        try:
            product_selector = self.config.product_container_selector or '.product, .product-item'
            items_before = len(await page.query_selector_all(product_selector))
            
            # Scroll down
            await page.evaluate(f'window.scrollBy(0, {self.config.scroll_distance})')
            self.state.scroll_position += self.config.scroll_distance
            
            # Wait for content to load
            await page.wait_for_timeout(self.config.scroll_delay)
            
            # Check if new items loaded
            items_after = len(await page.query_selector_all(product_selector))
            
            if items_after > items_before:
                self.state.items_count = items_after
                self.state.last_item_count = items_before
                self.state.stale_count = 0
                return True
            else:
                self.state.stale_count += 1
                
                # Check if we've reached the bottom
                at_bottom = await page.evaluate('''
                    () => {
                        return (window.innerHeight + window.scrollY) >= document.body.scrollHeight;
                    }
                ''')
                
                if at_bottom or self.state.stale_count >= self.config.max_scroll_attempts:
                    self.state.has_next = False
                
                return False
            
        except Exception as e:
            logger.warning(f"Failed to scroll for more: {e}")
            return False
    
    async def _go_to_numbered_page(self, page: Page) -> bool:
        """Navigate to the next numbered page."""
        next_url = await self._get_numbered_next_url(page)
        if not next_url:
            self.state.has_next = False
            return False
        
        try:
            await page.goto(next_url, wait_until='networkidle')
            return True
        except Exception as e:
            logger.warning(f"Failed to go to numbered page: {e}")
            return False
    
    async def _go_to_url_page(self, page: Page) -> bool:
        """Navigate using URL parameter."""
        next_url = self._get_parameter_next_url(page.url)
        
        if next_url in self.state.visited_urls:
            self.state.has_next = False
            return False
        
        try:
            response = await page.goto(next_url, wait_until='networkidle')
            
            # Check if we got a valid response
            if response and response.status == 200:
                return True
            else:
                self.state.has_next = False
                return False
                
        except Exception as e:
            logger.warning(f"Failed to go to URL page: {e}")
            return False
    
    async def iterate_pages(
        self, 
        page: Page,
        callback: Callable[[Page, int], Any]
    ) -> AsyncGenerator[Any, None]:
        """
        Iterate through all pages and call callback for each.
        
        Args:
            page: Playwright page
            callback: Async function to call for each page
        
        Yields:
            Results from callback
        """
        # Process first page
        result = await callback(page, self.state.current_page)
        yield result
        
        # Process remaining pages
        while self.state.has_next and self.state.current_page < self.config.max_pages:
            success = await self.go_to_next_page(page)
            
            if success:
                result = await callback(page, self.state.current_page)
                yield result
            else:
                break
        
        logger.info(f"Pagination complete. Processed {self.state.current_page} pages.")
    
    async def get_total_pages(self, page: Page) -> Optional[int]:
        """
        Try to determine the total number of pages.
        
        Args:
            page: Playwright page
        
        Returns:
            Total pages or None if unknown
        """
        try:
            # Look for "Page X of Y" text
            page_info_patterns = [
                r'page\s+\d+\s+of\s+(\d+)',
                r'(\d+)\s+pages?',
                r'showing\s+\d+\s*-\s*\d+\s+of\s+(\d+)',
            ]
            
            text = await page.inner_text('body')
            for pattern in page_info_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    return int(match.group(1))
            
            # Count page number links
            page_numbers = await self._find_page_numbers(page)
            if page_numbers:
                max_page = 1
                for element in page_numbers:
                    try:
                        text = await element.inner_text()
                        num = int(text.strip())
                        max_page = max(max_page, num)
                    except (ValueError, Exception):
                        continue
                
                if max_page > 1:
                    return max_page
            
        except Exception as e:
            logger.debug(f"Could not determine total pages: {e}")
        
        return None
    
    def reset(self):
        """Reset pagination state."""
        self.state = PaginationState()
        self._detected_type = None
    
    def get_state(self) -> Dict[str, Any]:
        """Get current pagination state."""
        return {
            'current_page': self.state.current_page,
            'total_pages': self.state.total_pages,
            'has_next': self.state.has_next,
            'items_count': self.state.items_count,
            'pagination_type': self._detected_type.value if self._detected_type else 'unknown',
            'visited_urls_count': len(self.state.visited_urls)
        }