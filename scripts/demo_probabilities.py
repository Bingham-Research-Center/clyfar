#!/usr/bin/env python3
"""
Demo visualizations for Clyfar exceedance probabilities.

Uses local JSON test data in data/json_tests (exceedance_probabilities) to
explore:
 - Multi-threshold probability time series
 - Bar chart of "days with meaningful risk" per threshold
 - Threshold × day heatmap of exceedance probability

Usage (from repo root):
    MPLCONFIGDIR=.mplconfig python scripts/demo_probabilities.py

Optional:
    MPLCONFIGDIR=.mplconfig python scripts/demo_probabilities.py 20251207_1200Z
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

# Ensure repo root is on sys.path so `viz` can be imported when this
# script is executed from the scripts/ directory.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from viz.forecast_plots import ForecastPlotter


def find_available_inits(root: Path):
    inits = set()
    for path in root.glob("forecast_exceedance_probabilities_*.json"):
        init = path.stem.split("_")[-1]
        inits.add(init)
    return sorted(inits)


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    data_root = repo_root / "data" / "json_tests"
    if not data_root.exists():
        raise SystemExit(f"Data directory not found: {data_root}")

    inits = find_available_inits(data_root)
    if not inits:
        raise SystemExit("No exceedance_probabilities JSON files found in data/json_tests")

    if len(sys.argv) > 1:
        init = sys.argv[1]
    else:
        # Default to latest full init (assumes filenames include date)
        init = inits[-1]

    out_dir = data_root / "brainstorm_probabilities"
    out_dir.mkdir(exist_ok=True)

    print(f"Using init: {init}")
    print(f"Writing plots to: {out_dir}")

    plotter = ForecastPlotter()
    matches = sorted(data_root.glob(f"forecast_exceedance_probabilities_*_{init}.json"))
    if not matches:
        raise SystemExit(
            f"Exceedance file not found for init {init} in {data_root} "
            "(expected pattern forecast_exceedance_probabilities_*_{init}.json)"
        )
    path = matches[0]

    df = plotter.load_exceedance(path)
    dates = df.index
    thresholds = list(df.columns)

    # 1) Multi-threshold probability lines
    fig, ax = plotter.plot_exceedance_lines(df, title=f"Exceedance probabilities · {init}")
    fig.savefig(out_dir / f"exceedance_lines_{init}.png", bbox_inches="tight")
    plt.close(fig)

    # 2) Bar chart: days with p>0.5 and p>0.2 per threshold
    fig, ax = plt.subplots(figsize=(8, 4))
    idx = np.arange(len(thresholds))
    width = 0.35
    gt_20 = [(df[t] > 0.2).sum() for t in thresholds]
    gt_50 = [(df[t] > 0.5).sum() for t in thresholds]
    ax.bar(idx - width / 2, gt_20, width, label="p > 0.2")
    ax.bar(idx + width / 2, gt_50, width, label="p > 0.5")
    ax.set_xticks(idx)
    ax.set_xticklabels([f">{t} ppb" for t in thresholds])
    ax.set_ylabel("Number of days")
    ax.set_title(f"Days with meaningful exceedance risk · {init}")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_dir / f"exceedance_days_{init}.png", bbox_inches="tight")
    plt.close(fig)

    # 3) Threshold × day heatmap
    fig, ax = plt.subplots(figsize=(10, 3.5))
    im = ax.imshow(df.values.T, aspect="auto", cmap="Reds", vmin=0, vmax=1)
    ax.set_yticks(range(len(thresholds)))
    ax.set_yticklabels([f">{t} ppb" for t in thresholds])
    ax.set_xticks(range(len(dates)))
    ax.set_xticklabels([d.strftime("%d %b") for d in dates], rotation=45, ha="right")
    ax.set_title(f"Exceedance probability heatmap · {init}")
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("Probability")
    fig.tight_layout()
    fig.savefig(out_dir / f"exceedance_heatmap_{init}.png", bbox_inches="tight")
    plt.close(fig)

    print("Done.")


if __name__ == "__main__":
    if "MPLCONFIGDIR" not in os.environ:
        os.environ["MPLCONFIGDIR"] = ".mplconfig"
    main()
