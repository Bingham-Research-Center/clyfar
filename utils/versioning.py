"""Helpers for resolving the current clyfar version string.

Source of truth for runtime metadata is ``__init__.__version__`` at repo root,
which should track the current stable git tag.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

_VERSION_RE = re.compile(r"__version__\s*=\s*['\"](?P<version>[^'\"]+)['\"]")
_REPO_ROOT = Path(__file__).resolve().parents[1]
_INIT_PATH = _REPO_ROOT / "__init__.py"


def get_clyfar_version(default: str = "1.0.1") -> str:
    """Return the active clyfar version string.

    Resolution order:
    1. ``CLYFAR_VERSION`` environment override (if set).
    2. ``__version__`` from repo-root ``__init__.py``.
    3. ``default`` fallback.
    """
    env_override = os.getenv("CLYFAR_VERSION")
    if env_override:
        return env_override.strip()

    try:
        text = _INIT_PATH.read_text(encoding="utf-8")
    except OSError:
        return default

    match = _VERSION_RE.search(text)
    if not match:
        return default
    return match.group("version")

