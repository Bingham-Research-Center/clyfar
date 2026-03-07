#!/usr/bin/env python3
"""Resolve a Ffion bundle and print a selected field."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from utils.ffion_bundle import resolve_ffion_bundle


def main() -> None:
    parser = argparse.ArgumentParser(description="Resolve Ffion bundle metadata.")
    parser.add_argument("--ffion-version", help="Ffion version to resolve.")
    parser.add_argument("--ffion-manifest", help="Explicit Ffion manifest path to resolve.")
    parser.add_argument(
        "--field",
        choices=(
            "ffion_version",
            "label",
            "manifest_path",
            "prompt_template",
            "bias_file",
            "qa_file",
            "qa_enabled_by_default",
            "prompt_sha256",
            "bias_sha256",
            "qa_sha256",
        ),
        help="Print a single field value instead of JSON.",
    )
    args = parser.parse_args()

    bundle = resolve_ffion_bundle(
        ffion_version=args.ffion_version,
        manifest_path=args.ffion_manifest,
    )
    payload = {
        "ffion_version": bundle.ffion_version,
        "label": bundle.label,
        "manifest_path": str(bundle.manifest_path),
        "prompt_template": str(bundle.prompt_template),
        "bias_file": str(bundle.bias_file) if bundle.bias_file else "",
        "qa_file": str(bundle.qa_file) if bundle.qa_file else "",
        "qa_enabled_by_default": bundle.qa_enabled_by_default,
        "prompt_sha256": bundle.prompt_sha256,
        "bias_sha256": bundle.bias_sha256 or "",
        "qa_sha256": bundle.qa_sha256 or "",
    }
    if args.field:
        value = payload[args.field]
        if isinstance(value, bool):
            print("1" if value else "0")
        else:
            print(value)
        return

    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
