"""
Scraper API routes.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Dict, Any
import uuid
import json
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

from app.models.database import get_db
from app.models.job import Job, JobStatus, JobType
from app.models.selector_preset import SelectorPreset
from app.schemas.scraper_schema import (
    ScraperRequest, ScraperResponse, ScraperPreviewRequest,
    DetectedSelectors, ScraperConfig, SelectorConfig
)
from app.core.pattern_detector import PatternDetector
from app.models.user import User
from app.api.routes.auth import get_optional_current_user
from app.services.visual_picker_service import visual_picker_service
from app.services.ai_extractor_service import ai_extractor_service


router = APIRouter()


@router.post("/start", response_model=ScraperResponse)
async def start_scraping(
    request: ScraperRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    """
    Start a new scraping job.
    
    This endpoint initiates a scraping job for the given URL.
    The job runs in the background and progress can be tracked via the jobs API.
    """
    try:
        # Parse URL to get domain
        parsed_url = urlparse(str(request.url))
        domain = parsed_url.netloc
        
        # Generate unique job ID
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        
        # Create job record
        job = Job(
            job_id=job_id,
            name=request.name or f"Scrape {domain}",
            description=request.description,
            url=str(request.url),
            domain=domain,
            job_type=JobType.FULL_SITE,
            status=JobStatus.PENDING,
            user_id=current_user.id if current_user else 1,
            config=request.config.model_dump() if request.config else {}
        )
        
        db.add(job)
        await db.commit()
        await db.refresh(job)
        
        # Start scraping in background
        # In production, this would be sent to Celery
        background_tasks.add_task(
            run_scraper_job,
            job.id,
            str(request.url),
            request.config
        )
        
        return ScraperResponse(
            success=True,
            message="Scraping job started successfully",
            job_id=job_id,
            status="pending"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start scraping job: {str(e)}"
        )


# 
# Website discovery limits are intentionally bounded for interactive analysis.
_DISCOVERY_MAX_LINKS = 500
_DISCOVERY_MAX_CATEGORIES = 100
_DISCOVERY_TIMEOUT_MS = 25000


def _is_public_target(url: str) -> bool:
    """Allow only HTTP(S) targets whose resolved addresses are globally routable."""
    import ipaddress
    import socket

    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            return False
        if parsed.username or parsed.password:
            return False
        host = parsed.hostname.lower().strip(".")
        if host in {"localhost", "localhost.localdomain"} or host.endswith(".local"):
            return False
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        addresses = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
        return bool(addresses) and all(
            ipaddress.ip_address(item[4][0]).is_global for item in addresses
        )
    except (OSError, ValueError, TypeError, OverflowError):
        return False


def _is_safe_network_request(url: str) -> bool:
    """Permit browser-local schemes, but validate every HTTP(S) request target."""
    parsed = urlparse(url)
    return _is_public_target(url) if parsed.scheme in ("http", "https") else True


def _is_pagination_candidate(url: str, label: str = "", rel: str = "") -> bool:
    """Recognise common path, query-string, rel=next and labelled pagination links."""
    import re
    from urllib.parse import parse_qs

    parsed = urlparse(url)
    query_keys = {key.lower() for key in parse_qs(parsed.query).keys()}
    pagination_keys = {"page", "p", "pageno", "pagenum", "page_number", "offset", "start"}
    if query_keys & pagination_keys:
        return True
    if re.search(r"/page/\d+(?:/|$)", parsed.path, re.I):
        return True
    return rel.strip().lower() == "next" or bool(
        re.search(r"\b(next|next page|older products)\b", label, re.I)
    )


def _normalise_discovery_url(href: str, base_url: str) -> Optional[str]:
    from urllib.parse import urljoin, urldefrag, urlparse
    if not href:
        return None
    candidate = urldefrag(urljoin(base_url, href.strip()))[0]
    parsed = urlparse(candidate)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return None
    if parsed.hostname.lower() != urlparse(base_url).hostname.lower():
        return None
    if any(token in candidate.lower() for token in ("javascript:", "mailto:", "tel:")):
        return None
    return candidate


@router.post("/discover")
async def discover_website(payload: Dict[str, Any]):
    """
    Render a public storefront with Playwright and return a bounded discovery
    report: platform hints, navigation categories, sitemap locations and
    candidate product/listing URLs. This is an analysis preview, not a crawl.
    """
    url = payload.get("url")
    if not isinstance(url, str) or not _is_public_target(url):
        raise HTTPException(status_code=400, detail="Provide a valid public HTTP or HTTPS website URL.")

    from playwright.async_api import async_playwright
    from urllib.parse import urljoin, urlparse
    from xml.etree import ElementTree
    import re

    browser = None
    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={"width": 1440, "height": 1000},
                locale="en-GB",
                ignore_https_errors=False,
            )

            async def guard_discovery_request(route):
                request_url = route.request.url
                if not _is_safe_network_request(request_url):
                    logger.warning("Blocked non-public discovery request: %s", request_url)
                    await route.abort("blockedbyclient")
                    return
                await route.continue_()

            # Validate browser subrequests and redirects, not only the first URL.
            await context.route("**/*", guard_discovery_request)
            page = await context.new_page()
            page.set_default_navigation_timeout(_DISCOVERY_TIMEOUT_MS)
            response = await page.goto(url, wait_until="domcontentloaded")
            await page.wait_for_timeout(1200)

            final_url = page.url
            if not _is_public_target(final_url):
                raise HTTPException(status_code=400, detail="The website redirected to a non-public address.")

            page_data = await page.evaluate("""() => {
              const text = (el) => (el?.innerText || el?.textContent || '').trim().replace(/\s+/g, ' ');
              const anchors = Array.from(document.querySelectorAll('a[href]')).slice(0, 500).map(a => ({
                href: a.getAttribute('href'),
                label: text(a).slice(0, 180),
                aria: (a.getAttribute('aria-label') || '').slice(0, 180)
              }));
              const jsonLd = Array.from(document.querySelectorAll('script[type="application/ld+json"]'))
                .map(s => s.textContent || '').join(' ').slice(0, 12000);
              const productNodes = Array.from(document.querySelectorAll(
                '[itemtype*="Product"], [data-product-id], [data-testid*="product"], .product, .product-item, .product-card, li.product'
              )).slice(0, 30);
              return {
                title: document.title || '',
                description: document.querySelector('meta[name="description"]')?.content || '',
                canonical: document.querySelector('link[rel="canonical"]')?.href || location.href,
                links: anchors,
                jsonLd,
                productNodeCount: productNodes.length,
                headings: Array.from(document.querySelectorAll('h1,h2')).slice(0, 30).map(text),
                platformSignals: {
                  shopify: /cdn\.shopify\.com|Shopify\.theme|shopify-section/i.test(document.documentElement.innerHTML),
                  woocommerce: /woocommerce|wc-block/i.test(document.documentElement.innerHTML),
                  magento: /Magento_|mage\\//i.test(document.documentElement.innerHTML),
                  bigcommerce: /bigcommerce|stencil-utils/i.test(document.documentElement.innerHTML),
                  prestashop: /prestashop/i.test(document.documentElement.innerHTML)
                }
              };
            }""")

            links = []
            seen = set()
            for item in page_data.get("links", []):
                candidate = _normalise_discovery_url(item.get("href"), final_url)
                if not candidate or candidate in seen:
                    continue
                seen.add(candidate)
                links.append({**item, "url": candidate})

            category_items = []
            product_candidates = []
            category_pattern = re.compile(r"/(category|categories|collection|collections|department|departments|c)/", re.I)
            product_pattern = re.compile(r"/(product|products|p|item|dp)/", re.I)
            excluded = re.compile(r"/(account|login|cart|checkout|search|blog|news|contact|about)(/|$)", re.I)
            for item in links:
                parsed_path = urlparse(item["url"]).path
                label = item.get("label") or item.get("aria") or parsed_path.rstrip("/").split("/")[-1].replace("-", " ").replace("_", " ").title()
                if excluded.search(parsed_path):
                    continue
                if category_pattern.search(parsed_path) or any(word in label.lower() for word in ("shop all", "all products", "accessories", "clothing", "bikes", "bicycles", "components")):
                    category_items.append({
                        "name": label[:120],
                        "url": item["url"],
                        "depth": max(1, len([part for part in parsed_path.split("/") if part])),
                    })
                elif product_pattern.search(parsed_path):
                    product_candidates.append(item["url"])

            sitemap_urls = []
            sitemap_status = "not_found"
            sitemap_candidates = [urljoin(final_url, "/robots.txt"), urljoin(final_url, "/sitemap.xml")]
            for sitemap_url in sitemap_candidates:
                try:
                    if not _is_public_target(sitemap_url):
                        continue
                    sitemap_response = await context.request.get(sitemap_url, timeout=7000)
                    if not sitemap_response.ok:
                        continue
                    body = await sitemap_response.text()
                    if sitemap_url.endswith("robots.txt"):
                        sitemap_locations = re.findall(r"(?im)^sitemap:\s*(https?://\S+)", body)
                        sitemap_candidates.extend(sitemap_locations[:5])
                        continue
                    root = ElementTree.fromstring(body[:2_000_000])
                    locs = [node.text.strip() for node in root.iter() if node.tag.lower().endswith("}loc") and node.text]
                    sitemap_urls.extend(locs[:200])
                    sitemap_status = "found"
                except Exception:
                    continue

            # Sitemap URL patterns often expose category and product routes.
            for sitemap_url in sitemap_urls:
                if urlparse(sitemap_url).hostname != urlparse(final_url).hostname:
                    continue
                path = urlparse(sitemap_url).path
                if category_pattern.search(path) and len(category_items) < _DISCOVERY_MAX_CATEGORIES:
                    category_items.append({
                        "name": path.rstrip("/").split("/")[-1].replace("-", " ").title(),
                        "url": sitemap_url,
                        "depth": max(1, len([part for part in path.split("/") if part])),
                        "source": "sitemap",
                    })
                elif product_pattern.search(path):
                    product_candidates.append(sitemap_url)

            # Crawl category/listing pages recursively. Keep this analysis bounded;
            # the full scrape job uses its own page/product limits.
            category_pattern = re.compile(r"/(category|categories|collection|collections|department|departments|c|catalog)/", re.I)
            product_pattern = re.compile(r"/(product|products|p|item|dp)/", re.I)
            excluded_pattern = re.compile(r"/(account|login|cart|checkout|search|blog|news|contact|about)(/|$)", re.I)
            category_by_url = {}
            category_queue = []
            for item in category_items:
                candidate = item["url"]
                if candidate not in category_by_url:
                    node = {
                        "name": item["name"],
                        "url": candidate,
                        "depth": 1,
                        "parent_url": None,
                        "children": [],
                        "source": item.get("source", "navigation"),
                    }
                    category_by_url[candidate] = node
                    category_queue.append((candidate, 1, None))

            crawled_category_pages = set()
            listing_pages = set()
            pagination_pages = 0
            recursive_product_urls = set(product_candidates)
            max_category_depth = 3
            max_listing_pages_per_category = 4
            crawl_page = await context.new_page()
            try:
                while category_queue and len(crawled_category_pages) < _DISCOVERY_MAX_CATEGORIES:
                    category_url, depth, parent_url = category_queue.pop(0)
                    if category_url in crawled_category_pages or depth > max_category_depth:
                        continue
                    crawled_category_pages.add(category_url)
                    try:
                        category_response = await crawl_page.goto(category_url, wait_until="domcontentloaded", timeout=_DISCOVERY_TIMEOUT_MS)
                        if not category_response or category_response.status >= 400:
                            continue
                        await crawl_page.wait_for_timeout(350)
                        page_links = await crawl_page.locator("a[href]").evaluate_all(
                            "(els) => els.slice(0, 600).map(a => ({href:a.getAttribute('href'), label:(a.innerText || '').trim().replace(/\s+/g,' ').slice(0,180), aria:(a.getAttribute('aria-label') || '').slice(0,180), rel:a.getAttribute('rel') || ''}))"
                        )
                        next_page_urls = []
                        for link in page_links:
                            candidate = _normalise_discovery_url(link.get("href"), category_url)
                            if not candidate or excluded_pattern.search(urlparse(candidate).path):
                                continue
                            path = urlparse(candidate).path
                            label = link.get("label") or path.rstrip("/").split("/")[-1].replace("-", " ").title()
                            if product_pattern.search(path):
                                recursive_product_urls.add(candidate)
                            elif category_pattern.search(path) and candidate not in category_by_url:
                                child = {
                                    "name": label[:120],
                                    "url": candidate,
                                    "depth": depth + 1,
                                    "parent_url": category_url,
                                    "children": [],
                                    "source": "category_page",
                                }
                                category_by_url[candidate] = child
                                category_queue.append((candidate, depth + 1, category_url))
                            elif _is_pagination_candidate(
                                candidate,
                                link.get("label") or link.get("aria") or label,
                                link.get("rel") or "",
                            ):
                                next_page_urls.append(candidate)

                        # Product cards can use opaque URLs without /product/ in their path.
                        card_links = await crawl_page.locator(
                            "article a[href], [class*='product'] a[href], [data-testid*='product'] a[href], [itemtype*='Product'] a[href]"
                        ).evaluate_all("(els) => els.slice(0, 300).map(a => a.href)")
                        for href in card_links:
                            candidate = _normalise_discovery_url(href, category_url)
                            if candidate and candidate != category_url:
                                recursive_product_urls.add(candidate)

                        # Follow a small number of listing pagination links, not arbitrary site links.
                        for next_url in list(dict.fromkeys(next_page_urls))[:max_listing_pages_per_category - 1]:
                            if next_url in listing_pages:
                                continue
                            try:
                                next_response = await crawl_page.goto(next_url, wait_until="domcontentloaded", timeout=_DISCOVERY_TIMEOUT_MS)
                                if not next_response or next_response.status >= 400:
                                    continue
                                listing_pages.add(next_url)
                                pagination_pages += 1
                                page_product_links = await crawl_page.locator(
                                    "a[href*='/product/'], a[href*='/products/'], article a[href], [class*='product'] a[href], [data-testid*='product'] a[href]"
                                ).evaluate_all("(els) => els.slice(0, 300).map(a => a.href)")
                                for href in page_product_links:
                                    candidate = _normalise_discovery_url(href, next_url)
                                    if candidate and candidate != next_url:
                                        recursive_product_urls.add(candidate)
                            except Exception as pagination_error:
                                logger.debug("Pagination discovery failed for %s: %s", next_url, pagination_error)
                    except Exception as category_error:
                        logger.debug("Category discovery failed for %s: %s", category_url, category_error)
            finally:
                await crawl_page.close()

            # Build an explicit tree while retaining a flat list for existing clients.
            category_tree = []
            for node in category_by_url.values():
                if node["parent_url"] and node["parent_url"] in category_by_url:
                    category_by_url[node["parent_url"]]["children"].append(node)
                else:
                    category_tree.append(node)

            unique_categories = list(category_by_url.values())[:_DISCOVERY_MAX_CATEGORIES]
            unique_products = list(dict.fromkeys(
                candidate for candidate in recursive_product_urls
                if urlparse(candidate).hostname == urlparse(final_url).hostname
            ))[:500]
            detector = PatternDetector()
            domain_detection = detector.detect_by_domain(final_url)
            platform_signals = page_data.get("platformSignals", {})
            detected_platform = domain_detection.get("platform") or next(
                (name for name, found in platform_signals.items() if found), "unknown"
            )

            return {
                "success": True,
                "requested_url": url,
                "final_url": final_url,
                "http_status": response.status if response else None,
                "title": page_data.get("title", ""),
                "description": page_data.get("description", ""),
                "platform": detected_platform,
                "platform_signals": platform_signals,
                "discovery": {
                    "categories": unique_categories,
                    "category_tree": category_tree,
                    "category_count": len(unique_categories),
                    "category_pages_crawled": len(crawled_category_pages),
                    "listing_pages_crawled": len(listing_pages),
                    "pagination_pages_crawled": pagination_pages,
                    "product_urls": unique_products,
                    "product_url_samples": unique_products[:30],
                    "product_url_count_estimate": len(unique_products),
                    "product_dom_nodes_on_landing_page": page_data.get("productNodeCount", 0),
                    "sitemap_status": sitemap_status,
                    "sitemap_url_count": len(sitemap_urls),
                    "headings": page_data.get("headings", []),
                    "truncated": len(links) >= _DISCOVERY_MAX_LINKS,
                },
                "limitations": [
                    "Counts are discovery samples, not a guaranteed total catalogue size.",
                    "Category hierarchy is inferred from same-domain navigation links and bounded recursive category-page crawling.",
                    "Discovery crawls at most 100 category pages, depth 3, and 4 listing pages per category; this is not a complete catalogue guarantee.",
                    "Some stores expose categories or products only after interaction or authentication.",
                ],
            }
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Website discovery failed for %s", url)
        raise HTTPException(status_code=502, detail=f"Website analysis failed: {str(exc)[:300]}")
    finally:
        if browser:
            await browser.close()


@router.post("/preview", response_model=DetectedSelectors)
# async def preview_scraping(request: ScraperPreviewRequest):
#     """
#     Preview scraping for a URL.
    
#     This endpoint analyzes the given URL and returns:
#     - Detected selectors for product extraction
#     - Sample products extracted with those selectors
#     - Platform detection (Shopify, WooCommerce, etc.)
#     """
#     try:
#         detector = PatternDetector()
#         result = await detector.analyze_page(str(request.url))
        
#         return DetectedSelectors(
#             confidence=result.get("confidence", 0.0),
#             platform=result.get("platform"),
#             selectors=result.get("selectors", {}),
#             sample_products=result.get("sample_products", [])
#         )
        
#     except Exception as e:
#         raise HTTPException(
#             status_code=500,
#             detail=f"Failed to analyze URL: {str(e)}"
#         )

def _to_selector_config(selectors: dict) -> "SelectorConfig":
    """Convert a plain dict of selectors to a SelectorConfig pydantic model."""
    return SelectorConfig(
        product_card=selectors.get("product_card"),
        product_link=selectors.get("product_link"),
        product_name=selectors.get("product_name"),
        product_price=selectors.get("product_price"),
        product_image=selectors.get("product_image"),
    )


@router.post("/preview", response_model=DetectedSelectors)
async def preview_scraping(request: ScraperPreviewRequest):
    """
    Analyze a URL to detect platform and selectors.
    Uses domain-based detection first (fast, works even when JS sites block simple requests),
    then optionally fetches the page for HTML-based refinement.
    """
    url_str = str(request.url)
    detector = PatternDetector()

    # 1. Try domain-based detection first (instant, no network needed)
    domain_result = detector.detect_by_domain(url_str)

    if domain_result["confidence"] >= 0.7:
        # High confidence match from domain alone — no need to fetch page
        return DetectedSelectors(
            confidence=domain_result["confidence"],
            platform=domain_result["platform"],
            selectors=_to_selector_config(domain_result["selectors"]),
            sample_products=[]
        )

    # 2. Try fetching the page HTML for unknown platforms (short timeout)
    try:
        import httpx
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-GB,en;q=0.9",
        }
        async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
            response = await client.get(url_str, headers=headers)
            html = response.text

        result = await detector.analyze_page(html, url_str)
        return DetectedSelectors(
            confidence=result.get("confidence", 0.0),
            platform=result.get("platform"),
            selectors=_to_selector_config(result.get("selectors", {})),
            sample_products=result.get("sample_products", [])
        )

    except Exception:
        # Page fetch failed (JS-rendered site, bot block, timeout, etc.)
        # Return best-effort generic selectors so user can still start a job
        generic = detector.get_generic_selectors()
        return DetectedSelectors(
            confidence=0.3,
            platform="Unknown (JavaScript-rendered site)",
            selectors=_to_selector_config(generic),
            sample_products=[]
        )

@router.post("/detect-platform")
async def detect_platform(url: str):
    """
    Detect the e-commerce platform of a website.
    
    Returns the detected platform (Shopify, WooCommerce, Magento, etc.)
    and any platform-specific configuration.
    """
    try:
        detector = PatternDetector()
        result = await detector.detect_platform(url)
        
        return {
            "success": True,
            "url": url,
            "platform": result.get("platform", "unknown"),
            "confidence": result.get("confidence", 0.0),
            "indicators": result.get("indicators", [])
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to detect platform: {str(e)}"
        )


@router.get("/visual-picker/render")
async def render_for_visual_picker(url: str):
    """
    Render a target website inside the visual selector picker sandbox,
    with asset rewriting, frame-buster neutralization, and interactive inspector script injected.
    """
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")
    html_content = await visual_picker_service.render_page_for_picker(url)
    return HTMLResponse(content=html_content)


@router.post("/visual-picker/test")
async def test_visual_selectors(payload: Dict[str, Any]):
    """
    Test custom CSS selectors on a live page and return element counts,
    matching text samples, and real-time product preview items.
    """
    url = payload.get("url")
    selectors = payload.get("selectors", {})
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")
    result = await visual_picker_service.test_custom_selectors(url, selectors)
    return result


@router.post("/test-selectors")
async def test_selectors(
    url: str,
    selectors: dict
):
    """
    Test custom selectors on a page.
    """
    try:
        result = await visual_picker_service.test_custom_selectors(url, selectors)
        return {
            "success": result.get("success", True),
            "url": url,
            "matched_elements": result.get("matched_elements", {}),
            "sample_data": result.get("preview_products", [])
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to test selectors: {str(e)}"
        )


async def _resolve_gemini_key(db: AsyncSession, explicit_key: Optional[str] = None) -> Optional[str]:
    """Resolve Gemini API key from request, environment settings, or saved integrations."""
    if explicit_key and explicit_key.strip():
        return explicit_key.strip()
    from app.config import settings
    if getattr(settings, "GEMINI_API_KEY", None):
        return settings.GEMINI_API_KEY
    try:
        from sqlalchemy import select
        from app.models.integration import IntegrationConfig
        q = select(IntegrationConfig).where(IntegrationConfig.platform.in_(["gemini", "google_gemini"]))
        res = await db.execute(q)
        cfg = res.scalar_one_or_none()
        if cfg and cfg.credentials:
            cd = json.loads(cfg.credentials)
            return cd.get("api_key")
    except Exception:
        pass
    return None


@router.post("/ai-extract")
async def ai_extract_products(payload: Dict[str, Any], db: AsyncSession = Depends(get_db)):
    """
    Extract products using Google Gemini zero-shot AI extraction.
    Accepts URL (and optional HTML / API key override).
    """
    url = payload.get("url")
    html = payload.get("html")
    api_key = payload.get("api_key")
    model = payload.get("model")

    if not url:
        raise HTTPException(status_code=400, detail="URL is required")

    effective_key = await _resolve_gemini_key(db, api_key)

    if not html:
        import httpx
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9",
            }
            async with httpx.AsyncClient(timeout=20.0, follow_redirects=True, verify=False) as client:
                resp = await client.get(url, headers=headers)
                html = resp.text
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to fetch {url}: {str(e)}")

    result = await ai_extractor_service.extract_products_with_ai(
        html=html,
        base_url=url,
        api_key=effective_key,
        model=model
    )
    return result


@router.post("/ai-suggest-selectors")
async def ai_suggest_selectors(payload: Dict[str, Any], db: AsyncSession = Depends(get_db)):
    """
    Reverse-engineer optimal CSS selectors using Gemini LLM analysis.
    """
    url = payload.get("url")
    html = payload.get("html")
    api_key = payload.get("api_key")

    if not url:
        raise HTTPException(status_code=400, detail="URL is required")

    effective_key = await _resolve_gemini_key(db, api_key)

    if not html:
        import httpx
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9",
            }
            async with httpx.AsyncClient(timeout=20.0, follow_redirects=True, verify=False) as client:
                resp = await client.get(url, headers=headers)
                html = resp.text
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to fetch {url}: {str(e)}")

    result = await ai_extractor_service.suggest_selectors_with_ai(
        html=html,
        base_url=url,
        api_key=effective_key
    )
    return result


@router.get("/presets")
async def list_selector_presets(
    domain: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """List saved selector recipes / presets."""
    from sqlalchemy import select
    query = select(SelectorPreset).order_by(SelectorPreset.id.desc())
    if domain:
        query = query.where(SelectorPreset.domain.ilike(f"%{domain}%"))
    res = await db.execute(query)
    presets = res.scalars().all()

    return [
        {
            "id": p.id,
            "name": p.name,
            "domain": p.domain,
            "description": p.description,
            "selectors": json.loads(p.selectors) if p.selectors else {},
            "created_at": p.created_at,
        }
        for p in presets
    ]


@router.post("/presets")
async def save_selector_preset(
    payload: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    """Save a custom selector recipe."""
    name = payload.get("name")
    domain = payload.get("domain")
    description = payload.get("description", "")
    selectors = payload.get("selectors", {})
    if not name or not selectors:
        raise HTTPException(status_code=400, detail="Name and selectors are required")

    preset = SelectorPreset(
        name=name,
        domain=domain,
        description=description,
        selectors=json.dumps(selectors),
    )
    db.add(preset)
    await db.commit()
    await db.refresh(preset)

    return {
        "id": preset.id,
        "name": preset.name,
        "domain": preset.domain,
        "description": preset.description,
        "selectors": selectors,
        "created_at": preset.created_at,
    }


@router.delete("/presets/{preset_id}")
async def delete_selector_preset(
    preset_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete a saved selector recipe."""
    preset = await db.get(SelectorPreset, preset_id)
    if not preset:
        raise HTTPException(status_code=404, detail="Preset not found")
    await db.delete(preset)
    await db.commit()
    return {"success": True, "message": "Preset deleted"}


@router.get("/supported-platforms")
async def get_supported_platforms():
    """
    Get list of supported e-commerce platforms.
    """
    return {
        "platforms": [
            {
                "id": "shopify",
                "name": "Shopify",
                "description": "Shopify-based stores (Liquid themes, native JSON endpoints)",
                "auto_detect": True
            },
            {
                "id": "woocommerce",
                "name": "WooCommerce",
                "description": "WordPress WooCommerce stores (StoreAPI, WC product markup)",
                "auto_detect": True
            },
            {
                "id": "bigcommerce",
                "name": "BigCommerce",
                "description": "BigCommerce stores (Stencil themes, GraphQL)",
                "auto_detect": True
            },
            {
                "id": "magento",
                "name": "Magento",
                "description": "Magento 2 / Adobe Commerce / Hyvä stores",
                "auto_detect": True
            },
            {
                "id": "squarespace",
                "name": "Squarespace",
                "description": "Squarespace Commerce (?format=json, grid-item)",
                "auto_detect": True
            },
            {
                "id": "wix",
                "name": "Wix",
                "description": "Wix Stores (data-hook selectors, warmup data)",
                "auto_detect": True
            },
            {
                "id": "etsy",
                "name": "Etsy",
                "description": "Etsy Marketplace listings and shops",
                "auto_detect": True
            },
            {
                "id": "walmart",
                "name": "Walmart",
                "description": "Walmart Marketplace search and categories",
                "auto_detect": True
            },
            {
                "id": "amazon",
                "name": "Amazon",
                "description": "Amazon Marketplace product search and ASINs",
                "auto_detect": True
            },
            {
                "id": "ebay",
                "name": "eBay",
                "description": "eBay Marketplace listings, cards, and auctions",
                "auto_detect": True
            },
            {
                "id": "generic",
                "name": "Generic",
                "description": "Any e-commerce website (heuristic & AI detection)",
                "auto_detect": True
            }
        ]
    }


@router.post("/sitemap/parse")
async def parse_sitemap(payload: Dict[str, Any]):
    """
    Parse a remote or local sitemap URL (including sitemap indexes and .gz files).
    Discovers all product URLs up to depth limit.
    """
    sitemap_url = payload.get("sitemap_url")
    filter_products = bool(payload.get("filter_products_only", False))
    if not sitemap_url:
        raise HTTPException(status_code=400, detail="sitemap_url is required")

    from app.core.sitemap_parser import sitemap_parser
    result = await sitemap_parser.fetch_and_parse(
        sitemap_url=sitemap_url,
        filter_products_only=filter_products
    )
    return result


@router.post("/bulk/parse-file")
async def parse_bulk_file(payload: Dict[str, Any]):
    """
    Parse uploaded CSV, TSV, or raw text file content.
    Automatically sniffs delimiters, header rows, and extracts all valid URLs.
    """
    file_content = payload.get("content", "")
    file_name = payload.get("file_name", "").lower()

    if not file_content:
        raise HTTPException(status_code=400, detail="file content is required")

    from app.services.bulk_importer_service import bulk_importer_service
    if file_name.endswith(".csv") or file_name.endswith(".tsv") or "," in file_content or "\t" in file_content:
        result = bulk_importer_service.parse_csv_or_tsv(file_content)
    else:
        result = bulk_importer_service.parse_raw_text(file_content)

    return result


@router.post("/bulk/start")
async def start_bulk_scraping(
    payload: Dict[str, Any],
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    """
    Start a high-throughput parallel bulk crawl across a list of URLs (from CSV or sitemap).
    Spawns concurrent worker pool up to 10,000+ items.
    """
    urls = payload.get("urls", [])
    if not urls or not isinstance(urls, list):
        raise HTTPException(status_code=400, detail="A non-empty list of 'urls' is required")

    # Clean & validate
    valid_urls = [str(u).strip() for u in urls if str(u).strip().startswith("http")]
    if not valid_urls:
        raise HTTPException(status_code=400, detail="No valid HTTP/HTTPS URLs provided")

    name = payload.get("name") or f"Bulk Import ({len(valid_urls)} URLs)"
    concurrency = int(payload.get("concurrency", 10))
    request_delay = float(payload.get("request_delay", 0.5))
    custom_selectors = payload.get("selectors")

    # Parse primary domain from first URL
    first_parsed = urlparse(valid_urls[0])
    domain = first_parsed.netloc or "bulk-import"

    job_id = f"job_bulk_{uuid.uuid4().hex[:10]}"
    job = Job(
        job_id=job_id,
        name=name,
        description=f"Parallel bulk crawl across {len(valid_urls)} URLs (concurrency: {concurrency})",
        url=valid_urls[0],
        domain=domain,
        job_type=JobType.PRODUCT_LIST,
        status=JobStatus.PENDING,
        user_id=current_user.id if current_user else 1,
        total_pages=len(valid_urls),
        config={
            "is_bulk": True,
            "urls_count": len(valid_urls),
            "concurrency": concurrency,
            "request_delay": request_delay,
            "selectors": custom_selectors,
        }
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Launch bulk scraping in background
    background_tasks.add_task(
        run_bulk_scraper_job,
        job.id,
        valid_urls,
        concurrency,
        request_delay,
        custom_selectors
    )

    return {
        "success": True,
        "message": f"Bulk scraping job started for {len(valid_urls)} URLs",
        "job_id": job_id,
        "total_urls": len(valid_urls),
        "status": "pending",
    }



async def run_scraper_job(job_id: int, url: str, config: Optional[ScraperConfig]):
    """Background task to run the scraper using httpx + BeautifulSoup."""
    from datetime import datetime, timezone
    from sqlalchemy import select
    from app.models.database import get_db_context
    from app.models.product import Product, PriceHistory
    from app.core.httpx_scraper import HttpxScraper

    async with get_db_context() as db:
        job = await db.get(Job, job_id)
        if not job:
            return

        job.status = JobStatus.RUNNING
        job.started_at = datetime.now(timezone.utc)
        job.logs = []
        await db.commit()

        async def write_log(message: str, level: str = "info"):
            """Append log entry to the job record in DB."""
            try:
                async with get_db_context() as log_db:
                    j = await log_db.get(Job, job_id)
                    if j:
                        current_logs = list(j.logs or [])
                        current_logs.append({
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "level": level,
                            "message": message,
                        })
                        j.logs = current_logs
                        await log_db.commit()
            except Exception as e:
                logger.error(f"write_log error: {e}")

        async def save_products(products_data: list):
            """Save a batch of scraped products to DB, tracking price changes and history."""
            try:
                async with get_db_context() as save_db:
                    j = await save_db.get(Job, job_id)
                    if not j:
                        return
                    domain = urlparse(url).netloc
                    saved = 0
                    for data in products_data:
                        try:
                            p_url = data.get("url")
                            raw_price = data.get("price")
                            p_price = float(raw_price) if raw_price is not None else None
                            p_text = data.get("price_text")
                            p_curr = data.get("currency")

                            # Detect currency from raw price text if missing
                            from app.services.currency_service import currency_service
                            if not p_curr or p_curr == "USD":
                                p_curr = currency_service.detect_currency(p_text, default=p_curr or "USD")

                            # Normalize price to target currency
                            p_norm_price, p_rate = None, None
                            p_target_curr = getattr(settings, "TARGET_CURRENCY", "USD")
                            if p_price is not None and getattr(settings, "CURRENCY_AUTO_NORMALIZE", True):
                                p_norm_price, p_rate = await currency_service.convert_price(
                                    amount=p_price,
                                    from_currency=p_curr,
                                    to_currency=p_target_curr
                                )

                            # Check for existing product by URL
                            existing_p = None
                            if p_url:
                                stmt = select(Product).where(Product.url == p_url).limit(1)
                                res = await save_db.execute(stmt)
                                existing_p = res.scalar_one_or_none()

                            if existing_p:
                                # Product exists: calculate price changes & record history snapshot
                                old_price = float(existing_p.price) if existing_p.price is not None else None
                                if p_price is not None:
                                    if old_price is not None and old_price != p_price:
                                        existing_p.previous_price = existing_p.price
                                        change = round(p_price - old_price, 2)
                                        existing_p.price_change = change
                                        if old_price > 0:
                                            existing_p.price_change_percentage = round((change / old_price) * 100, 2)

                                        # Trigger real-time price drop notification (Telegram / Slack / Discord / Webhook)
                                        if p_price < old_price:
                                            try:
                                                from app.services.alert_service import alert_service
                                                await alert_service.process_price_change(
                                                    db=save_db,
                                                    product_id=existing_p.id,
                                                    product_name=existing_p.name,
                                                    product_url=existing_p.url,
                                                    old_price=old_price,
                                                    new_price=p_price,
                                                    currency=p_curr,
                                                    image_url=existing_p.image_url,
                                                )
                                            except Exception as alert_err:
                                                logger.error(f"Error triggering price drop alert: {alert_err}")

                                        # Trigger automated competitor repricing (Shopify / WooCommerce / Webhook)
                                        try:
                                            from app.services.repricing_service import repricing_service
                                            await repricing_service.evaluate_and_reprice_product(
                                                db=save_db,
                                                product=existing_p,
                                                competitor_price=p_price,
                                                competitor_domain=domain,
                                            )
                                        except Exception as reprice_err:
                                            logger.debug(f"Repricing rule evaluation error: {reprice_err}")
                                    
                                    existing_p.price = p_price
                                    existing_p.lowest_price = min(float(existing_p.lowest_price or p_price), p_price)
                                    existing_p.highest_price = max(float(existing_p.highest_price or p_price), p_price)

                                if p_text:
                                    existing_p.price_text = p_text
                                for field in ("name", "description", "sku", "brand", "category", "subcategory", "category_path"):
                                    value = data.get(field)
                                    if value:
                                        setattr(existing_p, field, value[:500] if field == "name" else value)
                                if data.get("image_url"):
                                    existing_p.image_url = data.get("image_url")
                                availability = str(data.get("availability") or "").lower()
                                if availability:
                                    existing_p.in_stock = not any(token in availability for token in ("outofstock", "soldout", "out of stock", "unavailable"))
                                    existing_p.stock_status = availability
                                if data.get("stock_quantity") is not None:
                                    existing_p.stock_quantity = data.get("stock_quantity")
                                existing_p.raw_data = {**(existing_p.raw_data or {}), **data}
                                existing_p.currency = p_curr
                                existing_p.normalized_price = p_norm_price
                                existing_p.normalized_currency = p_target_curr
                                existing_p.exchange_rate = p_rate
                                existing_p.job_id = job_id
                                existing_p.scraped_at = datetime.now(timezone.utc)

                                if p_price is not None:
                                    ph = PriceHistory(
                                        product_id=existing_p.id,
                                        job_id=job_id,
                                        price=p_price,
                                        price_text=p_text,
                                        currency=p_curr,
                                    )
                                    save_db.add(ph)
                                saved += 1
                            else:
                                # New product: insert and create initial price history
                                p = Product(
                                    job_id=job_id,
                                    name=data.get("name", "Unknown")[:500],
                                    sku=data.get("sku"),
                                    brand=data.get("brand"),
                                    url=p_url or f"{url}#{saved}",
                                    price=p_price,
                                    previous_price=None,
                                    price_change=0,
                                    price_change_percentage=0,
                                    lowest_price=p_price,
                                    highest_price=p_price,
                                    price_text=p_text,
                                    currency=p_curr,
                                    normalized_price=p_norm_price,
                                    normalized_currency=p_target_curr,
                                    exchange_rate=p_rate,
                                    image_url=data.get("image_url"),
                                    description=data.get("description"),
                                    title=data.get("title"),
                                    category=data.get("category"),
                                    subcategory=data.get("subcategory"),
                                    category_path=data.get("category_path"),
                                    in_stock=not any(token in str(data.get("availability") or "").lower() for token in ("outofstock", "soldout", "out of stock", "unavailable")),
                                    stock_quantity=data.get("stock_quantity"),
                                    stock_status=data.get("availability"),
                                    raw_data=data,
                                    source_domain=domain,
                                )

                                # Optional Cloudinary CDN auto-upload
                                if settings.CLOUDINARY_AUTO_UPLOAD and p.image_url:
                                    try:
                                        from app.services.cloudinary_service import cloudinary_service
                                        if cloudinary_service.is_configured():
                                            c_res = await cloudinary_service.upload_image_url(p.image_url)
                                            if c_res.get("success"):
                                                p.cloudinary_url = c_res.get("secure_url")
                                                p.cloudinary_public_id = c_res.get("public_id")
                                                if c_res.get("thumbnail_url"):
                                                    p.thumbnail_url = c_res.get("thumbnail_url")
                                    except Exception as c_err:
                                        logger.debug(f"Cloudinary auto-upload error: {c_err}")

                                # Optional AWS S3 Cloud Storage auto-upload
                                if settings.AWS_S3_AUTO_UPLOAD and p.image_url:
                                    try:
                                        from app.services.s3_storage_service import s3_storage_service
                                        if s3_storage_service.is_configured():
                                            s3_res = await s3_storage_service.download_and_upload_image(p.image_url)
                                            if s3_res.get("success"):
                                                p.s3_url = s3_res.get("s3_url")
                                                p.s3_key = s3_res.get("s3_key")
                                    except Exception as s3_err:
                                        logger.debug(f"S3 auto-upload error: {s3_err}")

                                # Optional Supabase Free Cloud Storage auto-upload
                                if settings.SUPABASE_AUTO_UPLOAD and p.image_url:
                                    try:
                                        from app.services.supabase_storage_service import supabase_storage_service
                                        if supabase_storage_service.is_configured():
                                            supa_res = await supabase_storage_service.download_and_upload_image(p.image_url)
                                            if supa_res.get("success"):
                                                p.supabase_url = supa_res.get("supabase_url")
                                                p.supabase_path = supa_res.get("supabase_path")
                                    except Exception as supa_err:
                                        logger.debug(f"Supabase auto-upload error: {supa_err}")

                                save_db.add(p)
                                await save_db.flush()

                                # Cross-store competitor product matching & deduplication clustering
                                try:
                                    from app.services.product_matching_service import product_matching_service
                                    await product_matching_service.find_or_assign_cluster_for_product(
                                        db=save_db,
                                        product=p,
                                        threshold=0.75,
                                        allow_ai=False
                                    )
                                except Exception as match_err:
                                    logger.debug(f"Product matching clustering error: {match_err}")

                                if p_price is not None:
                                    ph = PriceHistory(
                                        product_id=p.id,
                                        job_id=job_id,
                                        price=p_price,
                                        price_text=p_text,
                                        currency=p_curr,
                                    )
                                    save_db.add(ph)

                                # Save variants for new product
                                raw_variants = data.get("variants") or []
                                if raw_variants:
                                    from app.models.product import ProductVariant
                                    for v_item in raw_variants:
                                        if isinstance(v_item, dict) and (v_item.get("name") or v_item.get("title")):
                                            v_name = v_item.get("name") or v_item.get("title")
                                            v_price = v_item.get("price")
                                            v_orig = v_item.get("original_price") or v_item.get("compare_at_price")
                                            variant_record = ProductVariant(
                                                product_id=p.id,
                                                variant_id=str(v_item.get("variant_id") or v_item.get("id") or ""),
                                                sku=v_item.get("sku"),
                                                name=v_name[:255],
                                                attributes=v_item.get("attributes") or {},
                                                price=float(v_price) if v_price is not None else None,
                                                original_price=float(v_orig) if v_orig is not None else None,
                                                in_stock=bool(v_item.get("in_stock", v_item.get("available", True))),
                                                stock_quantity=v_item.get("stock_quantity") or v_item.get("inventory_quantity"),
                                                image_url=v_item.get("image_url"),
                                            )
                                            save_db.add(variant_record)

                                saved += 1
                        except Exception as ex:
                            logger.error(f"Error saving individual product: {ex}")
                    if saved:
                        j.total_products = (j.total_products or 0) + saved
                        await save_db.commit()
                        logger.info(f"Successfully saved {saved} products for job {job_id}. Total: {j.total_products}")
            except Exception as e:
                logger.error(f"save_products error: {e}")

        async def on_page_done(page_url: str, success: bool, pages_count: int):
            """Update scraped_pages count."""
            try:
                async with get_db_context() as page_db:
                    j = await page_db.get(Job, job_id)
                    if j:
                        j.scraped_pages = pages_count
                        if not success:
                            j.failed_pages = (j.failed_pages or 0) + 1
                        await page_db.commit()
            except Exception as e:
                logger.error(f"on_page_done error: {e}")

        try:
            max_pages = config.max_pages if config else 100
            max_products = config.max_products if config else 10000
            max_depth = config.max_depth if config else 3
            request_delay = ((config.request_delay or 1000) / 1000.0) if config else 1.0
            
            # Rotating Proxy Pool initialization with automated failover
            from app.core.proxy_manager import build_proxy_pool
            from app.config import settings

            raw_proxies = None
            if config:
                raw_proxies = getattr(config, 'proxy', None)
                if not raw_proxies and getattr(config, 'custom_settings', None):
                    raw_proxies = config.custom_settings.get('proxy') or config.custom_settings.get('proxies')

            proxy_pool = build_proxy_pool(
                explicit_proxies=raw_proxies,
                failover_enabled=getattr(settings, "PROXY_FAILOVER_ENABLED", True),
                max_retries=getattr(settings, "PROXY_MAX_RETRIES", 3),
            )

            if proxy_pool.has_proxies:
                await write_log(
                    f"Initialized Rotating Proxy Pool ({proxy_pool.total_proxies} proxies | "
                    f"Auto-Failover on 403/429 blocks enabled)",
                    "info"
                )

            # Platform auto-detection
            from app.scrapers.scraper_registry import ScraperRegistry
            detection = ScraperRegistry.detect_platform_detailed(url, fetch_if_needed=False)
            detected_platform = detection.get("platform", "generic")
            confidence = int(detection.get("confidence", 0.0) * 100)
            method = detection.get("method", "domain")

            await write_log(f"Auto-detected platform: {detected_platform.upper()} ({confidence}% confidence via {method})", "info")

            use_pw = bool(config and getattr(config, 'javascript_rendering', False))
            domain_lower = url.lower()
            selected_category_urls = list(dict.fromkeys(getattr(config, "category_urls", None) or [])) if config else []
            if selected_category_urls:
                root_host = (urlparse(url).hostname or "").lower()
                for category_url in selected_category_urls:
                    parsed_category = urlparse(category_url)
                    if parsed_category.scheme not in ("http", "https") or (parsed_category.hostname or "").lower() != root_host:
                        raise ValueError("Selected category URLs must belong to the original website.")
                await write_log(f"Starting from {len(selected_category_urls)} selected category URLs.", "info")
            else:
                selected_category_urls = [url]
            if any(m in domain_lower for m in ("amazon.", "ebay.", "walmart.", "etsy.", "wix.")) or detected_platform in ("amazon", "ebay", "walmart", "etsy", "wix"):
                use_pw = True

            if use_pw:
                from app.core.playwright_scraper import PlaywrightScraper
                scraper = PlaywrightScraper(
                    job_id=job_id,
                    start_url=url,
                    start_urls=selected_category_urls,
                    max_pages=max_pages,
                    max_products=max_products,
                    max_depth=max_depth,
                    request_delay=request_delay,
                    proxy_pool=proxy_pool,
                    on_log=write_log,
                    on_product_batch=save_products,
                    on_page_done=on_page_done,
                )
            else:
                scraper = HttpxScraper(
                    job_id=job_id,
                    start_url=url,
                    start_urls=selected_category_urls,
                    max_pages=max_pages,
                    max_products=max_products,
                    max_depth=max_depth,
                    request_delay=request_delay,
                    proxy_pool=proxy_pool,
                    on_log=write_log,
                    on_product_batch=save_products,
                    on_page_done=on_page_done,
                )
            await scraper.run()

            j = await db.get(Job, job_id)
            if j:
                j.status = JobStatus.COMPLETED
                j.completed_at = datetime.now(timezone.utc)
                await db.commit()

        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            logger.error(f"Scraper job {job_id} failed: {e}\n{error_trace}")
            try:
                j = await db.get(Job, job_id)
                if j:
                    j.status = JobStatus.FAILED
                    j.error_message = str(e) or "Scraper failed unexpectedly"
                    j.error_trace = error_trace
                    j.completed_at = datetime.now(timezone.utc)
                    await db.commit()
            except Exception:
                pass


@router.get("/proxies/status")
async def get_proxy_pool_status():
    """
    Get live health metrics, rotation status, and active proxies in the pool.
    """
    from app.core.proxy_manager import build_proxy_pool
    pool = build_proxy_pool()
    return pool.get_status_summary()


@router.post("/proxies/test")
async def test_proxy_pool(payload: Optional[Dict[str, Any]] = None):
    """
    Test connectivity of custom proxies or the currently configured pool.
    Returns latency, HTTP status, and verified exit IP.
    """
    from app.core.proxy_manager import build_proxy_pool
    proxies = payload.get("proxies") if payload else None
    pool = build_proxy_pool(explicit_proxies=proxies)
    if not pool.has_proxies:
        return {
            "success": False,
            "message": "No proxies provided or configured.",
            "results": []
        }
    results = await pool.test_all()
    successful = [r for r in results if r.get("success")]
    return {
        "success": len(successful) > 0,
        "total": len(results),
        "active": len(successful),
        "results": results
    }


async def run_bulk_scraper_job(
    job_id: int,
    urls: List[str],
    concurrency: int = 10,
    request_delay: float = 0.5,
    custom_selectors: Optional[Dict[str, Any]] = None,
):
    """
    Background worker for bulk parallel scraping.
    Processes thousands of product URLs concurrently with progress updates and price drop alerting.
    """
    from datetime import datetime, timezone
    from sqlalchemy import select
    from app.models.database import get_db_context
    from app.models.product import Product, PriceHistory
    from app.core.bulk_batch_scraper import BulkBatchScraper
    from app.core.proxy_manager import build_proxy_pool
    from app.config import settings

    async with get_db_context() as db:
        job = await db.get(Job, job_id)
        if not job:
            return

        job.status = JobStatus.RUNNING
        job.started_at = datetime.now(timezone.utc)
        job.logs = []
        await db.commit()

        async def write_log(message: str, level: str = "info"):
            try:
                async with get_db_context() as log_db:
                    j = await log_db.get(Job, job_id)
                    if j:
                        current_logs = list(j.logs or [])
                        current_logs.append({
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "level": level,
                            "message": message,
                        })
                        j.logs = current_logs
                        await log_db.commit()
            except Exception as e:
                logger.error(f"write_log error: {e}")

        async def save_products(products_data: list):
            try:
                async with get_db_context() as save_db:
                    j = await save_db.get(Job, job_id)
                    if not j:
                        return
                    saved = 0
                    for data in products_data:
                        try:
                            p_url = data.get("url")
                            raw_price = data.get("price")
                            p_price = float(raw_price) if raw_price is not None else None
                            p_text = data.get("price_text")
                            p_curr = data.get("currency") or "USD"
                            domain = urlparse(p_url).netloc if p_url else j.domain

                            existing_p = None
                            if p_url:
                                stmt = select(Product).where(Product.url == p_url).limit(1)
                                res = await save_db.execute(stmt)
                                existing_p = res.scalar_one_or_none()

                            if existing_p:
                                old_price = float(existing_p.price) if existing_p.price is not None else None
                                if p_price is not None:
                                    if old_price is not None and old_price != p_price:
                                        existing_p.previous_price = existing_p.price
                                        change = round(p_price - old_price, 2)
                                        existing_p.price_change = change
                                        if old_price > 0:
                                            existing_p.price_change_percentage = round((change / old_price) * 100, 2)

                                        if p_price < old_price:
                                            try:
                                                from app.services.alert_service import alert_service
                                                await alert_service.process_price_change(
                                                    db=save_db,
                                                    product_id=existing_p.id,
                                                    product_name=existing_p.name,
                                                    product_url=existing_p.url,
                                                    old_price=old_price,
                                                    new_price=p_price,
                                                    currency=p_curr,
                                                    image_url=existing_p.image_url,
                                                )
                                            except Exception as alert_err:
                                                logger.error(f"Error in price drop alert: {alert_err}")

                                    existing_p.price = p_price
                                    if existing_p.lowest_price is None or p_price < float(existing_p.lowest_price):
                                        existing_p.lowest_price = p_price
                                    if existing_p.highest_price is None or p_price > float(existing_p.highest_price):
                                        existing_p.highest_price = p_price

                                if data.get("name"):
                                    existing_p.name = data["name"]
                                if data.get("image_url"):
                                    existing_p.image_url = data["image_url"]
                                existing_p.updated_at = datetime.now(timezone.utc)
                                saved += 1
                            else:
                                p = Product(
                                    job_id=job_id,
                                    name=data.get("name", "Product")[:500],
                                    sku=data.get("sku"),
                                    brand=data.get("brand"),
                                    price=p_price,
                                    currency=p_curr,
                                    price_text=p_text,
                                    lowest_price=p_price,
                                    highest_price=p_price,
                                    url=p_url,
                                    image_url=data.get("image_url"),
                                    source_domain=domain,
                                )
                                save_db.add(p)
                                await save_db.flush()

                                # Cross-store competitor product matching & deduplication clustering
                                try:
                                    from app.services.product_matching_service import product_matching_service
                                    await product_matching_service.find_or_assign_cluster_for_product(
                                        db=save_db,
                                        product=p,
                                        threshold=0.75,
                                        allow_ai=False
                                    )
                                except Exception as match_err:
                                    logger.debug(f"Bulk product matching clustering error: {match_err}")

                                if p_price is not None:
                                    ph = PriceHistory(
                                        product_id=p.id,
                                        job_id=job_id,
                                        price=p_price,
                                        price_text=p_text,
                                        currency=p_curr,
                                    )
                                    save_db.add(ph)
                                saved += 1
                        except Exception as ex:
                            logger.error(f"Error saving product: {ex}")

                    if saved:
                        j.total_products = (j.total_products or 0) + saved
                        await save_db.commit()
            except Exception as e:
                logger.error(f"save_products error in bulk job: {e}")

        async def update_progress(completed: int, total: int, successful: int):
            try:
                async with get_db_context() as prog_db:
                    j = await prog_db.get(Job, job_id)
                    if j:
                        j.scraped_pages = completed
                        j.failed_pages = completed - successful
                        j.progress = round((completed / max(1, total)) * 100, 1)
                        await prog_db.commit()
            except Exception as e:
                logger.error(f"update_progress error: {e}")

        try:
            proxy_pool = build_proxy_pool(
                failover_enabled=getattr(settings, "PROXY_FAILOVER_ENABLED", True),
                max_retries=getattr(settings, "PROXY_MAX_RETRIES", 3),
            )

            bulk_scraper = BulkBatchScraper(
                job_id=job_id,
                urls=urls,
                concurrency=concurrency,
                request_delay=request_delay,
                proxy_pool=proxy_pool,
                custom_selectors=custom_selectors,
                on_log=write_log,
                on_product_batch=save_products,
                on_progress=update_progress,
            )

            await bulk_scraper.run()

            j = await db.get(Job, job_id)
            if j:
                j.status = JobStatus.COMPLETED
                j.progress = 100.0
                j.completed_at = datetime.now(timezone.utc)
                await db.commit()

        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            logger.error(f"Bulk job {job_id} failed: {e}\n{error_trace}")
            try:
                j = await db.get(Job, job_id)
                if j:
                    j.status = JobStatus.FAILED
                    j.error_message = str(e) or "Bulk scraper failed unexpectedly"
                    j.error_trace = error_trace
                    j.completed_at = datetime.now(timezone.utc)
                    await db.commit()
            except Exception:
                pass