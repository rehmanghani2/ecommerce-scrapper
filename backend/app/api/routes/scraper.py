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
    DetectedSelectors, ScraperConfig
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

@router.post("/preview", response_model=DetectedSelectors)
async def preview_scraping(request: ScraperPreviewRequest):
    try:
        import httpx

        detector = PatternDetector()

        # 1 Fetch page HTML
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            response = await client.get(str(request.url), headers=headers)
            response.raise_for_status()
            html = response.text

        # 2 Analyze HTML
        result = await detector.analyze_page(
            html,
            str(request.url)
        )

        return DetectedSelectors(
            confidence=result.get("confidence", 0.0),
            platform=result.get("platform"),
            selectors=result.get("selectors", {}),
            sample_products=result.get("sample_products", [])
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze URL: {str(e)}"
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
    """Background task to run the scraper."""
    from app.models.database import get_db_context
    from app.core.scraper_engine import ScraperEngine
    
    async with get_db_context() as db:
        try:
            # Update job status
            job = await db.get(Job, job_id)
            if not job:
                return
            
            job.status = JobStatus.RUNNING
            await db.commit()
            
            # Run scraper
            engine = ScraperEngine(
                db=db,
                job_id=job_id,
                start_url=url,
                max_depth=config.max_depth if config else 3,
                max_pages=config.max_pages if config else 100
            )
            await engine.start()
            
        except Exception as e:
            # Update job with error
            job = await db.get(Job, job_id)
            if job:
                job.status = JobStatus.FAILED
                job.error_message = str(e)
                await db.commit()