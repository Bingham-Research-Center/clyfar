"""Helpers for resolving versioned Ffion prompt-science bundles.

The prompt-science bundle is separate from the runtime Ffion version. It pins
the editable science-conditioning inputs that shape the generated outlook:

- prompt template
- short-term bias caveats
- optional QA/operator notes
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_REGISTRY_PATH = _REPO_ROOT / "templates" / "llm" / "science_registry.json"
_DEFAULT_SCIENCE_VERSION = "1.0.0"
_ENV_VERSION_KEYS = ("FFION_SCIENCE_VERSION", "LLM_SCIENCE_VERSION")
_ENV_MANIFEST_KEYS = ("FFION_SCIENCE_MANIFEST", "LLM_SCIENCE_MANIFEST")


@dataclass(frozen=True)
class FfionScienceBundle:
    """Resolved prompt-science bundle metadata."""

    science_version: str
    label: str
    manifest_path: Path
    prompt_template: Path
    bias_file: Path | None
    qa_file: Path | None
    qa_enabled_by_default: bool
    notes: str
    prompt_sha256: str
    bias_sha256: str | None
    qa_sha256: str | None


def _normalise_version(raw: str) -> str:
    value = raw.strip()
    if value.lower().startswith("ffion-science-v"):
        return value.split("ffion-science-v", 1)[1].strip()
    if value.lower().startswith("science-v"):
        return value.split("science-v", 1)[1].strip()
    if value.lower().startswith("v"):
        return value[1:].strip()
    return value


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _resolve_path(raw: str | None, *, relative_to: Path) -> Path | None:
    if not raw:
        return None
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = (relative_to / path).resolve()
    return path


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _first_env_value(keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = os.getenv(key)
        if value:
            return value
    return None


def load_science_registry(path: Path = _DEFAULT_REGISTRY_PATH) -> dict[str, Any]:
    """Return the science registry JSON, or an empty registry if missing."""
    if not path.exists():
        return {"active_science_version": _DEFAULT_SCIENCE_VERSION, "versions": {}}
    return _load_json(path)


def get_ffion_science_version(
    default: str = _DEFAULT_SCIENCE_VERSION,
    registry_path: Path = _DEFAULT_REGISTRY_PATH,
) -> str:
    """Return the active prompt-science version string."""
    env_override = _first_env_value(_ENV_VERSION_KEYS)
    if env_override:
        return _normalise_version(env_override)

    registry = load_science_registry(registry_path)
    active = registry.get("active_science_version") or default
    return _normalise_version(str(active))


def resolve_ffion_science_bundle(
    science_version: str | None = None,
    *,
    manifest_path: str | Path | None = None,
    registry_path: Path = _DEFAULT_REGISTRY_PATH,
) -> FfionScienceBundle:
    """Resolve a concrete prompt-science bundle from registry or manifest."""
    manifest_override = manifest_path or _first_env_value(_ENV_MANIFEST_KEYS)
    if manifest_override:
        manifest = Path(manifest_override).expanduser()
        if not manifest.is_absolute():
            manifest = (_REPO_ROOT / manifest).resolve()
    else:
        resolved_version = _normalise_version(
            science_version or get_ffion_science_version(registry_path=registry_path)
        )
        registry = load_science_registry(registry_path)
        versions = registry.get("versions", {})
        entry = versions.get(resolved_version)
        if entry is None:
            raise FileNotFoundError(
                f"Science version {resolved_version!r} not found in registry {registry_path}"
            )
        manifest = _resolve_path(entry.get("manifest"), relative_to=_REPO_ROOT)
        if manifest is None:
            raise FileNotFoundError(
                f"Registry entry for science version {resolved_version!r} is missing a manifest path"
            )

    if not manifest.exists():
        raise FileNotFoundError(f"Science manifest not found: {manifest}")

    data = _load_json(manifest)
    base_dir = manifest.parent

    bundle_version = _normalise_version(str(data.get("science_version", science_version or "")))
    if not bundle_version:
        raise ValueError(f"Science manifest is missing science_version: {manifest}")

    prompt_template = _resolve_path(data.get("prompt_template"), relative_to=base_dir)
    if prompt_template is None or not prompt_template.exists():
        raise FileNotFoundError(f"Prompt template not found for science bundle: {manifest}")

    bias_file = _resolve_path(data.get("bias_file"), relative_to=base_dir)
    if bias_file is not None and not bias_file.exists():
        raise FileNotFoundError(f"Bias file not found for science bundle: {bias_file}")

    qa_file = _resolve_path(data.get("qa_file"), relative_to=base_dir)
    if qa_file is not None and not qa_file.exists():
        raise FileNotFoundError(f"QA file not found for science bundle: {qa_file}")

    return FfionScienceBundle(
        science_version=bundle_version,
        label=str(data.get("label", f"Ffion Science v{bundle_version}")),
        manifest_path=manifest,
        prompt_template=prompt_template,
        bias_file=bias_file,
        qa_file=qa_file,
        qa_enabled_by_default=bool(data.get("qa_enabled_by_default", False)),
        notes=str(data.get("notes", "")).strip(),
        prompt_sha256=_sha256_file(prompt_template),
        bias_sha256=_sha256_file(bias_file) if bias_file else None,
        qa_sha256=_sha256_file(qa_file) if qa_file else None,
    )

