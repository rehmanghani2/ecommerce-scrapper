"""
Scraper API routes.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import uuid
from urllib.parse import urlparse

from app.models.database import get_db
from app.models.job import Job, JobStatus, JobType
from app.schemas.scraper_schema import (
    ScraperRequest, ScraperResponse, ScraperPreviewRequest,
    DetectedSelectors, ScraperConfig, SelectorConfig
)
from app.core.pattern_detector import PatternDetector


router = APIRouter()


@router.post("/start", response_model=ScraperResponse)
async def start_scraping(
    request: ScraperRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
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


# @router.post("/preview", response_model=DetectedSelectors)
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


@router.post("/test-selectors")
async def test_selectors(
    url: str,
    selectors: dict
):
    """
    Test custom selectors on a page.
    
    Use this to verify that your custom selectors work correctly
    before starting a full scraping job.
    """
    try:
        from app.core.product_extractor import ProductExtractor
        
        extractor = ProductExtractor()
        result = await extractor.test_selectors(url, selectors)
        
        return {
            "success": True,
            "url": url,
            "matched_elements": result.get("matched_elements", {}),
            "sample_data": result.get("sample_data", [])
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to test selectors: {str(e)}"
        )


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
                "description": "Shopify-based stores",
                "auto_detect": True
            },
            {
                "id": "woocommerce",
                "name": "WooCommerce",
                "description": "WordPress WooCommerce stores",
                "auto_detect": True
            },
            {
                "id": "magento",
                "name": "Magento",
                "description": "Magento/Adobe Commerce stores",
                "auto_detect": True
            },
            {
                "id": "generic",
                "name": "Generic",
                "description": "Any e-commerce website",
                "auto_detect": True
            }
        ]
    }


async def run_scraper_job(job_id: int, url: str, config: Optional[ScraperConfig]):
    """Background task to run the scraper using httpx + BeautifulSoup."""
    from datetime import datetime, timezone
    from app.models.database import get_db_context
    from app.models.product import Product
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
            """Save a batch of scraped products to DB."""
            try:
                async with get_db_context() as save_db:
                    j = await save_db.get(Job, job_id)
                    if not j:
                        return
                    domain = urlparse(url).netloc
                    saved = 0
                    for data in products_data:
                        try:
                            p = Product(
                                job_id=job_id,
                                name=data.get("name", "Unknown")[:500],
                                url=data.get("url"),
                                price=data.get("price"),
                                price_text=data.get("price_text"),
                                image_url=data.get("image_url"),
                                source_domain=domain,
                            )
                            save_db.add(p)
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
            
            # Proxy configuration support
            proxy_setting = None
            import os
            if config:
                raw_proxy = getattr(config, 'proxy', None)
                if not raw_proxy and getattr(config, 'custom_settings', None):
                    raw_proxy = config.custom_settings.get('proxy')
                if raw_proxy:
                    proxy_setting = raw_proxy

            if not proxy_setting:
                from app.config import settings
                proxy_setting = getattr(settings, "SCRAPER_PROXY", None) or os.environ.get("SCRAPER_PROXY")

            pw_proxy = None
            httpx_proxy = None
            if proxy_setting:
                if isinstance(proxy_setting, str):
                    httpx_proxy = proxy_setting
                    if "@" in proxy_setting:
                        scheme_part, rest = proxy_setting.split("://", 1) if "://" in proxy_setting else ("http", proxy_setting)
                        user_pass, host_port = rest.split("@", 1) if "@" in rest else ("", rest)
                        user, password = user_pass.split(":", 1) if ":" in user_pass else (user_pass, "")
                        pw_proxy = {
                            "server": f"{scheme_part}://{host_port}",
                            "username": user,
                            "password": password
                        }
                    else:
                        pw_proxy = {"server": proxy_setting}
                elif isinstance(proxy_setting, dict):
                    pw_proxy = proxy_setting
                    httpx_proxy = proxy_setting.get("server")

            if config and getattr(config, 'javascript_rendering', False):
                from app.core.playwright_scraper import PlaywrightScraper
                scraper = PlaywrightScraper(
                    job_id=job_id,
                    start_url=url,
                    max_pages=max_pages,
                    max_products=max_products,
                    max_depth=max_depth,
                    request_delay=request_delay,
                    proxy=pw_proxy,
                    on_log=write_log,
                    on_product_batch=save_products,
                    on_page_done=on_page_done,
                )
            else:
                scraper = HttpxScraper(
                    job_id=job_id,
                    start_url=url,
                    max_pages=max_pages,
                    max_products=max_products,
                    max_depth=max_depth,
                    request_delay=request_delay,
                    proxy=httpx_proxy,
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