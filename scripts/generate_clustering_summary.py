#!/usr/bin/env python3
"""
Generate a JSON summary of ensemble clustering showing GEFS↔Clyfar linkage.

Uses a deterministic two-stage algorithm:
1) Identify a null/background-dominated subset first.
2) Cluster the non-null residual with weighted time-block distances.

Usage:
    python scripts/generate_clustering_summary.py 2026010212
    python scripts/generate_clustering_summary.py --case-dir data/json_tests/CASE_20260102_1200Z

Output:
    {case_dir}/forecast_clustering_summary_{init}.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, Sequence

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from utils.scenario_clustering import build_clustering_summary
from viz.forecast_plots import ForecastPlotter


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


def _to_weather_payload(raw: Dict[str, Sequence[float]]) -> Dict[str, Sequence[float]]:
    """Extract snow/wind lists from a weather payload."""
    snow = raw.get("snow", []) if isinstance(raw, dict) else []
    wind = raw.get("wind", []) if isinstance(raw, dict) else []
    return {
        "snow": list(snow) if isinstance(snow, list) else [],
        "wind": list(wind) if isinstance(wind, list) else [],
    }


def _daily_weather_from_hourly(payload: Dict[str, Sequence[float]], n_days: int) -> Dict[str, Sequence[float]]:
    """Downsample hourly weather arrays to daily medians for cluster characterization."""
    out: Dict[str, Sequence[float]] = {"snow": [], "wind": []}
    for key in ("snow", "wind"):
        arr = payload.get(key, [])
        if not isinstance(arr, list) or not arr:
            out[key] = []
            continue

        # Expected GEFS horizon is hourly. Use 24-hour bins for day-level summaries.
        chunks = []
        for i in range(0, len(arr), 24):
            chunks.append(arr[i:i + 24])

        medians = []
        for chunk in chunks[:n_days]:
            vals = [float(v) for v in chunk if v is not None]
            if vals:
                medians.append(float(pd.Series(vals).median()))
            else:
                medians.append(float("nan"))
        out[key] = medians
    return out


def load_case_inputs(case_root: Path, norm_init: str) -> tuple[
    Dict[str, pd.DataFrame],
    Dict[str, pd.DataFrame],
    Dict[str, Dict[str, Sequence[float]]],
    Dict[str, np.ndarray],
]:
    """Load possibility, percentile, and weather data from a CASE directory."""
    poss_root = case_root / "possibilities"
    pct_root = case_root / "percentiles"
    weather_root = case_root / "weather"

    if not poss_root.exists():
        raise SystemExit(f"Possibilities directory not found: {poss_root}")
    if not pct_root.exists():
        raise SystemExit(f"Percentiles directory not found: {pct_root}")

    plotter = ForecastPlotter()

    member_poss: Dict[str, pd.DataFrame] = {}
    member_missing_masks: Dict[str, np.ndarray] = {}
    for path in sorted(poss_root.glob(f"forecast_possibility_heatmap_*_{norm_init}.json")):
        parts = path.stem.split("_")
        member = parts[3]  # clyfar000
        df, missing_mask = plotter.load_possibility(path)
        member_poss[member] = df[["background", "moderate", "elevated", "extreme"]]
        member_missing_masks[member] = np.asarray(missing_mask, dtype=bool)

    if not member_poss:
        raise SystemExit(f"No possibility_heatmap files found for {norm_init}")

    member_percentiles: Dict[str, pd.DataFrame] = {}
    for path in sorted(pct_root.glob(f"forecast_percentile_scenarios_*_{norm_init}.json")):
        parts = path.stem.split("_")
        member = parts[3]  # clyfar000
        df = plotter.load_percentiles(path)
        member_percentiles[member] = df[["p50", "p90"]]

    if not member_percentiles:
        raise SystemExit(f"No percentile_scenarios files found for {norm_init}")

    # Weather characterization is optional in clustering logic.
    weather_data: Dict[str, Dict[str, Sequence[float]]] = {}
    n_days = len(next(iter(member_poss.values())).index)
    if weather_root.exists():
        for path in sorted(weather_root.glob(f"forecast_gefs_weather_*_{norm_init}.json")):
            parts = path.stem.split("_")
            member = parts[3]  # clyfar000
            try:
                with open(path) as f:
                    payload = json.load(f)
                raw_weather = payload.get("weather", {})
                weather_data[member] = _daily_weather_from_hourly(
                    _to_weather_payload(raw_weather),
                    n_days=n_days,
                )
            except Exception:
                # Weather characterization is best-effort only.
                continue

    return member_poss, member_percentiles, weather_data, member_missing_masks


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate clustering summary JSON for LLM context."
    )
    parser.add_argument(
        "init",
        nargs="?",
        help="Init time as YYYYMMDDHH or YYYYMMDD_HHMMZ",
    )
    parser.add_argument(
        "--case-dir",
        type=str,
        help="Direct path to CASE directory (alternative to init)",
    )
    args = parser.parse_args()

    if args.case_dir:
        case_root = Path(args.case_dir).resolve()
        norm_init = case_root.name.replace("CASE_", "")
    elif args.init:
        data_root = REPO_ROOT / "data" / "json_tests"
        norm_init = parse_init(args.init)
        case_root = case_root_for_init(data_root, norm_init)
    else:
        raise SystemExit("Provide either init time or --case-dir")

    if not case_root.exists():
        raise SystemExit(f"Case directory not found: {case_root}")

    print(f"Generating clustering summary for: {norm_init}")

    member_poss, member_percentiles, weather_data, member_missing_masks = load_case_inputs(
        case_root,
        norm_init,
    )
    summary = build_clustering_summary(
        norm_init=norm_init,
        member_poss=member_poss,
        member_percentiles=member_percentiles,
        weather_data=weather_data,
        member_missing_masks=member_missing_masks,
    )

    out_path = case_root / f"forecast_clustering_summary_{norm_init}.json"
    with open(out_path, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"Wrote clustering summary to: {out_path}")
    print(f"  {summary['n_clusters']} clusters, representatives: {summary['representative_members']}")


if __name__ == "__main__":
    if "MPLCONFIGDIR" not in os.environ:
        os.environ["MPLCONFIGDIR"] = ".mplconfig"
    main()
