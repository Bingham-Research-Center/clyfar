#!/usr/bin/env python3
"""
Demo scenario clustering based on possibility heatmaps (categories) for Clyfar.

Uses local JSON test data in data/json_tests to:
 - Cluster members on elevated+extreme possibilities over the full forecast
 - Summarize three scenarios (large baseline + smaller high-risk tails)
 - For each scenario:
     * Cluster mean category heatmap
     * Fraction of members with high P(elevated+extreme)

Usage (from repo root):
    MPLCONFIGDIR=.mplconfig python scripts/demo_scenarios_possibility.py 0600Z

If no init is given, chooses the init with largest spread in elevated+extreme.
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
    """Return sorted list of init strings present in possibility filenames."""
    inits = set()
    for path in root.rglob("forecast_possibility_heatmap_*_*.json"):
        parts = path.stem.split("_")
        if len(parts) < 2:
            continue
        inits.add(f"{parts[-2]}_{parts[-1]}")
    return sorted(inits)


def parse_init_or_suffix(arg: str) -> tuple[str | None, str]:
    """
    Accept either 'YYYYMMDD_HHMMZ' or 'HHMMZ'.

    Returns (full_init_or_None, suffix).
    """
    arg = arg.strip()
    if "_" in arg and arg.endswith("Z"):
        return arg, arg.split("_")[-1]
    # 10-digit init without underscore: YYYYMMDDHH -> YYYYMMDD_HH00Z
    if len(arg) == 10 and arg.isdigit():
        date = arg[:8]
        hour = arg[8:]
        hhmm = hour.ljust(4, "0")
        full = f"{date}_{hhmm}Z"
        return full, full.split("_")[-1]
    # Fallback: suffix only (e.g. HHMMZ)
    return None, arg


def case_root_for_init(base: Path, norm_init: str) -> Path:
    """Return CASE_YYYYMMDD_HHMMZ directory for a normalised init."""
    date, hhmmz = norm_init.split("_")
    hhmm = hhmmz.replace("Z", "")
    case_id = f"CASE_{date}_{hhmm}Z"
    return base / case_id


def pick_most_variable_init(root: Path, inits: List[str]) -> str:
    """Pick init with largest spread in elevated+extreme across members/days."""
    plotter = ForecastPlotter()
    scores = {}
    for init in inits:
        values = []
        for path in root.rglob(f"forecast_possibility_heatmap_*_{init}.json"):
            df, _ = plotter.load_possibility(path)
            high = (df["elevated"] + df["extreme"]).to_numpy()
            values.extend(high.tolist())
        if not values:
            scores[init] = -1.0
        else:
            arr = np.array(values)
            scores[init] = float(arr.std())
    return max(scores, key=scores.get)


def build_features(
    member_poss: Dict[str, "np.ndarray"], index: "np.ndarray"
) -> Tuple[np.ndarray, List[str]]:
    """Create feature matrix from elevated+extreme over full horizon."""
    members = sorted(member_poss.keys())
    X_list = []
    for m in members:
        df = member_poss[m]
        # ensure aligned
        df = df.reindex(index)
        high = (df["elevated"] + df["extreme"]).to_numpy()
        extreme = df["extreme"].to_numpy()
        # Replace NaNs with 0 for clustering distance calculations
        high = np.nan_to_num(high, nan=0.0)
        extreme = np.nan_to_num(extreme, nan=0.0)
        vec = np.concatenate([high, extreme])
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
        sums = sub.sum(axis=1)
        medoids[cluster_id] = idx[int(np.argmin(sums))]
    return medoids


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    data_root = repo_root / "data" / "json_tests"
    if not data_root.exists():
        raise SystemExit(f"Data directory not found: {data_root}")

    # If init provided as argument, skip scanning
    if len(sys.argv) > 1:
        full_init, suffix = parse_init_or_suffix(sys.argv[1])
    else:
        # Auto-detect available inits
        inits = find_available_inits(data_root)
        if not inits:
            raise SystemExit("No possibility_heatmap JSON files found in data/json_tests")
        # Choose most variable based on full init list and derive suffix
        full_init = pick_most_variable_init(data_root, inits)
        _, suffix = parse_init_or_suffix(full_init)

    # Prefer CASE layout when full init is provided
    if full_init is not None:
        case_root = case_root_for_init(data_root, full_init)
        case_poss = case_root / "possibilities"
        if case_poss.exists():
            poss_root = case_poss
            out_dir = case_root / "figs" / "scenarios_possibility"
        else:
            poss_root = data_root
            out_dir = data_root / "brainstorm_scenarios_possibility"
    else:
        poss_root = data_root
        out_dir = data_root / "brainstorm_scenarios_possibility"

    out_dir.mkdir(parents=True, exist_ok=True)

    label_init = full_init if full_init is not None else suffix
    print(f"Using init: {label_init}")
    print(f"Writing plots to: {out_dir}")

    plotter = ForecastPlotter()

    # Load all members' possibility heatmaps
    member_poss: Dict[str, "np.ndarray"] = {}
    dates = None
    for path in sorted(poss_root.glob(f"forecast_possibility_heatmap_*_{suffix}.json")):
        # pattern: forecast_possibility_heatmap_clyfarXXX_YYYYMMDD_HHMMZ.json
        parts = path.stem.split("_")
        member = parts[3]  # clyfar000
        df, _ = plotter.load_possibility(path)
        if dates is None:
            dates = df.index
        member_poss[member] = df

    if not member_poss:
        raise SystemExit(f"No possibility_heatmap files found for init {label_init}")

    index = dates

    # Build feature matrix and cluster
    X, members = build_features(member_poss, index)
    X = (X - X.mean(axis=0)) / (X.std(axis=0) + 1e-6)
    k = 3
    labels = cluster_members(X, k)
    medoids = find_medoids(X, labels)

    # Scenario summary
    cluster_members_map: Dict[int, List[str]] = defaultdict(list)
    for m, label in zip(members, labels):
        cluster_members_map[label].append(m)

    print("Scenario clusters (possibility-based):")
    for cid in sorted(cluster_members_map):
        members_c = cluster_members_map[cid]
        frac = len(members_c) / float(len(members))
        medoid_idx = medoids[cid]
        medoid_member = members[medoid_idx]
        print(
            f"  Scenario {cid}: {len(members_c)}/{len(members)} members "
            f"({frac:.0%}), medoid={medoid_member}"
        )

    # Plot cluster-level heatmaps and high-risk fractions
    for cid in sorted(cluster_members_map):
        members_c = cluster_members_map[cid]
        subset = {m: member_poss[m] for m in members_c}

        fig, ax = plotter.plot_cluster_mean_possibility_heatmap(
            subset,
            title=f"Scenario {cid} mean possibilities · {label_init}",
        )
        fig.savefig(out_dir / f"scenario_{cid}_mean_heatmap_{label_init}.png", bbox_inches="tight")
        plt.close(fig)

        fig, ax = plotter.plot_cluster_highrisk_fraction(
            subset,
            threshold=0.5,
            title=f"Scenario {cid} high-risk fraction (P(elev+ext)>0.5) · {label_init}",
        )
        fig.savefig(out_dir / f"scenario_{cid}_highrisk_{label_init}.png", bbox_inches="tight")
        plt.close(fig)

    # Scenario membership bar chart
    fig, ax = plt.subplots(figsize=(6, 3))
    cids = sorted(cluster_members_map)
    counts = [len(cluster_members_map[cid]) for cid in cids]
    frac = [c / float(len(members)) for c in counts]
    ax.bar([str(cid) for cid in cids], frac, color="#4b8bbe")
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Fraction of members")
    ax.set_xlabel("Scenario ID")
    ax.set_title(f"Scenario membership fractions · {label_init}")
    fig.tight_layout()
    fig.savefig(out_dir / f"scenario_membership_{label_init}.png", bbox_inches="tight")
    plt.close(fig)

    print("Done.")


if __name__ == "__main__":
    if "MPLCONFIGDIR" not in os.environ:
        os.environ["MPLCONFIGDIR"] = ".mplconfig"
    main()
