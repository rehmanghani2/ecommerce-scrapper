import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _function(tree, name):
    return next(
        node for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == name
    )


def _source_tree(path):
    return ast.parse(path.read_text(encoding="utf-8"))


def test_discovery_endpoint_dispatches_to_worker_instead_of_launching_browser():
    tree = _source_tree(ROOT / "app" / "api" / "routes" / "scraper.py")
    endpoint = _function(tree, "discover_website")
    source = ast.get_source_segment(
        (ROOT / "app" / "api" / "routes" / "scraper.py").read_text(encoding="utf-8"),
        endpoint,
    )
    assert "discover_website_task.delay" in source
    assert "async_playwright" not in source


def test_start_endpoint_queues_crawl_instead_of_using_api_background_tasks():
    tree = _source_tree(ROOT / "app" / "api" / "routes" / "scraper.py")
    endpoint = _function(tree, "start_scraping")
    source = ast.get_source_segment(
        (ROOT / "app" / "api" / "routes" / "scraper.py").read_text(encoding="utf-8"),
        endpoint,
    )
    assert "execute_scrape_job.delay" in source
    assert "background_tasks.add_task" not in source
    assert "run_scraper_job" not in source


def test_worker_runs_scraper_engine_inside_its_own_async_loop():
    tree = _source_tree(ROOT / "app" / "worker" / "tasks.py")
    source = (ROOT / "app" / "worker" / "tasks.py").read_text(encoding="utf-8")
    assert "asyncio.run(_execute_scrape_job" in source
    assert "ScraperEngine(" in source
    assert "get_db_context()" in source


def test_worker_image_uses_playwright_browser_base_image():
    dockerfile = (ROOT.parent.parent / "workers" / "Dockerfile").read_text(encoding="utf-8")
    assert dockerfile.startswith("FROM mcr.microsoft.com/playwright/python:")
