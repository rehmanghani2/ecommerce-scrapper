"""
Sitemap XML and Gzip parser service.
Supports standard sitemaps, sitemap indexes (nested recursive sitemaps),
compressed .xml.gz sitemaps, and product-specific URL filtering.
"""

import gzip
import io
import logging
import re
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional, Set
from urllib.parse import urlparse
import httpx

logger = logging.getLogger(__name__)

# Common namespaces in standard XML sitemaps
NAMESPACES = {
    "sm": "http://www.sitemaps.org/schemas/sitemap/0.9",
    "image": "http://www.google.com/schemas/sitemap-image/1.1",
    "video": "http://www.google.com/schemas/sitemap-video/1.1",
    "news": "http://www.google.com/schemas/sitemap-news/0.9",
}

# Heuristics to detect product URLs from e-commerce sitemaps
PRODUCT_PATH_PATTERNS = [
    r"/products?/",
    r"/item/",
    r"/p/",
    r"/dp/",
    r"/gp/product/",
    r"-p-\d+",
    r"/pd/",
    r"/goods/",
    r"/product-detail/",
]


class SitemapParser:
    """Parser for remote and local XML / GZ sitemaps."""

    def __init__(self, timeout: float = 20.0, max_depth: int = 3, max_urls: int = 15000):
        self.timeout = timeout
        self.max_depth = max_depth
        self.max_urls = max_urls

    def parse_xml_content(self, raw_bytes: bytes, url: str = "") -> Dict[str, Any]:
        """
        Parse raw XML bytes (automatically decompressing gzip if needed).
        Returns a dict containing:
          - is_index: bool
          - sitemaps: list of nested sitemap URLs
          - urls: list of item dicts (loc, lastmod, priority, changefreq, images)
        """
        # Decompress gzip if magic number or .gz URL
        if raw_bytes[:2] == b"\x1f\x8b" or url.lower().endswith(".gz"):
            try:
                raw_bytes = gzip.decompress(raw_bytes)
            except Exception as e:
                logger.warning(f"Failed to decompress gzip sitemap: {e}")

        # Decode text and strip xmlns prefixes if malformed
        try:
            text = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            text = raw_bytes.decode("latin-1", errors="ignore")

        # Parse XML root
        try:
            root = ET.fromstring(text)
        except ET.ParseError:
            # Fallback: remove problematic characters or declare default xmlns
            cleaned = re.sub(r'xmlns="[^"]+"', '', text, count=1)
            root = ET.fromstring(cleaned)

        tag = root.tag.lower()
        if "}" in tag:
            tag = tag.split("}", 1)[1]

        is_index = "sitemapindex" in tag
        sitemap_urls: List[str] = []
        entries: List[Dict[str, Any]] = []

        if is_index:
            # Contains nested sitemap tags
            for sitemap_node in root.findall(".//{http://www.sitemaps.org/schemas/sitemap/0.9}sitemap"):
                loc_node = sitemap_node.find("{http://www.sitemaps.org/schemas/sitemap/0.9}loc")
                if loc_node is not None and loc_node.text:
                    sitemap_urls.append(loc_node.text.strip())
            # Fallback if no namespace found
            if not sitemap_urls:
                for sitemap_node in root.findall(".//sitemap"):
                    loc_node = sitemap_node.find("loc")
                    if loc_node is not None and loc_node.text:
                        sitemap_urls.append(loc_node.text.strip())
        else:
            # Contains url tags
            for url_node in root.findall(".//{http://www.sitemaps.org/schemas/sitemap/0.9}url"):
                loc = url_node.findtext("{http://www.sitemaps.org/schemas/sitemap/0.9}loc")
                lastmod = url_node.findtext("{http://www.sitemaps.org/schemas/sitemap/0.9}lastmod")
                changefreq = url_node.findtext("{http://www.sitemaps.org/schemas/sitemap/0.9}changefreq")
                priority = url_node.findtext("{http://www.sitemaps.org/schemas/sitemap/0.9}priority")

                # Google image extension
                image_loc = None
                img_node = url_node.find(".//{http://www.google.com/schemas/sitemap-image/1.1}image")
                if img_node is not None:
                    image_loc = img_node.findtext("{http://www.google.com/schemas/sitemap-image/1.1}loc")

                if loc:
                    entries.append({
                        "loc": loc.strip(),
                        "lastmod": lastmod.strip() if lastmod else None,
                        "changefreq": changefreq.strip() if changefreq else None,
                        "priority": float(priority.strip()) if priority else None,
                        "image": image_loc.strip() if image_loc else None,
                    })

            # Fallback if no namespace matched
            if not entries:
                for url_node in root.findall(".//url"):
                    loc = url_node.findtext("loc")
                    lastmod = url_node.findtext("lastmod")
                    if loc:
                        entries.append({
                            "loc": loc.strip(),
                            "lastmod": lastmod.strip() if lastmod else None,
                        })

        return {
            "is_index": is_index,
            "sitemaps": sitemap_urls,
            "entries": entries,
            "total": len(sitemap_urls) if is_index else len(entries),
        }

    async def fetch_and_parse(
        self,
        sitemap_url: str,
        filter_products_only: bool = False,
        headers: Optional[Dict[str, str]] = None,
        proxy_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Fetch remote sitemap, traverse sitemap indexes up to max_depth,
        and collect all unique product URLs.
        """
        default_headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "text/xml,application/xml,application/gzip,application/octet-stream,*/*",
        }
        if headers:
            default_headers.update(headers)

        discovered_urls: Set[str] = set()
        visited_sitemaps: Set[str] = set()
        sitemap_queue: List[tuple] = [(sitemap_url, 0)]  # (url, depth)
        all_entries: List[Dict[str, Any]] = []

        client_kwargs: Dict[str, Any] = {
            "headers": default_headers,
            "timeout": self.timeout,
            "follow_redirects": True,
            "verify": False,
        }
        if proxy_url:
            client_kwargs["proxy"] = proxy_url

        async with httpx.AsyncClient(**client_kwargs) as client:
            while sitemap_queue and len(discovered_urls) < self.max_urls:
                curr_sitemap, depth = sitemap_queue.pop(0)
                if curr_sitemap in visited_sitemaps:
                    continue
                visited_sitemaps.add(curr_sitemap)

                try:
                    resp = await client.get(curr_sitemap)
                    if resp.status_code != 200:
                        logger.warning(f"Sitemap {curr_sitemap} returned HTTP {resp.status_code}")
                        continue

                    parsed = self.parse_xml_content(resp.content, curr_sitemap)

                    if parsed["is_index"] and depth < self.max_depth:
                        # Prioritize product-specific sitemaps (e.g. sitemap_products_1.xml)
                        child_sitemaps = parsed["sitemaps"]
                        if filter_products_only:
                            prod_sitemaps = [s for s in child_sitemaps if "product" in s.lower()]
                            if prod_sitemaps:
                                child_sitemaps = prod_sitemaps

                        for child in child_sitemaps:
                            if child not in visited_sitemaps:
                                sitemap_queue.append((child, depth + 1))
                    else:
                        for entry in parsed["entries"]:
                            loc = entry["loc"]
                            if filter_products_only and not self.is_likely_product_url(loc):
                                continue
                            if loc not in discovered_urls:
                                discovered_urls.add(loc)
                                all_entries.append(entry)
                                if len(discovered_urls) >= self.max_urls:
                                    break

                except Exception as e:
                    logger.error(f"Error fetching/parsing sitemap {curr_sitemap}: {e}")

        return {
            "success": True,
            "sitemap_url": sitemap_url,
            "sitemaps_inspected": len(visited_sitemaps),
            "total_urls": len(discovered_urls),
            "urls": list(discovered_urls),
            "sample_entries": all_entries[:50],
        }

    @staticmethod
    def is_likely_product_url(url: str) -> bool:
        """Check if URL matches typical e-commerce product detail pattern."""
        u = url.lower()
        # Exclude typical non-product assets and taxonomies
        if any(ign in u for ign in ["/category/", "/categories/", "/collections/", "/blog/", "/pages/", "/cart", "/account", "/checkout"]):
            return False
        return any(re.search(pat, u) for pat in PRODUCT_PATH_PATTERNS)


sitemap_parser = SitemapParser()
