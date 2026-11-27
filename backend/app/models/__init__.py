"""Database model package with lazy exports to avoid importing unrelated models."""

from importlib import import_module

_EXPORTS = {
    "Base": ".database",
    "get_db": ".database",
    "engine": ".database",
    "AsyncSessionLocal": ".database",
    "Job": ".job",
    "JobStatus": ".job",
    "Product": ".product",
    "ProductImage": ".product",
    "ProductVariant": ".product",
    "PriceHistory": ".product",
    "ProductReview": ".product",
    "ProductSentimentSummary": ".product",
    "ProductStockHistory": ".product",
    "ProductInventoryForecast": ".product",
    "ScheduledJob": ".schedule",
    "IntegrationConfig": ".integration",
    "SyncLog": ".integration",
    "AlertConfig": ".alert",
    "AlertNotificationLog": ".alert",
    "RepricingRule": ".repricing",
    "RepricingLog": ".repricing",
    "SelectorPreset": ".selector_preset",
    "User": ".user",
    "ProxyRecord": ".proxy",
    "ReportSchedule": ".report",
    "GeneratedReport": ".report",
    "PricingSimulationScenario": ".simulator",
    "ProductPromotion": ".promotion",
    "SerpKeyword": ".serp",
    "SerpRankingItem": ".serp",
    "ProductBuyBoxState": ".buybox",
    "ProductBuyBoxHistory": ".buybox",
    "DomainThrottlePolicy": ".throttle",
    "TaxonomyStandard": ".taxonomy",
    "TaxonomyNode": ".taxonomy",
    "CategoryMappingRule": ".taxonomy",
    "ProductTaxonomyMapping": ".taxonomy",
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
