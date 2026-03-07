#!/usr/bin/env python3
"""Resolve a Ffion prompt-science bundle and print a selected field."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from utils.ffion_science import resolve_ffion_science_bundle


def main() -> None:
    parser = argparse.ArgumentParser(description="Resolve Ffion prompt-science bundle metadata.")
    parser.add_argument("--science-version", help="Science bundle version to resolve.")
    parser.add_argument("--science-manifest", help="Explicit manifest path to resolve.")
    parser.add_argument(
        "--field",
        choices=(
            "science_version",
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

    bundle = resolve_ffion_science_bundle(
        science_version=args.science_version,
        manifest_path=args.science_manifest,
    )
    payload = {
        "science_version": bundle.science_version,
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

