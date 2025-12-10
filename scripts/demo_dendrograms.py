#!/usr/bin/env python3
"""
Generate dendrograms for Clyfar ensemble clustering (percentiles + possibilities).

For a given CASE_YYYYMMDD_HHMMZ directory under data/json_tests/, this script:
 - Loads per-member percentile JSONs and builds feature vectors (p50 + p90 across time)
 - Loads per-member possibility JSONs and builds feature vectors (elevated+extreme, extreme)
 - Groups identical feature vectors (e.g., members with all-background behaviour) so they
   appear as a single leaf with a bundled label
 - Plots Ward hierarchical dendrograms for both feature spaces
 - Saves PNGs under:
     CASE_.../figs/dendrograms/percentiles/dendrogram_percentiles_YYYYMMDD_HHMMZ.png
     CASE_.../figs/dendrograms/possibilities/dendrogram_possibility_YYYYMMDD_HHMMZ.png

Usage (from repo root):
    MPLCONFIGDIR=.mplconfig python scripts/demo_dendrograms.py 2025120412
    # or
    MPLCONFIGDIR=.mplconfig python scripts/demo_dendrograms.py 20251204_1200Z
"""

from __future__ import annotations

import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib.pyplot as plt
import numpy as np
from scipy.cluster.hierarchy import dendrogram, linkage
from scipy.spatial.distance import pdist

# Ensure repo root is on sys.path
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from viz.forecast_plots import ForecastPlotter  # type: ignore


def parse_init(init: str) -> str:
    """
    Normalise init string to 'YYYYMMDD_HHMMZ'.

    Accepts either 'YYYYMMDD_HHMMZ' or 'YYYYMMDDHH'.
    """
    init = init.strip()
    if "_" in init and init.endswith("Z"):
        return init
    if len(init) == 10 and init.isdigit():
        date = init[:8]
        hour = init[8:]
        hhmm = hour.ljust(4, "0")
        return f"{date}_{hhmm}Z"
    raise ValueError(f"Unrecognised init format for dendrograms: {init}")


def case_root_for_init(base: Path, norm_init: str) -> Path:
    """Return CASE_YYYYMMDD_HHMMZ directory for a normalised init."""
    date, hhmmz = norm_init.split("_")
    hhmm = hhmmz.replace("Z", "")
    case_id = f"CASE_{date}_{hhmm}Z"
    return base / case_id


def group_identical_vectors(X: np.ndarray, labels: List[str]) -> Tuple[np.ndarray, List[str]]:
    """
    Group identical feature vectors.

    Returns:
        X_unique: unique rows from X
        grouped_labels: labels describing each unique row, bundling duplicates
    """
    key_to_indices: Dict[bytes, List[int]] = defaultdict(list)
    for i, row in enumerate(X):
        key = row.tobytes()
        key_to_indices[key].append(i)

    X_unique_list: List[np.ndarray] = []
    grouped_labels: List[str] = []
    for key, idxs in key_to_indices.items():
        X_unique_list.append(X[idxs[0]])
        members = [labels[i] for i in idxs]
        if len(members) == 1:
            grouped_labels.append(members[0])
        else:
            grouped_labels.append(f"{members[0]} (+{len(members) - 1} more)")

    X_unique = np.vstack(X_unique_list)
    return X_unique, grouped_labels


def build_percentile_features(
    percentiles_root: Path, norm_init: str, plotter: ForecastPlotter
) -> Tuple[np.ndarray, List[str]]:
    """Load percentile_scenarios JSONs and create feature matrix p50+p90 across time."""
    member_percentiles: Dict[str, "np.ndarray"] = {}
    dates = None
    pattern = f"forecast_percentile_scenarios_*_{norm_init}.json"
    for path in sorted(percentiles_root.glob(pattern)):
        member = path.stem.split("_")[3]
        df = plotter.load_percentiles(path)
        if dates is None:
            dates = df.index
        member_percentiles[member] = df

    if not member_percentiles:
        raise SystemExit(f"No percentile_scenarios files found for {norm_init} in {percentiles_root}")

    # Align and build features
    members = sorted(member_percentiles.keys())
    X_list = []
    for m in members:
        df = member_percentiles[m]
        df = df.reindex(dates)
        p50 = df["p50"].to_numpy()
        p90 = df["p90"].to_numpy()
        vec = np.concatenate([p50, p90])
        X_list.append(vec)
    X = np.vstack(X_list)
    return X, members


def build_possibility_features(
    poss_root: Path, norm_init: str, plotter: ForecastPlotter
) -> Tuple[np.ndarray, List[str]]:
    """Load possibility_heatmap JSONs and create feature matrix (elevated+extreme, extreme)."""
    member_poss: Dict[str, "np.ndarray"] = {}
    dates = None
    pattern = f"forecast_possibility_heatmap_*_{norm_init}.json"
    for path in sorted(poss_root.glob(pattern)):
        member = path.stem.split("_")[3]
        df, _ = plotter.load_possibility(path)
        if dates is None:
            dates = df.index
        member_poss[member] = df

    if not member_poss:
        raise SystemExit(f"No possibility_heatmap files found for {norm_init} in {poss_root}")

    members = sorted(member_poss.keys())
    X_list = []
    for m in members:
        df = member_poss[m].reindex(dates)
        high = (df["elevated"] + df["extreme"]).to_numpy()
        extreme = df["extreme"].to_numpy()
        high = np.nan_to_num(high, nan=0.0)
        extreme = np.nan_to_num(extreme, nan=0.0)
        vec = np.concatenate([high, extreme])
        X_list.append(vec)
    X = np.vstack(X_list)
    return X, members


def plot_dendrogram(X: np.ndarray, labels: List[str], title: str, out_path: Path) -> None:
    """Helper to plot and save a dendrogram given features and labels."""
    if X.shape[0] < 2:
        print(f"Not enough unique members to plot dendrogram for {title}")
        return

    # Standardise by feature
    X_std = (X - X.mean(axis=0)) / (X.std(axis=0) + 1e-6)
    Z = linkage(X_std, method="ward")

    fig, ax = plt.subplots(figsize=(10, 4))
    dendrogram(Z, labels=labels, leaf_rotation=90, leaf_font_size=8, ax=ax)
    ax.set_title(title)
    ax.set_ylabel("Distance")
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote dendrogram to {out_path}")


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate dendrograms for Clyfar percentile and possibility clustering."
    )
    parser.add_argument(
        "init",
        help="Init time as YYYYMMDDHH or YYYYMMDD_HHMMZ (e.g. 2025120412 or 20251204_1200Z)",
    )
    args = parser.parse_args()

    data_root = REPO_ROOT / "data" / "json_tests"
    if not data_root.exists():
        raise SystemExit(f"Data directory not found: {data_root}")

    norm_init = parse_init(args.init)
    case_root = case_root_for_init(data_root, norm_init)
    if not case_root.exists():
        raise SystemExit(f"Case directory not found: {case_root}")

    print(f"Using init: {norm_init}")
    print(f"Case root: {case_root}")

    plotter = ForecastPlotter()

    # Percentiles dendrogram
    percentiles_root = case_root / "percentiles"
    if percentiles_root.exists():
        try:
            Xp, members_p = build_percentile_features(percentiles_root, norm_init, plotter)
            Xp_unique, labels_p = group_identical_vectors(Xp, members_p)
            out_p = case_root / "figs" / "dendrograms" / "percentiles" / f"dendrogram_percentiles_{norm_init}.png"
            plot_dendrogram(Xp_unique, labels_p, f"Percentile-based clustering · {norm_init}", out_p)
        except SystemExit as e:
            print(e)
    else:
        print(f"No percentiles directory found at {percentiles_root}, skipping percentile dendrogram.")

    # Possibility dendrogram
    poss_root = case_root / "possibilities"
    if poss_root.exists():
        try:
            Xq, members_q = build_possibility_features(poss_root, norm_init, plotter)
            Xq_unique, labels_q = group_identical_vectors(Xq, members_q)
            out_q = case_root / "figs" / "dendrograms" / "possibilities" / f"dendrogram_possibility_{norm_init}.png"
            plot_dendrogram(Xq_unique, labels_q, f"Possibility-based clustering · {norm_init}", out_q)
        except SystemExit as e:
            print(e)
    else:
        print(f"No possibilities directory found at {poss_root}, skipping possibility dendrogram.")


if __name__ == "__main__":
    if "MPLCONFIGDIR" not in os.environ:
        os.environ["MPLCONFIGDIR"] = ".mplconfig"
    main()

