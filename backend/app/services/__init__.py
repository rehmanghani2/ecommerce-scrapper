"""Service package with lazy imports to avoid loading unrelated integrations."""

from importlib import import_module

_EXPORTS = {
    "JobService": ".job_service",
    "ExportService": ".export_service",
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
