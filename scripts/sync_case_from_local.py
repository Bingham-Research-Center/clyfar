#!/usr/bin/env python3
"""
Populate CASE_YYYYMMDD_HHMMZ directories from a local JSON source tree.

This mirrors fetch_case_from_api.py but copies files from a local folder
instead of downloading over HTTP. For each requested init it copies:
 - forecast_possibility_heatmap_*_{init}.json  -> CASE_.../possibilities/
 - forecast_percentile_scenarios_*_{init}.json -> CASE_.../percentiles/
 - forecast_exceedance_probabilities_*_{init}.json -> CASE_.../probs/
 - forecast_clustering_summary_{init}.json      -> CASE_.../

Usage (from repo root):
    python scripts/sync_case_from_local.py --init 2025121518 \
        --source /path/to/json/forecasts --history 5
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path
from typing import Dict, List

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


def gather_matches(source: Path, init_str: str) -> Dict[str, List[Path]]:
    """Collect local JSON files for a given init."""
    groups: Dict[str, List[Path]] = {
        "possibilities": [], "percentiles": [], "probs": [], "weather": [], "clustering": []
    }
    for path in source.glob(f"*{init_str}.json"):
        name = path.name
        if name.startswith("forecast_possibility_heatmap_"):
            groups["possibilities"].append(path)
        elif name.startswith("forecast_percentile_scenarios_"):
            groups["percentiles"].append(path)
        elif name.startswith("forecast_exceedance_probabilities"):
            groups["probs"].append(path)
        elif name.startswith("forecast_gefs_weather_"):
            groups["weather"].append(path)
        elif name.startswith("forecast_clustering_summary_"):
            groups["clustering"].append(path)
    return groups


def copy_group(files: List[Path], dest_dir: Path, init_str: str, group: str) -> int:
    dest_dir.mkdir(parents=True, exist_ok=True)
    created = 0
    for src in files:
        # When multiple probability files exist, prefer the canonical name
        if group == "probs" and src.name != f"forecast_exceedance_probabilities_{init_str}.json":
            # Only keep non-standard filenames if the canonical file is missing
            canonical = dest_dir / f"forecast_exceedance_probabilities_{init_str}.json"
            if canonical.exists():
                continue
        dest = dest_dir / src.name
        if dest.exists():
            continue
        shutil.copy2(src, dest)
        created += 1
    return created


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sync CASE directories from a local forecast JSON folder."
    )
    parser.add_argument(
        "--init",
        required=True,
        help="Init time as YYYYMMDDHH or YYYYMMDD_HHMMZ",
    )
    parser.add_argument(
        "--history",
        type=int,
        default=5,
        help="Number of 6-hour inits (current + past) to ensure exist (default 5).",
    )
    parser.add_argument(
        "--source",
        required=True,
        type=str,
        help="Local directory containing forecast JSON files (flat).",
    )
    args = parser.parse_args()

    source_dir = Path(args.source).expanduser().resolve()
    if not source_dir.exists():
        raise SystemExit(f"Source directory not found: {source_dir}")

    data_root = REPO_ROOT / "data" / "json_tests"
    data_root.mkdir(parents=True, exist_ok=True)

    norm_init = parse_init(args.init)

    from datetime import datetime, timedelta

    init_dt = datetime.strptime(norm_init, "%Y%m%d_%H%MZ")
    history_inits = []
    for i in range(max(1, args.history)):
        dt = init_dt - timedelta(hours=6 * i)
        history_inits.append(dt.strftime("%Y%m%d_%H%MZ"))

    print(f"Source: {source_dir}")
    print(f"Target root: {data_root}")
    print(f"Ensuring {len(history_inits)} init(s): {', '.join(history_inits)}")

    for init_str in history_inits:
        case_root = case_root_for_init(data_root, init_str)
        case_root.mkdir(parents=True, exist_ok=True)

        groups = gather_matches(source_dir, init_str)
        if not any(groups.values()):
            print(f"  Warning: no local files matched {init_str}; skipping CASE {case_root.name}")
            continue

        print(f"  Populating {case_root.name} ...")
        for group_name, files in groups.items():
            if not files:
                print(f"    - {group_name}: no files found locally")
                continue
            if group_name == "clustering":
                dest_dir = case_root
            else:
                dest_dir = case_root / group_name
            new_files = copy_group(files, dest_dir, init_str, group_name)
            print(
                f"    - {group_name}: ensured {len(files)} file(s) "
                f"(copied {new_files}, skipped {len(files) - new_files})"
            )

    print("Done syncing CASE directories from local source.")


if __name__ == "__main__":
    main()
