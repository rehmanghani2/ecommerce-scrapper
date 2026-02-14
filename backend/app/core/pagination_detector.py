"""
pagination_detector.py
-----------------------
Generic pagination detection for ecommerce category/listing pages.

Purpose:
- Detect "next page" URLs without site-specific logic
- Support common ecommerce pagination patterns
- Feed discovered pagination URLs back into the crawler

Design principles:
- Heuristic-based (not hardcoded per site)
- Safe (never crashes crawler)
- Works with static HTML (Playwright-rendered)
"""

from typing import List, Optional
from urllib.parse import urljoin, urlparse, parse_qs

from bs4 import BeautifulSoup

from app.utils.logger import get_logger

logger = get_logger(__name__)


class PaginationDetector:
    """
    Generic pagination detector.
    """

    COMMON_NEXT_TEXTS = {
        "next", "next page", ">", ">>", "›", "→",
        "load more", "show more"
    }

    def __init__(self, base_domain: str):
        self.base_domain = base_domain

    def detect(self, html: str, base_url: str) -> List[str]:
        """
        Detect pagination URLs from HTML.
        Returns a list of candidate next-page URLs.
        """
        urls = []

        try:
            soup = BeautifulSoup(html, "lxml")
        except Exception:
            soup = BeautifulSoup(html, "html.parser")

        # 1. rel="next"
        link = soup.find("link", rel="next")
        if link and link.get("href"):
            next_url = self._normalize(link.get("href"), base_url)
            if next_url:
                urls.append(next_url)

        # 2. Anchor text heuristics
        for a in soup.find_all("a", href=True):
            text = (a.get_text() or "").strip().lower()
            href = a.get("href")

            if not href:
                continue

            if text in self.COMMON_NEXT_TEXTS:
                next_url = self._normalize(href, base_url)
                if next_url:
                    urls.append(next_url)

        # 3. Page number increment heuristic (?page=2)
        numeric_next = self._detect_numeric_pagination(base_url)
        if numeric_next:
            urls.append(numeric_next)

        # Deduplicate
        return list(set(urls))

    def _normalize(self, href: str, base_url: str) -> Optional[str]:
        try:
            absolute = urljoin(base_url, href)
            parsed = urlparse(absolute)

            if parsed.netloc != self.base_domain:
                return None

            return absolute
        except Exception:
            return None

    def _detect_numeric_pagination(self, base_url: str) -> Optional[str]:
        """
        Detect and increment common pagination query params.
        Example: ?page=1 -> ?page=2
        """
        parsed = urlparse(base_url)
        query = parse_qs(parsed.query)

        for key in ("page", "p", "pg"):
            if key in query:
                try:
                    current = int(query[key][0])
                    query[key] = [str(current + 1)]
                    from urllib.parse import urlencode
                    return parsed._replace(query=urlencode(query, doseq=True)).geturl()
                except Exception:
                    return None

        return None
