"""
link_extractor.py
-----------------
Responsible for extracting and normalizing links from HTML pages.

This module is GENERIC by design and works across 200+ ecommerce websites.
It does NOT know about products or selectors.

Responsibilities:
- Extract <a href> links
- Normalize URLs
- Enforce same-domain rules
- Filter unwanted URLs (assets, mailto, javascript)
"""

from typing import List, Set
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from app.utils.logger import get_logger

logger = get_logger(__name__)


class LinkExtractor:
    """
    Generic link extractor for crawler
    """

    def __init__(self, base_domain: str):
        self.base_domain = base_domain

    def extract_links(self, html: str, base_url: str) -> List[str]:
        """
        Extract and normalize links from HTML
        """
        links: Set[str] = set()

        try:
            soup = BeautifulSoup(html, "lxml")
        except Exception:
            logger.warning("Failed to parse HTML with lxml, falling back to html.parser")
            soup = BeautifulSoup(html, "html.parser")

        for anchor in soup.find_all("a", href=True):
            href = anchor.get("href").strip()

            if not href:
                continue

            normalized = self._normalize_url(href, base_url)
            if not normalized:
                continue

            if self._is_valid_url(normalized):
                links.add(normalized)

        return list(links)

    def _normalize_url(self, href: str, base_url: str) -> str | None:
        """
        Convert relative URLs to absolute URLs
        """
        if href.startswith("javascript:") or href.startswith("mailto:"):
            return None

        try:
            return urljoin(base_url, href)
        except Exception:
            return None

    def _is_valid_url(self, url: str) -> bool:
        """
        Enforce domain and exclude static assets
        """
        parsed = urlparse(url)

        if not parsed.scheme.startswith("http"):
            return False

        if parsed.netloc != self.base_domain:
            return False

        # Skip static assets
        blocked_ext = (
            ".jpg", ".jpeg", ".png", ".gif", ".svg",
            ".css", ".js", ".ico", ".pdf",
        )

        if parsed.path.lower().endswith(blocked_ext):
            return False

        return True
