from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass
from typing import Deque, Set, Optional
from urllib.parse import urlparse, urljoin


@dataclass
class FrontierItem:
    url: str
    depth: int = 0
    score: float = 0.0


class URLFrontier:
    """
    Manages the crawl frontier:
    - URL queue (FIFO with scoring support)
    - Visited URL tracking
    - Domain restriction
    - Depth limiting
    """

    def __init__(
        self,
        start_url: str,
        max_depth: int = 4,
        max_urls: int = 10_000,
        allowed_domain: Optional[str] = None,
    ):
        self.start_url = start_url.rstrip("/")
        self.max_depth = max_depth
        self.max_urls = max_urls

        parsed = urlparse(start_url)
        self.allowed_domain = allowed_domain or parsed.netloc

        self._queue: Deque[FrontierItem] = deque()
        self._visited: Set[str] = set()
        self._lock = asyncio.Lock()

        self._enqueue(self.start_url, depth=0)

    # ---------------------------
    # Public API
    # ---------------------------

    async def get_next(self) -> Optional[FrontierItem]:
        async with self._lock:
            if not self._queue:
                return None
            return self._queue.popleft()

    async def add_url(self, url: str, *, depth: int, score: float = 0.0) -> bool:
        """
        Add a new URL to the frontier if valid.
        Returns True if enqueued, False otherwise.
        """
        normalized = self._normalize(url)
        if not normalized:
            return False

        async with self._lock:
            if normalized in self._visited:
                return False

            if len(self._visited) + len(self._queue) >= self.max_urls:
                return False

            if depth > self.max_depth:
                return False

            self._enqueue(normalized, depth, score)
            return True

    async def mark_visited(self, url: str) -> None:
        async with self._lock:
            self._visited.add(url)

    def stats(self) -> dict:
        return {
            "queued": len(self._queue),
            "visited": len(self._visited),
            "max_depth": self.max_depth,
            "allowed_domain": self.allowed_domain,
        }

    # ---------------------------
    # Internal Helpers
    # ---------------------------

    def _enqueue(self, url: str, depth: int, score: float = 0.0) -> None:
        self._queue.append(FrontierItem(url=url, depth=depth, score=score))

    def _normalize(self, url: str) -> Optional[str]:
        if not url:
            return None

        parsed = urlparse(url)

        # Resolve relative URLs
        if not parsed.netloc:
            url = urljoin(self.start_url, url)
            parsed = urlparse(url)

        # Domain restriction
        if parsed.netloc != self.allowed_domain:
            return None

        # Remove fragments
        cleaned = parsed._replace(fragment="").geturl()
        return cleaned.rstrip("/")
