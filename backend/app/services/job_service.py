"""
Job Service Module
Handles job management operations.
"""

import asyncio
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
import logging

from app.models.job import Job, JobStatus, JobType
from app.models.product import Product
from app.core.scraper_engine import ScraperEngine, ScraperConfig

logger = logging.getLogger(__name__)


class JobService:
    """Service for managing scraping jobs."""
    
    def __init__(self, db: AsyncSession):
        """Initialize the job service."""
        self.db = db
        self._running_jobs: Dict[str, ScraperEngine] = {}
    
    async def create_job(
        self,
        url: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        job_type: JobType = JobType.FULL_SITE,
        config: Optional[Dict[str, Any]] = None,
        user_id: Optional[int] = None
    ) -> Job:
        """
        Create a new scraping job.
        
        Args:
            url: Target URL to scrape
            name: Job name
            description: Job description
            job_type: Type of job
            config: Scraper configuration
            user_id: Owner user ID
        
        Returns:
            Created Job instance
        """
        from urllib.parse import urlparse
        from app.utils.helpers import generate_job_id
        
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
        
        job = Job(
            job_id=generate_job_id(),
            name=name or f"Scrape {domain}",
            description=description,
            url=url,
            domain=domain,
            job_type=job_type,
            status=JobStatus.PENDING,
            config=config or {},
            user_id=user_id
        )
        
        self.db.add(job)
        await self.db.commit()
        await self.db.refresh(job)
        
        logger.info(f"Created job {job.job_id} for {domain}")
        
        return job
    
    async def get_job(self, job_id: str) -> Optional[Job]:
        """Get a job by its job_id."""
        query = select(Job).where(Job.job_id == job_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_job_by_id(self, id: int) -> Optional[Job]:
        """Get a job by its database ID."""
        return await self.db.get(Job, id)
    
    async def list_jobs(
        self,
        user_id: Optional[int] = None,
        status: Optional[JobStatus] = None,
        domain: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """
        List jobs with filtering and pagination.
        
        Returns:
            Dict with jobs, total count, and pagination info
        """
        # Build query
        query = select(Job)
        count_query = select(func.count(Job.id))
        
        # Apply filters
        filters = []
        if user_id:
            filters.append(Job.user_id == user_id)
        if status:
            filters.append(Job.status == status)
        if domain:
            filters.append(Job.domain.ilike(f"%{domain}%"))
        
        if filters:
            query = query.where(and_(*filters))
            count_query = count_query.where(and_(*filters))
        
        # Get total count
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0
        
        # Apply pagination and ordering
        offset = (page - 1) * page_size
        query = query.order_by(Job.created_at.desc()).offset(offset).limit(page_size)
        
        # Execute query
        result = await self.db.execute(query)
        jobs = result.scalars().all()
        
        return {
            "jobs": jobs,
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": (total + page_size - 1) // page_size
        }
    
    async def start_job(self, job_id: str) -> bool:
        """
        Start a pending job.
        
        Args:
            job_id: Job ID to start
        
        Returns:
            True if job was started
        """
        job = await self.get_job(job_id)
        if not job:
            return False
        
        if job.status not in [JobStatus.PENDING, JobStatus.PAUSED]:
            return False
        
        # Create scraper engine
        config_dict = job.config or {}
        config = ScraperConfig(**config_dict) if config_dict else ScraperConfig()
        
        engine = ScraperEngine(config)
        self._running_jobs[job_id] = engine
        
        # Start job in background
        asyncio.create_task(self._run_job(job, engine))
        
        return True
    
    async def _run_job(self, job: Job, engine: ScraperEngine) -> None:
        """Run a job in the background."""
        try:
            result = await engine.run(
                job_id=job.id,
                start_url=job.url,
                db=self.db
            )
            
            logger.info(f"Job {job.job_id} completed: {result}")
            
        except Exception as e:
            logger.error(f"Job {job.job_id} failed: {e}")
            
            job.status = JobStatus.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
            await self.db.commit()
        
        finally:
            # Remove from running jobs
            if job.job_id in self._running_jobs:
                del self._running_jobs[job.job_id]
    
    async def pause_job(self, job_id: str) -> bool:
        """Pause a running job."""
        if job_id in self._running_jobs:
            self._running_jobs[job_id].pause()
            
            job = await self.get_job(job_id)
            if job:
                job.status = JobStatus.PAUSED
                await self.db.commit()
            
            return True
        return False
    
    async def resume_job(self, job_id: str) -> bool:
        """Resume a paused job."""
        if job_id in self._running_jobs:
            self._running_jobs[job_id].resume()
            
            job = await self.get_job(job_id)
            if job:
                job.status = JobStatus.RUNNING
                await self.db.commit()
            
            return True
        return False
    
    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a running job."""
        if job_id in self._running_jobs:
            self._running_jobs[job_id].cancel()
        
        job = await self.get_job(job_id)
        if job and job.status in [JobStatus.RUNNING, JobStatus.PAUSED, JobStatus.PENDING]:
            job.status = JobStatus.CANCELLED
            job.completed_at = datetime.utcnow()
            await self.db.commit()
            return True
        
        return False
    
    async def delete_job(self, job_id: str) -> bool:
        """Delete a job and its products."""
        job = await self.get_job(job_id)
        if not job:
            return False
        
        if job.status == JobStatus.RUNNING:
            await self.cancel_job(job_id)
        
        await self.db.delete(job)
        await self.db.commit()
        
        logger.info(f"Deleted job {job_id}")
        return True
    
    async def get_job_products(
        self,
        job_id: str,
        page: int = 1,
        page_size: int = 50
    ) -> Dict[str, Any]:
        """Get products for a job with pagination."""
        job = await self.get_job(job_id)
        if not job:
            return {"products": [], "total": 0, "page": 1, "pages": 0}
        
        # Count products
        count_query = select(func.count(Product.id)).where(Product.job_id == job.id)
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0
        
        # Get products
        offset = (page - 1) * page_size
        query = (
            select(Product)
            .where(Product.job_id == job.id)
            .order_by(Product.id)
            .offset(offset)
            .limit(page_size)
        )
        result = await self.db.execute(query)
        products = result.scalars().all()
        
        return {
            "products": products,
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": (total + page_size - 1) // page_size
        }
    
    async def get_job_stats(self, job_id: str) -> Dict[str, Any]:
        """Get statistics for a job."""
        job = await self.get_job(job_id)
        if not job:
            return {}
        
        # Get product stats
        stats_query = select(
            func.count(Product.id).label('total'),
            func.count(Product.id).filter(Product.in_stock == True).label('in_stock'),
            func.avg(Product.price).label('avg_price'),
            func.min(Product.price).label('min_price'),
            func.max(Product.price).label('max_price'),
            func.count(func.distinct(Product.category)).label('categories'),
            func.count(func.distinct(Product.brand)).label('brands'),
        ).where(Product.job_id == job.id)
        
        result = await self.db.execute(stats_query)
        row = result.first()
        
        return {
            "job_id": job_id,
            "status": job.status.value,
            "total_products": row.total if row else 0,
            "in_stock_products": row.in_stock if row else 0,
            "average_price": float(row.avg_price) if row and row.avg_price else None,
            "min_price": float(row.min_price) if row and row.min_price else None,
            "max_price": float(row.max_price) if row and row.max_price else None,
            "unique_categories": row.categories if row else 0,
            "unique_brands": row.brands if row else 0,
            "pages_scraped": job.scraped_pages,
            "pages_failed": job.failed_pages,
            "duration": job.duration,
        }