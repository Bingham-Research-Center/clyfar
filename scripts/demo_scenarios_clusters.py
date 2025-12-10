#!/usr/bin/env python3
"""
Demo scenario clustering for Clyfar ensemble members.

Uses local JSON test data in data/json_tests to:
 - Build simple feature vectors from percentile_scenarios (p50/p90)
 - Cluster members (hierarchical, Ward) over a 5-day window
 - Identify a medoid member per cluster as the representative scenario
 - Plot union spaghetti envelopes per cluster for brainstorming

Usage (from repo root):
    MPLCONFIGDIR=.mplconfig python scripts/demo_scenarios_clusters.py

Optional:
    MPLCONFIGDIR=.mplconfig python scripts/demo_scenarios_clusters.py 20251207_1200Z
"""

from __future__ import annotations

import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib.pyplot as plt
import numpy as np
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import pdist, squareform

# Ensure repo root is on sys.path so `viz` can be imported when this
# script is executed from the scripts/ directory.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from viz.forecast_plots import ForecastPlotter


def find_available_inits(root: Path) -> List[str]:
    """Return sorted list of init strings present in percentile JSON filenames."""
    inits = set()
    for path in root.glob("forecast_percentile_scenarios_*_*.json"):
        inits.add(path.stem.split("_")[-1])
    return sorted(inits)


def pick_most_variable_init(root: Path, inits: List[str]) -> str:
    """Pick the init with largest spread in p90 across members/days."""
    plotter = ForecastPlotter()
    scores = {}
    for init in inits:
        values = []
        for path in root.glob(f"forecast_percentile_scenarios_*_{init}.json"):
            df = plotter.load_percentiles(path)
            values.extend(df["p90"].tolist())
        if not values:
            scores[init] = -1.0
        else:
            arr = np.array(values)
            scores[init] = float(arr.std())
    return max(scores, key=scores.get)


def build_features_for_window(
    member_percentiles: Dict[str, "np.ndarray"], window: slice
) -> Tuple[np.ndarray, List[str]]:
    """Create feature matrix: members × (p50_window + p90_window)."""
    members = sorted(member_percentiles.keys())
    X_list = []
    for m in members:
        df = member_percentiles[m]
        p50 = df["p50"].iloc[window].to_numpy()
        p90 = df["p90"].iloc[window].to_numpy()
        vec = np.concatenate([p50, p90])
        X_list.append(vec)
    X = np.vstack(X_list)
    return X, members


def cluster_members(X: np.ndarray, k: int) -> np.ndarray:
    """Run Ward hierarchical clustering and cut into k clusters."""
    Z = linkage(X, method="ward")
    labels = fcluster(Z, k, criterion="maxclust")
    return labels


def find_medoids(X: np.ndarray, labels: np.ndarray) -> Dict[int, int]:
    """Return medoid index per cluster (index into X)."""
    medoids: Dict[int, int] = {}
    dist_matrix = squareform(pdist(X))
    for cluster_id in np.unique(labels):
        idx = np.where(labels == cluster_id)[0]
        sub = dist_matrix[np.ix_(idx, idx)]
        # Sum of distances to all others; pick minimum
        sums = sub.sum(axis=1)
        medoids[cluster_id] = idx[int(np.argmin(sums))]
    return medoids


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    data_root = repo_root / "data" / "json_tests"
    if not data_root.exists():
        raise SystemExit(f"Data directory not found: {data_root}")

    inits = find_available_inits(data_root)
    if not inits:
        raise SystemExit("No percentile_scenarios JSON files found in data/json_tests")

    if len(sys.argv) > 1:
        init = sys.argv[1]
    else:
        # Default to the init with largest spread in p90 across members
        init = pick_most_variable_init(data_root, inits)

    out_dir = data_root / "brainstorm_scenarios"
    out_dir.mkdir(exist_ok=True)

    print(f"Using init: {init}")
    print(f"Writing plots to: {out_dir}")

    plotter = ForecastPlotter()

    # Load all members' percentiles
    member_percentiles: Dict[str, "np.ndarray"] = {}
    dates = None
    for path in sorted(data_root.glob(f"forecast_percentile_scenarios_*_{init}.json")):
        member = path.stem.split("_")[3]
        df = plotter.load_percentiles(path)
        if dates is None:
            dates = df.index
        member_percentiles[member] = df

    if not member_percentiles:
        raise SystemExit(f"No percentile_scenarios files found for {init}")

    # Use full horizon as the window for clustering
    window = slice(0, len(dates))
    X, members = build_features_for_window(member_percentiles, window)

    # Standardize features (p50 and p90) to comparable scale
    X = (X - X.mean(axis=0)) / (X.std(axis=0) + 1e-6)

    # Simple 3-cluster solution to produce a dominant scenario plus tail scenarios
    k = 3
    labels = cluster_members(X, k)
    medoids = find_medoids(X, labels)

    # Scenario summary
    cluster_members_map: Dict[int, List[str]] = defaultdict(list)
    for m, label in zip(members, labels):
        cluster_members_map[label].append(m)

    print("Scenario clusters (full forecast horizon):")
    for cid in sorted(cluster_members_map):
        members_c = cluster_members_map[cid]
        frac = len(members_c) / float(len(members))
        medoid_idx = medoids[cid]
        medoid_member = members[medoid_idx]
        print(
            f"  Scenario {cid}: {len(members_c)}/{len(members)} members "
            f"({frac:.0%}), medoid={medoid_member}"
        )

    # Plot union spaghetti envelope for each cluster separately
    for cid in sorted(cluster_members_map):
        subset = {m: member_percentiles[m] for m in cluster_members_map[cid]}
        fig, ax = plotter.plot_percentile_spaghetti_union(
            subset,
            title=f"Scenario {cid} union envelope (p10–p90) · {init}",
        )
        fig.savefig(out_dir / f"scenario_{cid}_union_{init}.png", bbox_inches="tight")
        plt.close(fig)

    # Also plot medoid fan chart for each scenario
    for cid in sorted(cluster_members_map):
        medoid_member = members[medoids[cid]]
        df = member_percentiles[medoid_member]
        fig, ax = plotter.plot_percentile_fan(
            df,
            member_label=medoid_member,
            title=f"Scenario {cid} medoid percentiles · {init}",
        )
        fig.savefig(out_dir / f"scenario_{cid}_medoid_{medoid_member}_{init}.png", bbox_inches="tight")
        plt.close(fig)

    print("Done.")


if __name__ == "__main__":
    if "MPLCONFIGDIR" not in os.environ:
        os.environ["MPLCONFIGDIR"] = ".mplconfig"
    main()
