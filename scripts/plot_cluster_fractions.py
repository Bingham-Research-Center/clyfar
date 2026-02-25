#!/usr/bin/env python3
"""
Plot cluster fractions from forecast_clustering_summary JSON.

Usage:
    python scripts/plot_cluster_fractions.py 20260209_1800Z
    python scripts/plot_cluster_fractions.py 2026020918
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Patch

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from viz.forecast_plots import CATEGORY_COLORS


def parse_init(init: str) -> str:
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
    date, hhmmz = norm_init.split("_")
    hhmm = hhmmz.replace("Z", "")
    return base / f"CASE_{date}_{hhmm}Z"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Plot cluster fraction chart for a CASE directory."
    )
    parser.add_argument(
        "init",
        help="Init time as YYYYMMDDHH or YYYYMMDD_HHMMZ",
    )
    args = parser.parse_args()

    norm_init = parse_init(args.init)
    case_root = case_root_for_init(REPO_ROOT / "data" / "json_tests", norm_init)
    if not case_root.exists():
        raise SystemExit(f"Case directory not found: {case_root}")

    summary_path = case_root / f"forecast_clustering_summary_{norm_init}.json"
    if not summary_path.exists():
        raise SystemExit(f"Clustering summary not found: {summary_path}")

    summary = json.loads(summary_path.read_text())
    clusters = summary.get("clusters", [])
    if not clusters:
        raise SystemExit("No clusters found in summary.")

    labels = []
    values = []
    colors = []
    for cluster in clusters:
        cid = cluster.get("id", 0)
        kind = cluster.get("kind", "scenario")
        dominant = cluster.get("clyfar_ozone", {}).get("dominant_category", "background")
        fraction = float(cluster.get("fraction", 0.0) or 0.0)
        label = "Null" if kind == "null" else f"Scenario {cid}"
        labels.append(label)
        values.append(fraction)
        colors.append(CATEGORY_COLORS.get(dominant, "#9ca3af"))

    fig, ax = plt.subplots(figsize=(6.5, 3.2))
    bars = ax.bar(labels, values, color=colors, edgecolor="#111827")
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Fraction of members")
    ax.set_title(f"Cluster fractions · {norm_init}")

    for bar, cluster in zip(bars, clusters):
        dominant = cluster.get("clyfar_ozone", {}).get("dominant_category", "background")
        risk = cluster.get("clyfar_ozone", {}).get("risk_level", "unknown")
        pct = int(round(100 * float(cluster.get("fraction", 0.0) or 0.0)))
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.02,
            f"{pct}%\n{dominant}/{risk}",
            ha="center",
            va="bottom",
            fontsize=8,
        )

    legend_items = []
    for cat in ("background", "moderate", "elevated", "extreme"):
        if cat in CATEGORY_COLORS:
            legend_items.append(Patch(color=CATEGORY_COLORS[cat], label=cat))
    ax.legend(
        handles=legend_items,
        title="Dominant category",
        fontsize=8,
        title_fontsize=8,
        loc="upper right",
    )

    out_path = case_root / "figs" / f"cluster_fractions_{norm_init}.png"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)
    print(out_path)


if __name__ == "__main__":
    main()
