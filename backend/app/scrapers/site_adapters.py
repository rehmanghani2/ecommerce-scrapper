"""
Declarative storefront compatibility profiles for the initial UK validation set.

Selectors are candidate patterns, not claims of live-site verification. Keep profiles
small and override them only after fixture or permitted live-browser evidence.
"""
from dataclasses import dataclass
from typing import Any, Dict, Optional
from urllib.parse import urlparse


@dataclass(frozen=True)
class SiteAdapter:
    key: str
    name: str
    hosts: tuple[str, ...]
    platform_hint: str
    selector_config: Dict[str, Any]
    pagination_selectors: tuple[str, ...]
    category_selectors: tuple[str, ...]


_COMMON_FIELDS = {
    "name": "[itemprop='name'], .product-title, .product-name, .product-item-link, .product-item-name, h2, h3",
    "price": "[itemprop='price']::attr(content), .price, .product-price, .price-box .price, .current-price",
    "image_url": "img::attr(data-src), img::attr(data-lazy-src), img::attr(data-original), img::attr(src), [itemprop='image']::attr(content)",
    "url": "a.product-item-link::attr(href), a.product-link::attr(href), a::attr(href), [itemprop='url']::attr(href)",
    "sku": "[itemprop='sku']::attr(content), [data-sku]::attr(data-sku), .sku",
    "brand": "[itemprop='brand']::attr(content), .product-brand, .brand, .manufacturer",
    "availability": "[itemprop='availability']::attr(href), .stock-status, .availability, .stock",
}


def _profile(key: str, name: str, hosts: tuple[str, ...], platform: str,
             containers: str, pagination: tuple[str, ...],
             categories: tuple[str, ...]) -> SiteAdapter:
    return SiteAdapter(
        key=key,
        name=name,
        hosts=hosts,
        platform_hint=platform,
        selector_config={"product_container": containers, "fields": dict(_COMMON_FIELDS)},
        pagination_selectors=pagination,
        category_selectors=categories,
    )


SITE_ADAPTERS = (
    _profile(
        "leeli-cycles", "Leeli Cycles", ("leelicycles.co.uk",), "generic",
        ".product-card, .product-item, .product, li.product, [data-product-id]",
        ("a[rel='next']", ".pagination a.next", "a.next.page-numbers"),
        ("nav a[href*='/collections/']", "nav a[href*='/category/']"),
    ),
    _profile(
        "ballicom", "Ballicom", ("ballicom.co.uk",), "generic",
        ".product-item, .product-card, .product, li.product, [data-product-id]",
        ("a[rel='next']", ".pagination a.next", ".pages a.next"),
        ("nav a[href*='/category/']", "nav a[href*='/categories/']"),
    ),
    _profile(
        "exertis-store", "Exertis Store", ("store.exertis.co.uk",), "generic",
        ".product-item, .product-card, .product-tile, [data-product-id], [data-product]",
        ("a[rel='next']", ".pagination a.next", "a[aria-label*='Next']"),
        ("nav a[href*='/category/']", "nav a[href*='/catalog/']"),
    ),
    _profile(
        "rs-components", "RS Components UK", ("uk.rs-online.com",), "generic",
        ".product-card, .product-tile, .product-item, [data-testid*='product'], [data-product-id]",
        ("a[rel='next']", "a[aria-label*='Next']", ".pagination a.next"),
        ("nav a[href*='/web/c/']", "a[href*='/web/c/']", "[data-testid*='category'] a"),
    ),
)

_HOST_INDEX = {host: adapter for adapter in SITE_ADAPTERS for host in adapter.hosts}


def get_site_adapter(url: str) -> Optional[SiteAdapter]:
    """Return an exact-host adapter; never match an unrelated lookalike domain."""
    try:
        host = (urlparse(url).hostname or "").lower().rstrip(".")
    except (TypeError, ValueError):
        return None
    if host.startswith("www."):
        host = host[4:]
    return _HOST_INDEX.get(host)


def list_site_adapters() -> tuple[SiteAdapter, ...]:
    return SITE_ADAPTERS
