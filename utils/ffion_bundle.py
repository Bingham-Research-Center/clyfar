"""Helpers for resolving versioned Ffion bundle files.

Ffion has a single version axis. Each Ffion version pins the editable files that
shape outlook generation:

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

from utils.versioning import get_ffion_version

_REPO_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_REGISTRY_PATH = _REPO_ROOT / "templates" / "llm" / "ffion_registry.json"
_ENV_MANIFEST_KEYS = ("FFION_MANIFEST", "LLM_FFION_MANIFEST")


@dataclass(frozen=True)
class FfionBundle:
    """Resolved metadata for a versioned Ffion bundle."""

    ffion_version: str
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
    if value.lower().startswith("ffion-v"):
        return value.split("ffion-v", 1)[1].strip()
    if value.lower().startswith("v"):
        return value[1:].strip()
    return value


def sha256_file(path: Path) -> str:
    """Return the sha256 hex digest for a file."""
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


def load_ffion_registry(path: Path = _DEFAULT_REGISTRY_PATH) -> dict[str, Any]:
    """Return the Ffion bundle registry JSON."""
    if not path.exists():
        return {"versions": {}}
    return _load_json(path)


def resolve_ffion_bundle(
    ffion_version: str | None = None,
    *,
    manifest_path: str | Path | None = None,
    registry_path: Path = _DEFAULT_REGISTRY_PATH,
) -> FfionBundle:
    """Resolve a concrete Ffion bundle from the registry or a manifest override."""
    explicit_version = _normalise_version(ffion_version) if ffion_version else None
    requested_version = explicit_version or _normalise_version(get_ffion_version())

    manifest_override = manifest_path or _first_env_value(_ENV_MANIFEST_KEYS)
    if manifest_override:
        manifest = Path(manifest_override).expanduser()
        if not manifest.is_absolute():
            manifest = (_REPO_ROOT / manifest).resolve()
    else:
        registry = load_ffion_registry(registry_path)
        versions = registry.get("versions", {})
        entry = versions.get(requested_version)
        if entry is None:
            raise FileNotFoundError(
                f"Ffion version {requested_version!r} not found in registry {registry_path}"
            )
        manifest = _resolve_path(entry.get("manifest"), relative_to=registry_path.parent)
        if manifest is None:
            raise FileNotFoundError(
                f"Registry entry for Ffion version {requested_version!r} is missing a manifest path"
            )

    if not manifest.exists():
        raise FileNotFoundError(f"Ffion manifest not found: {manifest}")

    data = _load_json(manifest)
    base_dir = manifest.parent

    bundle_version = _normalise_version(str(data.get("ffion_version", requested_version or "")))
    if not bundle_version:
        raise ValueError(f"Ffion manifest is missing ffion_version: {manifest}")
    if explicit_version and bundle_version != explicit_version:
        raise ValueError(
            f"Ffion manifest version {bundle_version!r} does not match requested version {explicit_version!r}"
        )

    prompt_template = _resolve_path(data.get("prompt_template"), relative_to=base_dir)
    if prompt_template is None or not prompt_template.exists():
        raise FileNotFoundError(f"Prompt template not found for Ffion bundle: {manifest}")

    bias_file = _resolve_path(data.get("bias_file"), relative_to=base_dir)
    if bias_file is not None and not bias_file.exists():
        raise FileNotFoundError(f"Bias file not found for Ffion bundle: {bias_file}")

    qa_file = _resolve_path(data.get("qa_file"), relative_to=base_dir)
    if qa_file is not None and not qa_file.exists():
        raise FileNotFoundError(f"QA file not found for Ffion bundle: {qa_file}")

    return FfionBundle(
        ffion_version=bundle_version,
        label=str(data.get("label", f"Ffion v{bundle_version}")),
        manifest_path=manifest,
        prompt_template=prompt_template,
        bias_file=bias_file,
        qa_file=qa_file,
        qa_enabled_by_default=bool(data.get("qa_enabled_by_default", False)),
        notes=str(data.get("notes", "")).strip(),
        prompt_sha256=sha256_file(prompt_template),
        bias_sha256=sha256_file(bias_file) if bias_file else None,
        qa_sha256=sha256_file(qa_file) if qa_file else None,
    )
