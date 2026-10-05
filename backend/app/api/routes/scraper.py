"""
Scraper API routes.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Dict, Any
import uuid
import json
from urllib.parse import urlparse

from app.models.database import get_db
from app.models.job import Job, JobStatus, JobType
from app.models.selector_preset import SelectorPreset
from app.schemas.scraper_schema import (
    ScraperRequest, ScraperResponse, ScraperPreviewRequest,
    DetectedSelectors, ScraperConfig, SelectorConfig
)
from app.core.pattern_detector import PatternDetector
from app.services.visual_picker_service import visual_picker_service
from app.services.ai_extractor_service import ai_extractor_service


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
    db: AsyncSession = Depends(get_db)
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
                            p_curr = data.get("currency") or "USD"

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
                                    
                                    existing_p.price = p_price
                                    existing_p.lowest_price = min(float(existing_p.lowest_price or p_price), p_price)
                                    existing_p.highest_price = max(float(existing_p.highest_price or p_price), p_price)

                                if p_text:
                                    existing_p.price_text = p_text
                                if data.get("image_url"):
                                    existing_p.image_url = data.get("image_url")
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
                                    url=p_url or f"{url}#{saved}",
                                    price=p_price,
                                    previous_price=None,
                                    price_change=0,
                                    price_change_percentage=0,
                                    lowest_price=p_price,
                                    highest_price=p_price,
                                    price_text=p_text,
                                    currency=p_curr,
                                    image_url=data.get("image_url"),
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
            if any(m in domain_lower for m in ("amazon.", "ebay.", "walmart.", "etsy.", "wix.")) or detected_platform in ("amazon", "ebay", "walmart", "etsy", "wix"):
                use_pw = True

            if use_pw:
                from app.core.playwright_scraper import PlaywrightScraper
                scraper = PlaywrightScraper(
                    job_id=job_id,
                    start_url=url,
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