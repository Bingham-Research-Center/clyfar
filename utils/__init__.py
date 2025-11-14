"""Lightweight utils package namespace.

Expose only the helpers that downstream modules actually use and lazily import
their submodules to keep CLI startup fast.
"""

from importlib import import_module
from types import ModuleType
from typing import Dict

__all__ = [
    "utils",
    "download_utils",
    "geog_funcs",
    "lookups",
]

_MODULE_MAP: Dict[str, str] = {name: f".{name}" for name in __all__}


def __getattr__(name: str) -> ModuleType:
    if name not in _MODULE_MAP:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = import_module(_MODULE_MAP[name], __name__)
    globals()[name] = module
    return module


def __dir__() -> list[str]:
    return sorted(list(__all__) + list(globals().keys()))
