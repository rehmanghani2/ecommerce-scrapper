from fastapi.routing import APIRoute

from app.api.routes.scraper import _to_selector_config, preview_scraping, router
from app.schemas.scraper_schema import SelectorConfig


def test_preview_route_is_registered_only_for_preview_handler():
    preview_routes = [
        route
        for route in router.routes
        if isinstance(route, APIRoute)
        and route.path == "/preview"
        and "POST" in route.methods
    ]

    assert len(preview_routes) == 1
    assert preview_routes[0].endpoint is preview_scraping


def test_selector_conversion_returns_nested_selector_config():
    selectors = _to_selector_config({"product_name": ".product-title"})

    assert isinstance(selectors, SelectorConfig)
    assert selectors.product_name == ".product-title"
