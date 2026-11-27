"""Core scraping package with lazy imports to keep utility modules lightweight."""

from importlib import import_module

_EXPORTS = {
    "PatternDetector": ".pattern_detector",
    "ScraperEngine": ".scraper_engine",
    "ProductExtractor": ".product_extractor",
    "PaginationHandler": ".pagination_handler",
    "DataCleaner": ".data_cleaner",
}

__all__ = list(_EXPORTS)


def __getattr__(name):
    module_name = _EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = import_module(module_name, __name__)
    value = getattr(module, name)
    globals()[name] = value
    return value
