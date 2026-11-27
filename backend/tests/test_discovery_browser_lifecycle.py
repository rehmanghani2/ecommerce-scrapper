import ast
import inspect

from app.api.routes.scraper import discover_website


def test_discovery_does_not_close_browser_after_playwright_context_exits():
    """The async_playwright context owns browser shutdown and its driver lifecycle."""
    source = inspect.getsource(discover_website)
    tree = ast.parse(source)

    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "close"
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "browser"
    ]

    assert calls == []
    assert any(
        isinstance(node, ast.AsyncWith)
        and any(
            isinstance(item.context_expr, ast.Call)
            and isinstance(item.context_expr.func, ast.Name)
            and item.context_expr.func.id == "async_playwright"
            for item in node.items
        )
        for node in ast.walk(tree)
    )
