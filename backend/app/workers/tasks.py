"""
Celery Tasks
Background tasks for scraping, exporting, and maintenance.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from celery import group
from celery.exceptions import SoftTimeLimitExceeded
import logging

from workers.celery_worker import celery_app, AsyncTask, run_async

logger = logging.getLogger(__name__)


# ============== Scraping Tasks ==============

@celery_app.task(
    bind=True,
    base=AsyncTask,
    name="workers.tasks.scrape_website_task",
    max_retries=3,
    soft_time_limit=3300,
    time_limit=3600,
)
def scrape_website_task(
    self,
    job_id: int,
    url: str,
    config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Main task for scraping a website.
    
    Args:
        job_id: Database job ID
        url: Starting URL
        config: Scraper configuration
    
    Returns:
        Scraping results
    """
    logger.info(f"Starting scrape task for job {job_id}: {url}")
    
    try:
        result = run_async(_scrape_website_async(self, job_id, url, config))
        return result
        
    except SoftTimeLimitExceeded:
        logger.warning(f"Soft time limit exceeded for job {job_id}")
        run_async(_update_job_status(job_id, "failed", "Time limit exceeded"))
        raise
        
    except Exception as e:
        logger.error(f"Scrape task failed for job {job_id}: {e}")
        run_async(_update_job_status(job_id, "failed", str(e)))
        raise self.retry(exc=e, countdown=60)


async def _scrape_website_async(
    task,
    job_id: int,
    url: str,
    config: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """Async implementation of website scraping."""
    from app.models.database import AsyncSessionLocal
    from app.core.scraper_engine import ScraperEngine, ScraperConfig
    
    async with AsyncSessionLocal() as db:
        try:
            # Create scraper config
            scraper_config = ScraperConfig(**config) if config else ScraperConfig()
            
            # Create and run scraper
            engine = ScraperEngine(scraper_config)
            
            # Progress callback
            async def update_progress(progress_data: Dict[str, Any]):
                task.update_state(
                    state="PROGRESS",
                    meta={
                        "progress": progress_data.get("progress", 0),
                        "pages_scraped": progress_data.get("pages_scraped", 0),
                        "products_scraped": progress_data.get("products_scraped", 0),
                        "current_url": progress_data.get("current_url", ""),
                    }
                )
            
            result = await engine.run(
                job_id=job_id,
                start_url=url,
                config=scraper_config,
                db=db,
                progress_callback=update_progress
            )
            
            # Send notification on completion
            await _send_job_notification(job_id, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Async scrape failed: {e}")
            raise


async def _update_job_status(
    job_id: int, 
    status: str, 
    error_message: Optional[str] = None
):
    """Update job status in database."""
    from app.models.database import AsyncSessionLocal
    from app.models.job import Job, JobStatus
    
    async with AsyncSessionLocal() as db:
        job = await db.get(Job, job_id)
        if job:
            job.status = JobStatus(status)
            if error_message:
                job.error_message = error_message
            job.completed_at = datetime.utcnow()
            await db.commit()


async def _send_job_notification(job_id: int, result: Dict[str, Any]):
    """Send notification for completed job."""
    from app.models.database import AsyncSessionLocal
    from app.models.job import Job
    
    async with AsyncSessionLocal() as db:
        job = await db.get(Job, job_id)
        if job and job.user_id:
            # Queue notification task
            send_notification_task.delay(
                user_id=job.user_id,
                notification_type="job_completed",
                data={
                    "job_id": job.job_id,
                    "job_name": job.name,
                    "status": result.get("status"),
                    "products_scraped": result.get("products_scraped", 0),
                    "duration": result.get("duration_seconds", 0),
                }
            )


@celery_app.task(
    bind=True,
    base=AsyncTask,
    name="workers.tasks.process_url_task",
    max_retries=3,
)
def process_url_task(
    self,
    job_id: int,
    url: str,
    page_type: str = "auto"
) -> Dict[str, Any]:
    """
    Process a single URL (used for distributed scraping).
    
    Args:
        job_id: Database job ID
        url: URL to process
        page_type: Type of page (category, product, auto)
    
    Returns:
        Processing results
    """
    logger.info(f"Processing URL for job {job_id}: {url}")
    
    try:
        result = run_async(_process_url_async(job_id, url, page_type))
        return result
        
    except Exception as e:
        logger.error(f"URL processing failed: {e}")
        raise self.retry(exc=e, countdown=30)


async def _process_url_async(
    job_id: int,
    url: str,
    page_type: str
) -> Dict[str, Any]:
    """Async implementation of URL processing."""
    from app.models.database import AsyncSessionLocal
    from app.utils.browser_manager import get_browser_manager
    from app.core.product_extractor import ProductExtractor
    from app.utils.helpers import extract_domain
    
    async with AsyncSessionLocal() as db:
        browser_manager = await get_browser_manager()
        domain = extract_domain(url)
        
        async with browser_manager.get_page(domain=domain) as page:
            await page.goto(url, wait_until="domcontentloaded")
            
            extractor = ProductExtractor(base_url=url)
            
            if page_type == "product":
                product = await extractor.extract_from_detail_page(page)
                products = [product] if product else []
            else:
                products = await extractor.extract_from_listing_page(page)
            
            return {
                "url": url,
                "products_found": len(products),
                "products": products
            }


# ============== Export Tasks ==============

@celery_app.task(
    bind=True,
    base=AsyncTask,
    name="workers.tasks.export_data_task",
)
def export_data_task(
    self,
    job_id: int,
    format: str = "csv",
    filters: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Export scraped data to file.
    
    Args:
        job_id: Database job ID
        format: Export format (csv, excel, json)
        filters: Optional filters to apply
    
    Returns:
        Export result with file path
    """
    logger.info(f"Exporting data for job {job_id} to {format}")
    
    try:
        result = run_async(_export_data_async(job_id, format, filters))
        return result
        
    except Exception as e:
        logger.error(f"Export failed: {e}")
        raise


async def _export_data_async(
    job_id: int,
    format: str,
    filters: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """Async implementation of data export."""
    from app.models.database import AsyncSessionLocal
    from app.services.export_service import ExportService
    
    async with AsyncSessionLocal() as db:
        export_service = ExportService(db)
        
        file_path = await export_service.export_job_products(
            job_id=job_id,
            format=format
        )
        
        return {
            "success": True,
            "file_path": file_path,
            "format": format,
        }


# ============== Notification Tasks ==============

@celery_app.task(
    name="workers.tasks.send_notification_task",
)
def send_notification_task(
    user_id: int,
    notification_type: str,
    data: Dict[str, Any]
) -> bool:
    """
    Send notification to user.
    
    Args:
        user_id: Target user ID
        notification_type: Type of notification
        data: Notification data
    
    Returns:
        Success status
    """
    logger.info(f"Sending {notification_type} notification to user {user_id}")
    
    try:
        result = run_async(_send_notification_async(user_id, notification_type, data))
        return result
        
    except Exception as e:
        logger.error(f"Notification failed: {e}")
        return False


async def _send_notification_async(
    user_id: int,
    notification_type: str,
    data: Dict[str, Any]
) -> bool:
    """Async implementation of notification sending."""
    from app.services.notification_service import NotificationService
    
    service = NotificationService()
    return await service.send_notification(user_id, notification_type, data)


# ============== Maintenance Tasks ==============

@celery_app.task(
    name="workers.tasks.cleanup_old_jobs_task",
)
def cleanup_old_jobs_task(days_old: int = 30) -> Dict[str, Any]:
    """
    Clean up old completed/failed jobs.
    
    Args:
        days_old: Delete jobs older than this many days
    
    Returns:
        Cleanup statistics
    """
    logger.info(f"Cleaning up jobs older than {days_old} days")
    
    try:
        result = run_async(_cleanup_old_jobs_async(days_old))
        return result
        
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        raise


async def _cleanup_old_jobs_async(days_old: int) -> Dict[str, Any]:
    """Async implementation of job cleanup."""
    from app.models.database import AsyncSessionLocal
    from app.models.job import Job, JobStatus
    from sqlalchemy import delete, and_
    
    async with AsyncSessionLocal() as db:
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        
        # Delete old completed/failed jobs
        query = delete(Job).where(
            and_(
                Job.status.in_([JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]),
                Job.completed_at < cutoff_date
            )
        )
        
        result = await db.execute(query)
        await db.commit()
        
        deleted_count = result.rowcount
        
        logger.info(f"Deleted {deleted_count} old jobs")
        
        return {
            "deleted_jobs": deleted_count,
            "cutoff_date": cutoff_date.isoformat(),
        }


@celery_app.task(
    name="workers.tasks.cleanup_old_exports_task",
)
def cleanup_old_exports_task(hours_old: int = 24) -> Dict[str, Any]:
    """
    Clean up old export files.
    
    Args:
        hours_old: Delete exports older than this many hours
    
    Returns:
        Cleanup statistics
    """
    logger.info(f"Cleaning up exports older than {hours_old} hours")
    
    import os
    from app.config import settings
    
    deleted_count = 0
    total_size = 0
    cutoff_time = datetime.now().timestamp() - (hours_old * 3600)
    
    export_path = settings.EXPORT_PATH
    
    if os.path.exists(export_path):
        for filename in os.listdir(export_path):
            filepath = os.path.join(export_path, filename)
            if os.path.isfile(filepath):
                file_time = os.path.getctime(filepath)
                if file_time < cutoff_time:
                    file_size = os.path.getsize(filepath)
                    os.remove(filepath)
                    deleted_count += 1
                    total_size += file_size
    
    logger.info(f"Deleted {deleted_count} old export files ({total_size} bytes)")
    
    return {
        "deleted_files": deleted_count,
        "total_size_bytes": total_size,
    }


@celery_app.task(
    name="workers.tasks.health_check_task",
)
def health_check_task() -> Dict[str, Any]:
    """
    Perform health check on worker.
    
    Returns:
        Health check results
    """
    import psutil
    
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "cpu_percent": psutil.cpu_percent(),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_percent": psutil.disk_usage("/").percent,
    }


# ============== Batch Tasks ==============

@celery_app.task(
    bind=True,
    name="workers.tasks.batch_scrape_task",
)
def batch_scrape_task(
    self,
    urls: List[str],
    config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Scrape multiple URLs in batch.
    
    Args:
        urls: List of URLs to scrape
        config: Scraper configuration
    
    Returns:
        Batch results
    """
    logger.info(f"Starting batch scrape for {len(urls)} URLs")
    
    # Create a group of tasks
    tasks = group([
        scrape_website_task.s(None, url, config)
        for url in urls
    ])
    
    # Execute group
    result = tasks.apply_async()
    
    return {
        "batch_id": self.request.id,
        "total_urls": len(urls),
        "group_id": result.id,
    }


# ============== Scheduled Tasks ==============

@celery_app.task(
    name="workers.tasks.scheduled_scrape_task",
)
def scheduled_scrape_task(schedule_id: int) -> Dict[str, Any]:
    """
    Execute a scheduled scraping job.
    
    Args:
        schedule_id: ID of the schedule to execute
    
    Returns:
        Execution result
    """
    logger.info(f"Executing scheduled scrape {schedule_id}")
    
    try:
        result = run_async(_execute_scheduled_scrape(schedule_id))
        return result
        
    except Exception as e:
        logger.error(f"Scheduled scrape failed: {e}")
        raise


async def _execute_scheduled_scrape(schedule_id: int) -> Dict[str, Any]:
    """Execute a scheduled scrape job."""
    from app.models.database import AsyncSessionLocal
    from app.services.job_service import JobService
    
    # This would load schedule config from database
    # and create a new job based on it
    
    async with AsyncSessionLocal() as db:
        job_service = JobService(db)
        
        # Load schedule (placeholder - would need Schedule model)
        # schedule = await db.get(Schedule, schedule_id)
        
        # For now, return placeholder
        return {
            "schedule_id": schedule_id,
            "status": "executed",
        }