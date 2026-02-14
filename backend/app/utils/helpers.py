"""
Helper Utilities
Common utility functions used throughout the scraper platform.
"""

import re
import asyncio
import hashlib
import uuid
from typing import Optional, Any, Callable, TypeVar, List, Dict
from urllib.parse import urlparse, urljoin, urlunparse, parse_qs, urlencode
from functools import wraps
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

T = TypeVar('T')


# ============== URL Utilities ==============

def extract_domain(url: str) -> str:
    """
    Extract the domain from a URL.
    
    Args:
        url: Full URL
    
    Returns:
        Domain name (e.g., 'example.com')
    """
    try:
        parsed = urlparse(url)
        domain = parsed.netloc
        # Remove www. prefix
        if domain.startswith("www."):
            domain = domain[4:]
        return domain.lower()
    except Exception:
        return ""


def normalize_url(url: str, base_url: Optional[str] = None) -> str:
    """
    Normalize a URL to a consistent format.
    
    Args:
        url: URL to normalize
        base_url: Base URL for relative URLs
    
    Returns:
        Normalized absolute URL
    """
    if not url:
        return ""
    
    url = url.strip()
    
    # Handle relative URLs
    if base_url and not url.startswith(('http://', 'https://', '//')):
        url = urljoin(base_url, url)
    
    # Handle protocol-relative URLs
    if url.startswith("//"):
        url = "https:" + url
    
    try:
        parsed = urlparse(url)
        
        # Normalize the path
        path = parsed.path or "/"
        
        # Remove duplicate slashes
        path = re.sub(r'/+', '/', path)
        
        # Remove trailing slash for non-root paths
        if path != "/" and path.endswith("/"):
            path = path[:-1]
        
        # Rebuild URL
        normalized = urlunparse((
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            path,
            parsed.params,
            parsed.query,
            ""  # Remove fragment
        ))
        
        return normalized
    
    except Exception as e:
        logger.warning(f"Failed to normalize URL {url}: {e}")
        return url


def is_valid_url(url: str) -> bool:
    """Check if a string is a valid URL."""
    try:
        result = urlparse(url)
        return all([result.scheme in ['http', 'https'], result.netloc])
    except Exception:
        return False


def is_valid_product_url(url: str, domain: Optional[str] = None) -> bool:
    """
    Check if a URL is likely a product page URL.
    
    Args:
        url: URL to check
        domain: Optional domain to match
    
    Returns:
        True if URL looks like a product page
    """
    if not is_valid_url(url):
        return False
    
    parsed = urlparse(url)
    path = parsed.path.lower()
    
    # Check domain if provided
    if domain and domain not in parsed.netloc:
        return False
    
    # Exclude patterns
    exclude_patterns = [
        r'/cart',
        r'/checkout',
        r'/account',
        r'/login',
        r'/register',
        r'/wishlist',
        r'/search',
        r'/contact',
        r'/about',
        r'/faq',
        r'/help',
        r'/privacy',
        r'/terms',
        r'/returns',
        r'/shipping',
        r'/blog',
        r'/news',
        r'\.pdf$',
        r'\.jpg$',
        r'\.png$',
        r'\.gif$',
    ]
    
    for pattern in exclude_patterns:
        if re.search(pattern, path):
            return False
    
    # Include patterns (common product URL patterns)
    include_patterns = [
        r'/product[s]?/',
        r'/item[s]?/',
        r'/p/',
        r'/pd/',
        r'/dp/',  # Amazon style
        r'/goods/',
        r'-p-\d+',
        r'/\d+\.html$',
        r'[?&]product[_-]?id=',
        r'[?&]sku=',
    ]
    
    for pattern in include_patterns:
        if re.search(pattern, path + '?' + parsed.query):
            return True
    
    # If path has a reasonable structure (not just root)
    path_parts = [p for p in path.split('/') if p]
    if len(path_parts) >= 2:
        return True
    
    return False


def get_url_without_params(url: str, keep_params: Optional[List[str]] = None) -> str:
    """
    Remove query parameters from URL.
    
    Args:
        url: URL to process
        keep_params: List of parameter names to keep
    
    Returns:
        URL without query parameters (or with only kept params)
    """
    parsed = urlparse(url)
    
    if keep_params:
        params = parse_qs(parsed.query)
        filtered_params = {k: v for k, v in params.items() if k in keep_params}
        query = urlencode(filtered_params, doseq=True)
    else:
        query = ""
    
    return urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        parsed.params,
        query,
        ""
    ))


# ============== Text Cleaning ==============

def clean_text(text: Optional[str]) -> str:
    """
    Clean and normalize text.
    
    Args:
        text: Text to clean
    
    Returns:
        Cleaned text
    """
    if not text:
        return ""
    
    # Convert to string
    text = str(text)
    
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove leading/trailing whitespace
    text = text.strip()
    
    # Remove null characters
    text = text.replace('\x00', '')
    
    return text


def clean_price(price_text: Optional[str]) -> Optional[float]:
    """
    Extract numeric price from price text.
    
    Args:
        price_text: Price string (e.g., "£199.99", "$1,299.00")
    
    Returns:
        Float price value or None
    """
    if not price_text:
        return None
    
    # Convert to string and clean
    price_text = str(price_text).strip()
    
    # Remove currency symbols and common text
    price_text = re.sub(r'[£$€¥₹]', '', price_text)
    price_text = re.sub(r'(GBP|USD|EUR|from|From|starting|Starting|was|Was)', '', price_text, flags=re.IGNORECASE)
    
    # Remove thousand separators (commas)
    price_text = price_text.replace(',', '')
    
    # Extract first number
    match = re.search(r'(\d+(?:\.\d{1,2})?)', price_text)
    
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            pass
    
    return None


def extract_currency(price_text: Optional[str]) -> str:
    """
    Extract currency code from price text.
    
    Args:
        price_text: Price string
    
    Returns:
        Currency code (default: GBP)
    """
    if not price_text:
        return "GBP"
    
    currency_map = {
        '£': 'GBP',
        '$': 'USD',
        '€': 'EUR',
        '¥': 'JPY',
        '₹': 'INR',
    }
    
    for symbol, code in currency_map.items():
        if symbol in price_text:
            return code
    
    # Check for text codes
    text_upper = price_text.upper()
    for code in ['GBP', 'USD', 'EUR', 'JPY', 'INR', 'CAD', 'AUD']:
        if code in text_upper:
            return code
    
    return "GBP"


def clean_html(html: Optional[str]) -> str:
    """
    Remove HTML tags and clean text.
    
    Args:
        html: HTML string
    
    Returns:
        Clean text without HTML tags
    """
    if not html:
        return ""
    
    # Remove script and style tags with content
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove HTML tags
    html = re.sub(r'<[^>]+>', ' ', html)
    
    # Decode HTML entities
    import html as html_module
    html = html_module.unescape(html)
    
    # Clean whitespace
    return clean_text(html)


# ============== Data Utilities ==============

def generate_job_id() -> str:
    """Generate a unique job ID."""
    return f"job_{uuid.uuid4().hex[:12]}"


def generate_product_hash(url: str, name: str) -> str:
    """
    Generate a unique hash for a product.
    
    Args:
        url: Product URL
        name: Product name
    
    Returns:
        MD5 hash string
    """
    content = f"{normalize_url(url)}:{clean_text(name)}"
    return hashlib.md5(content.encode()).hexdigest()


def safe_get(data: Dict, *keys, default: Any = None) -> Any:
    """
    Safely get nested dictionary values.
    
    Args:
        data: Dictionary to traverse
        *keys: Keys to access
        default: Default value if key not found
    
    Returns:
        Value at key path or default
    
    Usage:
        value = safe_get(data, 'product', 'price', 'amount', default=0)
    """
    for key in keys:
        if isinstance(data, dict):
            data = data.get(key, default)
        elif isinstance(data, list) and isinstance(key, int):
            try:
                data = data[key]
            except IndexError:
                return default
        else:
            return default
    return data


def flatten_dict(d: Dict, parent_key: str = '', sep: str = '_') -> Dict:
    """
    Flatten a nested dictionary.
    
    Args:
        d: Dictionary to flatten
        parent_key: Prefix for keys
        sep: Separator between keys
    
    Returns:
        Flattened dictionary
    """
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


# ============== Async Utilities ==============

async def retry_async(
    func: Callable,
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,)
) -> Any:
    """
    Retry an async function with exponential backoff.
    
    Args:
        func: Async function to call
        max_attempts: Maximum retry attempts
        delay: Initial delay between retries
        backoff: Backoff multiplier
        exceptions: Tuple of exceptions to catch
    
    Returns:
        Function result
    
    Raises:
        Last exception if all retries fail
    """
    last_exception = None
    current_delay = delay
    
    for attempt in range(max_attempts):
        try:
            return await func()
        except exceptions as e:
            last_exception = e
            if attempt < max_attempts - 1:
                logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {current_delay}s...")
                await asyncio.sleep(current_delay)
                current_delay *= backoff
            else:
                logger.error(f"All {max_attempts} attempts failed")
    
    raise last_exception


def async_timeout(seconds: float):
    """
    Decorator to add timeout to async functions.
    
    Args:
        seconds: Timeout in seconds
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=seconds
                )
            except asyncio.TimeoutError:
                raise TimeoutError(f"Function {func.__name__} timed out after {seconds}s")
        return wrapper
    return decorator


async def gather_with_concurrency(
    n: int,
    *tasks,
    return_exceptions: bool = False
) -> List[Any]:
    """
    Run tasks with limited concurrency.
    
    Args:
        n: Maximum concurrent tasks
        *tasks: Coroutines to run
        return_exceptions: Whether to return exceptions instead of raising
    
    Returns:
        List of results
    """
    semaphore = asyncio.Semaphore(n)
    
    async def sem_task(task):
        async with semaphore:
            return await task
    
    return await asyncio.gather(
        *[sem_task(task) for task in tasks],
        return_exceptions=return_exceptions
    )


# ============== Validation Utilities ==============

def is_valid_email(email: str) -> bool:
    """Check if a string is a valid email address."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def is_valid_sku(sku: str) -> bool:
    """Check if a string looks like a valid SKU."""
    if not sku or len(sku) < 2:
        return False
    # SKU typically contains alphanumeric characters, hyphens, underscores
    return bool(re.match(r'^[A-Za-z0-9\-_\.]+$', sku))


def truncate(text: str, max_length: int = 100, suffix: str = '...') -> str:
    """Truncate text to a maximum length."""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


# ============== Date Utilities ==============

def parse_date(date_str: str) -> Optional[datetime]:
    """
    Parse various date formats.
    
    Args:
        date_str: Date string
    
    Returns:
        datetime object or None
    """
    formats = [
        '%Y-%m-%d',
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%dT%H:%M:%SZ',
        '%Y-%m-%dT%H:%M:%S.%f',
        '%d/%m/%Y',
        '%d-%m-%Y',
        '%m/%d/%Y',
        '%B %d, %Y',
        '%b %d, %Y',
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue
    
    return None