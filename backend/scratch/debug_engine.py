import asyncio
import sys
import os

# Add backend to path
sys.path.append(os.getcwd())

from app.core.scraper_engine import ScraperEngine
from app.models.database import get_db_context
from app.models.job import Job, JobStatus

async def test_engine():
    async with get_db_context() as db:
        import uuid
        # Create a dummy job
        job = Job(
            job_id=f"test_job_{uuid.uuid4().hex[:6]}",
            name="Test",
            url="https://example.com",
            domain="example.com",
            status=JobStatus.PENDING
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)
        
        print(f"Created job {job.id}")
        
        try:
            engine = ScraperEngine(db, job.id, "https://example.com")
            print("Starting engine...")
            await engine.start()
            print("Engine finished")
        except Exception as e:
            import traceback
            print(f"Engine failed: {e}")
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_engine())
