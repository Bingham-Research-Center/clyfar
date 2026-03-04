"""Helpers for resolving runtime version strings.

Source of truth for runtime metadata is ``__init__.__version__`` at repo root,
which should track the current stable git tag. Ffion's runtime version is kept
as a repo constant in this module for deterministic prompt/banner generation.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

_VERSION_RE = re.compile(r"__version__\s*=\s*['\"](?P<version>[^'\"]+)['\"]")
_REPO_ROOT = Path(__file__).resolve().parents[1]
_INIT_PATH = _REPO_ROOT / "__init__.py"
FFION_VERSION = "1.1.1"


def _normalise_version(raw: str) -> str:
    """Normalise optional ``v``-prefixed strings to bare semantic version."""
    value = raw.strip()
    if value.lower().startswith("ffion-v"):
        return value.split("ffion-v", 1)[1].strip()
    if value.lower().startswith("v"):
        return value[1:].strip()
    return value


def get_clyfar_version(default: str = "1.0.2") -> str:
    """Return the active clyfar version string.

    Resolution order:
    1. ``CLYFAR_VERSION`` environment override (if set).
    2. ``__version__`` from repo-root ``__init__.py``.
    3. ``default`` fallback.
    """
    env_override = os.getenv("CLYFAR_VERSION")
    if env_override:
        return _normalise_version(env_override)

    try:
        text = _INIT_PATH.read_text(encoding="utf-8")
    except OSError:
        return default

    match = _VERSION_RE.search(text)
    if not match:
        return default
    return _normalise_version(match.group("version"))


def get_ffion_version(default: str = FFION_VERSION) -> str:
    """Return the active ffion version string.

    Resolution order:
    1. ``FFION_VERSION`` environment override (if set).
    2. Repo constant ``FFION_VERSION``.
    3. ``default`` fallback.
    """
    env_override = os.getenv("FFION_VERSION")
    if env_override:
        return _normalise_version(env_override)
    return _normalise_version(FFION_VERSION or default)
