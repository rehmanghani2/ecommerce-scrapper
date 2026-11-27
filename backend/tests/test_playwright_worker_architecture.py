import ast
from pathlib import Path


BACKEND = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[2]


def _function(tree, name):
    return next(
        node for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == name
    )


def _source_tree(path):
    return ast.parse(path.read_text(encoding="utf-8"))


def test_discovery_endpoint_dispatches_to_worker_instead_of_launching_browser():
    path = BACKEND / "app" / "api" / "routes" / "scraper.py"
    source = path.read_text(encoding="utf-8")
    endpoint = _function(ast.parse(source), "discover_website")
    endpoint_source = ast.get_source_segment(source, endpoint)
    assert "discover_website_task.delay" in endpoint_source
    assert "async_playwright" not in endpoint_source


def test_start_endpoint_queues_crawl_instead_of_using_api_background_tasks():
    path = BACKEND / "app" / "api" / "routes" / "scraper.py"
    source = path.read_text(encoding="utf-8")
    endpoint = _function(ast.parse(source), "start_scraping")
    endpoint_source = ast.get_source_segment(source, endpoint)
    assert "execute_scrape_job.delay" in endpoint_source
    assert "background_tasks.add_task" not in endpoint_source
    assert "run_scraper_job" not in endpoint_source


def test_bulk_start_endpoint_dispatches_to_worker():
    path = BACKEND / "app" / "api" / "routes" / "scraper.py"
    source = path.read_text(encoding="utf-8")
    endpoint = _function(ast.parse(source), "start_bulk_scraping")
    endpoint_source = ast.get_source_segment(source, endpoint)
    assert "execute_bulk_scrape_job.delay" in endpoint_source
    assert "background_tasks.add_task" not in endpoint_source


def test_worker_runs_scraper_engine_inside_its_own_async_loop():
    path = BACKEND / "app" / "worker" / "tasks.py"
    source = path.read_text(encoding="utf-8")
    assert "asyncio.run(_execute_scrape_job" in source
    assert "ScraperEngine(" in source
    assert "get_db_context()" in source


def test_worker_image_uses_playwright_browser_base_image():
    dockerfile = (REPO_ROOT / "workers" / "Dockerfile").read_text(encoding="utf-8")
    assert dockerfile.startswith("FROM mcr.microsoft.com/playwright/python:")



def test_scheduled_jobs_dispatch_to_worker():
    path = BACKEND / "app" / "services" / "scheduler_service.py"
    source = path.read_text(encoding="utf-8")
    endpoint = _function(ast.parse(source), "trigger_schedule")
    endpoint_source = ast.get_source_segment(source, endpoint)
    assert "execute_scrape_job.delay" in endpoint_source
    assert "run_scraper_job" not in endpoint_source


def test_failed_job_retry_dispatches_to_worker():
    path = BACKEND / "app" / "api" / "routes" / "jobs.py"
    source = path.read_text(encoding="utf-8")
    endpoint = _function(ast.parse(source), "retry_job")
    endpoint_source = ast.get_source_segment(source, endpoint)
    assert "execute_scrape_job.delay" in endpoint_source
