#!/usr/bin/env python3
"""
Generate daily-max Clyfar heatmaps from exported possibility JSON.

This reuses the existing plotting style from viz/possibility_funcs.plot_dailymax_heatmap
to create one PNG per ensemble member for a given forecast init.

Case-aware layout:
    data/json_tests/CASE_YYYYMMDD_HHMMZ/possibilities/*.json  ->  figs/possibility/heatmaps/

Fallback (legacy):
    data/json_tests/*.json -> data/json_tests/brainstorm_heatmaps/

Usage (from repo root):
    MPLCONFIGDIR=.mplconfig python scripts/demo_heatmaps_from_json.py 2025120412
    # or
    MPLCONFIGDIR=.mplconfig python scripts/demo_heatmaps_from_json.py 20251204_1200Z
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

# Ensure repo root is on sys.path so `viz` can be imported when this
# script is executed from the scripts/ directory.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Suppress interactive popups; we only save figures to disk here.
plt.show = lambda *_, **__: None  # type: ignore

from viz.possibility_funcs import plot_dailymax_heatmap  # type: ignore


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
    raise ValueError(f"Unrecognised init format for heatmaps: {init}")


def case_root_for_init(base: Path, norm_init: str) -> Path:
    """Return CASE_YYYYMMDD_HHMMZ directory for a normalised init."""
    date, hhmmz = norm_init.split("_")
    hhmm = hhmmz.replace("Z", "")
    case_id = f"CASE_{date}_{hhmm}Z"
    return base / case_id


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate daily-max Clyfar heatmaps from possibility JSON."
    )
    parser.add_argument(
        "init",
        help="Init time as YYYYMMDDHH or YYYYMMDD_HHMMZ (e.g. 2025120412 or 20251204_1200Z)",
    )
    args = parser.parse_args()

    repo_root = REPO_ROOT
    data_root = repo_root / "data" / "json_tests"
    if not data_root.exists():
        raise SystemExit(f"Data directory not found: {data_root}")

    norm_init = parse_init(args.init)

    # Prefer CASE layout
    case_root = case_root_for_init(data_root, norm_init)
    case_poss = case_root / "possibilities"
    if case_poss.exists():
        poss_root = case_poss
        out_dir = case_root / "figs" / "possibility" / "heatmaps"
    else:
        poss_root = data_root
        out_dir = data_root / "brainstorm_heatmaps"

    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Using init: {norm_init}")
    print(f"Reading possibility JSONs from: {poss_root}")
    print(f"Writing heatmaps to: {out_dir}")

    pattern = f"forecast_possibility_heatmap_*_{norm_init}.json"
    files = sorted(poss_root.glob(pattern))
    if not files:
        raise SystemExit(f"No possibility heatmap JSONs matching {pattern} in {poss_root}")

    for path in files:
        with path.open() as f:
            payload = json.load(f)
        dates = pd.to_datetime(payload["forecast_dates"])
        heatmap = payload["heatmap"]

        # Ensure category order
        categories = ["background", "moderate", "elevated", "extreme"]
        df = pd.DataFrame({cat: heatmap.get(cat, []) for cat in categories}, index=dates)

        # Plot and save using existing styling
        fig, ax = plot_dailymax_heatmap(df)

        member = path.stem.split("_")[3]  # forecast_possibility_heatmap_clyfarXXX_...
        fname = f"heatmap_dailymax_{member}_{norm_init}.png"
        fig.savefig(out_dir / fname, bbox_inches="tight")
        plt.close(fig)

    print(f"Generated {len(files)} heatmaps.")


if __name__ == "__main__":
    if "MPLCONFIGDIR" not in os.environ:
        os.environ["MPLCONFIGDIR"] = ".mplconfig"
    main()
