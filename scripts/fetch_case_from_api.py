#!/usr/bin/env python3
"""
Fetch Clyfar forecast JSON for a given init from the BasinWx API.

For a given init time, this script:
 - Calls /api/filelist/forecasts on the BasinWx server
 - Filters filenames matching the init (YYYYMMDD_HHMMZ)
 - Downloads:
      * forecast_possibility_heatmap_*_{init}.json  -> CASE_.../possibilities/
      * forecast_percentile_scenarios_*_{init}.json -> CASE_.../percentiles/
      * forecast_exceedance_probabilities_{init}.json -> CASE_.../probs/
 - Creates/updates data/json_tests/CASE_YYYYMMDD_HHMMZ/ accordingly

Usage (from repo root):
    python scripts/fetch_case_from_api.py --init 2025121200 --base-url https://basinwx.com

Notes:
- This script does not require CHPC access; it only talks to the website.
- It does not generate plots or LLM text; see run_case_pipeline.py for that.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, List

import requests

REPO_ROOT = Path(__file__).resolve().parents[1]


def parse_init(init: str) -> str:
    """Normalise init string to 'YYYYMMDD_HHMMZ'."""
    init = init.strip()
    if "_" in init and init.endswith("Z"):
        return init
    if len(init) == 10 and init.isdigit():
        date = init[:8]
        hour = init[8:]
        hhmm = hour.ljust(4, "0")
        return f"{date}_{hhmm}Z"
    raise ValueError(f"Unrecognised init format: {init}")


def case_root_for_init(base: Path, norm_init: str) -> Path:
    """Return CASE_YYYYMMDD_HHMMZ directory for a normalised init."""
    date, hhmmz = norm_init.split("_")
    hhmm = hhmmz.replace("Z", "")
    case_id = f"CASE_{date}_{hhmm}Z"
    return base / case_id


def fetch_filelist(base_url: str) -> List[str]:
    """Fetch list of forecast filenames from BasinWx."""
    url = f"{base_url.rstrip('/')}/api/filelist/forecasts"
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, dict) and "files" in data:
        return list(data["files"])
    if isinstance(data, list):
        return list(data)
    raise RuntimeError(f"Unexpected filelist format from {url}")


def download_file(base_url: str, filename: str, dest: Path) -> None:
    """Download a single JSON file from the public forecasts directory."""
    url = f"{base_url.rstrip('/')}/public/api/static/forecasts/{filename}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    dest.write_bytes(resp.content)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch Clyfar forecast JSON from BasinWx into a CASE directory."
    )
    parser.add_argument(
        "--init",
        required=True,
        help="Init time as YYYYMMDDHH or YYYYMMDD_HHMMZ (e.g. 2025121200 or 20251212_0000Z)",
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("BASINWX_API_URL", "https://basinwx.com"),
        help="Base URL for BasinWx (default from BASINWX_API_URL or https://basinwx.com)",
    )
    args = parser.parse_args()

    data_root = REPO_ROOT / "data" / "json_tests"
    data_root.mkdir(parents=True, exist_ok=True)

    norm_init = parse_init(args.init)
    case_root = case_root_for_init(data_root, norm_init)

    print(f"Init: {norm_init}")
    print(f"Base URL: {args.base_url}")
    print(f"Case root: {case_root}")

    filelist = fetch_filelist(args.base_url)
    print(f"Found {len(filelist)} forecast files on server.")

    # Filter filenames containing this init
    matches = [f for f in filelist if norm_init in f]
    if not matches:
        raise SystemExit(f"No forecast files containing {norm_init} found on server.")

    # Group by product type
    groups: Dict[str, List[str]] = {"possibilities": [], "percentiles": [], "probs": []}
    for name in matches:
        if name.startswith("forecast_possibility_heatmap_"):
            groups["possibilities"].append(name)
        elif name.startswith("forecast_percentile_scenarios_"):
            groups["percentiles"].append(name)
        elif name.startswith("forecast_exceedance_probabilities_"):
            groups["probs"].append(name)

    # Download each group
    for group, files in groups.items():
        if not files:
            continue
        print(f"Downloading {len(files)} {group} files...")
        for fname in files:
            if group == "probs" and len(files) > 1:
                # Prefer the canonical name without extra segments
                if fname != f"forecast_exceedance_probabilities_{norm_init}.json":
                    continue
            dest_dir = case_root / group
            dest = dest_dir / fname
            download_file(args.base_url, fname, dest)

    print("Done fetching JSON into CASE directory.")


if __name__ == "__main__":
    main()

