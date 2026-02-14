"""
Celery Worker Application
Main entry point for the Celery task queue.
"""

from celery import Celery
from celery.signals import (
    worker_ready,
    worker_shutdown,
    task_prerun,
    task_postrun,
    task_failure,
)
import logging
import asyncio
from typing import Optional

from workers import celery_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create Celery app
celery_app = Celery("ecommerce_scraper")

# Load configuration
celery_app.config_from_object(celery_config)

# Auto-discover tasks
celery_app.autodiscover_tasks(["workers"])


# ============== Signals ==============

@worker_ready.connect
def on_worker_ready(sender, **kwargs):
    """Called when worker is ready to accept tasks."""
    logger.info(f"Worker {sender.hostname} is ready")
    
    # Initialize browser manager in worker process
    try:
        from app.utils.browser_manager import BrowserManager
        logger.info("Browser manager initialized for worker")
    except Exception as e:
        logger.warning(f"Could not initialize browser manager: {e}")


@worker_shutdown.connect
def on_worker_shutdown(sender, **kwargs):
    """Called when worker is shutting down."""
    logger.info(f"Worker {sender.hostname} shutting down")
    
    # Cleanup browser manager
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        from app.utils.browser_manager import shutdown_browser_manager
        loop.run_until_complete(shutdown_browser_manager())
        
        loop.close()
        logger.info("Browser manager shutdown complete")
    except Exception as e:
        logger.warning(f"Error during browser manager shutdown: {e}")


@task_prerun.connect
def on_task_prerun(sender, task_id, task, args, kwargs, **other):
    """Called before a task is executed."""
    logger.info(f"Task starting: {task.name}[{task_id}]")


@task_postrun.connect
def on_task_postrun(sender, task_id, task, args, kwargs, retval, state, **other):
    """Called after a task is executed."""
    logger.info(f"Task completed: {task.name}[{task_id}] - State: {state}")


@task_failure.connect
def on_task_failure(sender, task_id, exception, args, kwargs, traceback, einfo, **other):
    """Called when a task fails."""
    logger.error(f"Task failed: {sender.name}[{task_id}] - Error: {exception}")


# ============== Utility Functions ==============

def get_async_loop() -> asyncio.AbstractEventLoop:
    """Get or create an event loop for async tasks."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError("Event loop is closed")
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop


def run_async(coro):
    """Run an async coroutine in the current thread."""
    loop = get_async_loop()
    return loop.run_until_complete(coro)


# ============== Base Task Class ==============

class AsyncTask(celery_app.Task):
    """Base task class for async operations."""
    
    abstract = True
    
    def __init__(self):
        super().__init__()
        self._db_session: Optional[any] = None
    
    async def get_db_session(self):
        """Get database session for the task."""
        if self._db_session is None:
            from app.models.database import AsyncSessionLocal
            self._db_session = AsyncSessionLocal()
        return self._db_session
    
    async def close_db_session(self):
        """Close the database session."""
        if self._db_session:
            await self._db_session.close()
            self._db_session = None
    
    def on_success(self, retval, task_id, args, kwargs):
        """Called on task success."""
        run_async(self.close_db_session())
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Called on task failure."""
        run_async(self.close_db_session())
    
    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Called when task is retried."""
        run_async(self.close_db_session())


# Export app for celery CLI
app = celery_app


if __name__ == "__main__":
    celery_app.start()