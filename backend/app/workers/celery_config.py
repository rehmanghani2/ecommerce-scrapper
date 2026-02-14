"""
Celery Configuration
Defines all settings for the Celery task queue.
"""

from datetime import timedelta
import os

# Broker settings
broker_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1")
result_backend = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")

# Task settings
task_serializer = "json"
result_serializer = "json"
accept_content = ["json"]
timezone = "UTC"
enable_utc = True

# Task execution settings
task_acks_late = True
task_reject_on_worker_lost = True
task_time_limit = 3600  # 1 hour max per task
task_soft_time_limit = 3300  # Soft limit at 55 minutes

# Worker settings
worker_prefetch_multiplier = 1  # One task at a time for scraping
worker_concurrency = 4  # Number of concurrent workers
worker_max_tasks_per_child = 50  # Restart worker after 50 tasks

# Result settings
result_expires = 86400  # Results expire after 24 hours
result_extended = True

# Task routing
task_routes = {
    "workers.tasks.scrape_website_task": {"queue": "scraping"},
    "workers.tasks.process_url_task": {"queue": "scraping"},
    "workers.tasks.export_data_task": {"queue": "exports"},
    "workers.tasks.cleanup_old_jobs_task": {"queue": "maintenance"},
    "workers.tasks.send_notification_task": {"queue": "notifications"},
}

# Queue definitions
task_queues = {
    "scraping": {
        "exchange": "scraping",
        "routing_key": "scraping",
    },
    "exports": {
        "exchange": "exports",
        "routing_key": "exports",
    },
    "maintenance": {
        "exchange": "maintenance",
        "routing_key": "maintenance",
    },
    "notifications": {
        "exchange": "notifications",
        "routing_key": "notifications",
    },
}

# Default queue
task_default_queue = "scraping"

# Retry settings
task_autoretry_for = (Exception,)
task_retry_kwargs = {"max_retries": 3, "countdown": 60}

# Beat schedule (periodic tasks)
beat_schedule = {
    "cleanup-old-jobs": {
        "task": "workers.tasks.cleanup_old_jobs_task",
        "schedule": timedelta(hours=24),
        "options": {"queue": "maintenance"},
    },
    "cleanup-old-exports": {
        "task": "workers.tasks.cleanup_old_exports_task",
        "schedule": timedelta(hours=12),
        "options": {"queue": "maintenance"},
    },
    "health-check": {
        "task": "workers.tasks.health_check_task",
        "schedule": timedelta(minutes=5),
        "options": {"queue": "maintenance"},
    },
}

# Logging
worker_hijack_root_logger = False
worker_log_format = "[%(asctime)s: %(levelname)s/%(processName)s] %(message)s"
worker_task_log_format = "[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s"