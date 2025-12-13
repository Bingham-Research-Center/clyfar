#!/usr/bin/env python3
"""
Demo visualizations for Clyfar forecast quantities (ppb).

Uses local JSON test data in data/json_tests (percentile_scenarios) to
summarize the ensemble in a few ways:
 - Boxplots of daily p50 across members
 - Ensemble fan (p50 across members) over time
 - Histogram of max p90 per member

Usage (from repo root):
    MPLCONFIGDIR=.mplconfig python scripts/demo_quantities.py

Optional:
    MPLCONFIGDIR=.mplconfig python scripts/demo_quantities.py 20251207_1200Z
"""

from __future__ import annotations

import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List

import matplotlib.pyplot as plt
import numpy as np

# Ensure repo root is on sys.path so `viz` can be imported when this
# script is executed from the scripts/ directory.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from viz.forecast_plots import ForecastPlotter


def find_available_inits(root: Path) -> List[str]:
    """Return sorted list of init strings present in percentile JSON filenames."""
    inits = set()
    for path in root.rglob("forecast_percentile_scenarios_*_*.json"):
        parts = path.stem.split("_")
        if len(parts) < 2:
            continue
        init = f"{parts[-2]}_{parts[-1]}"
        inits.add(init)
    return sorted(inits)


def parse_init(init: str) -> str:
    """
    Normalise init string to 'YYYYMMDD_HHMMZ'.

    Accepts either 'YYYYMMDD_HHMMZ' or 'YYYYMMDDHH' (no Z, no underscore).
    """
    init = init.strip()
    if "_" in init and init.endswith("Z"):
        return init
    if len(init) == 10 and init.isdigit():
        date = init[:8]
        hour = init[8:]  # HH
        hhmm = hour.ljust(4, "0")  # HH -> HH00
        return f"{date}_{hhmm}Z"
    raise ValueError(f"Unrecognised init format: {init}")


def case_root_for_init(base: Path, norm_init: str) -> Path:
    """
    Return case root for a given normalised init 'YYYYMMDD_HHMMZ':
    CASE_YYYYMMDD_HHMMZ under base.
    """
    date, hhmmz = norm_init.split("_")
    hhmm = hhmmz.replace("Z", "")
    case_id = f"CASE_{date}_{hhmm}Z"
    return base / case_id


def pick_most_variable_init(root: Path, inits: List[str]) -> str:
    """Pick the init with largest spread in p90 across members/days."""
    plotter = ForecastPlotter()
    scores = {}
    for init in inits:
        values: List[float] = []
        for path in root.rglob(f"forecast_percentile_scenarios_*_{init}.json"):
            df = plotter.load_percentiles(path)
            # Flatten p90 values
            values.extend(df["p90"].tolist())
        if not values:
            scores[init] = -1.0
        else:
            arr = np.array(values)
            scores[init] = float(arr.std())
    # Return init with highest score
    return max(scores, key=scores.get)


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    data_root = repo_root / "data" / "json_tests"
    if not data_root.exists():
        raise SystemExit(f"Data directory not found: {data_root}")

    # If init provided as argument, skip scanning
    if len(sys.argv) > 1:
        init_arg = sys.argv[1]
    else:
        # Auto-detect available inits
        inits = find_available_inits(data_root)
        if not inits:
            raise SystemExit("No percentile_scenarios JSON files found in data/json_tests")
        init_arg = pick_most_variable_init(data_root, inits)

    norm_init = parse_init(init_arg)

    # Prefer new CASE_YYYYMMDDHHZ layout if present
    case_root = case_root_for_init(data_root, norm_init)
    case_percentiles = case_root / "percentiles"
    if case_percentiles.exists():
        percentiles_root = case_percentiles
        out_dir = case_root / "figs" / "quantities"
    else:
        percentiles_root = data_root
        out_dir = data_root / "brainstorm_quantities"

    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Using init: {norm_init}")
    print(f"Writing plots to: {out_dir}")

    plotter = ForecastPlotter()

    # Load per-member percentiles
    member_percentiles: Dict[str, "np.ndarray"] = {}
    dates = None
    for path in sorted(percentiles_root.glob(f"forecast_percentile_scenarios_*_{norm_init}.json")):
        meta_member = path.stem.split("_")[3]
        df = plotter.load_percentiles(path)
        if dates is None:
            dates = df.index
        member_percentiles[meta_member] = df

    if not member_percentiles:
        raise SystemExit(f"No percentile_scenarios files found for {norm_init}")

    # 1) Boxplots of daily p50 across members
    day_p50: Dict[int, List[float]] = defaultdict(list)
    for member, df in member_percentiles.items():
        for i, value in enumerate(df["p50"].tolist()):
            if value is not None:
                day_p50[i].append(value)

    fig, ax = plt.subplots(figsize=(10, 4))
    data = [day_p50[i] for i in sorted(day_p50.keys())]
    ax.boxplot(data, positions=range(len(data)), showfliers=False)
    if dates is not None:
        ax.set_xticks(range(len(data)))
        ax.set_xticklabels([d.strftime("%d %b") for d in dates], rotation=45, ha="right")
    ax.set_ylabel("Ozone (ppb)")
    ax.set_title(f"Daily p50 distribution across members · {norm_init}")
    fig.tight_layout()
    fig.savefig(out_dir / f"boxplot_p50_{norm_init}.png", bbox_inches="tight")
    plt.close(fig)

    # 2) Ensemble fan of p50 across members (per day)
    # Build array: days × members
    all_members = sorted(member_percentiles.keys())
    arr = np.array(
        [[member_percentiles[m]["p50"].iloc[i] for m in all_members] for i in range(len(dates))]
    )
    q10 = np.nanpercentile(arr, 10, axis=1)
    q50 = np.nanpercentile(arr, 50, axis=1)
    q90 = np.nanpercentile(arr, 90, axis=1)

    fig, ax = plt.subplots(figsize=(10, 3.5))
    ax.fill_between(dates, q10, q90, color="#a7f3d0", alpha=0.5, label="ensemble p10–p90 (p50)")
    ax.plot(dates, q50, color="#059669", linewidth=2, label="ensemble median p50")
    ax.set_ylabel("Ozone (ppb)")
    ax.set_title(f"Ensemble p50 fan across members · {norm_init}")
    ax.legend(loc="upper right", fontsize=8)
    fig.tight_layout()
    fig.savefig(out_dir / f"fan_p50_{norm_init}.png", bbox_inches="tight")
    plt.close(fig)

    # 3) Histogram of member max p90
    max_p90 = []
    for member, df in member_percentiles.items():
        max_p90.append(df["p90"].max())
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.hist(max_p90, bins=10, color="#0f62fe", alpha=0.8)
    ax.set_xlabel("Max p90 per member (ppb)")
    ax.set_ylabel("Count")
    ax.set_title(f"Distribution of peak p90 across members · {norm_init}")
    fig.tight_layout()
    fig.savefig(out_dir / f"hist_max_p90_{norm_init}.png", bbox_inches="tight")
    plt.close(fig)

    print("Done.")


if __name__ == "__main__":
    if "MPLCONFIGDIR" not in os.environ:
        os.environ["MPLCONFIGDIR"] = ".mplconfig"
    main()
