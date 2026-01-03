#!/usr/bin/env python3
"""
Generate a JSON summary of ensemble clustering showing GEFS↔Clyfar linkage.

Merges possibility-based clustering with GEFS weather characterization to
produce a small JSON file that helps Claude understand ensemble structure.

Usage:
    python scripts/generate_clustering_summary.py 2026010212
    python scripts/generate_clustering_summary.py --case-dir data/json_tests/CASE_20260102_1200Z

Output:
    {case_dir}/clustering_summary.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import pdist, squareform

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

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


def build_possibility_features(
    member_poss: Dict[str, "np.ndarray"], index: "np.ndarray"
) -> Tuple[np.ndarray, List[str]]:
    """Create feature matrix from elevated+extreme over full horizon."""
    members = sorted(member_poss.keys())
    X_list = []
    for m in members:
        df = member_poss[m]
        df = df.reindex(index)
        high = (df["elevated"] + df["extreme"]).to_numpy()
        extreme = df["extreme"].to_numpy()
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


def characterize_weather(weather_data: Dict[str, any], members: List[str]) -> Dict[str, str]:
    """Summarize GEFS weather pattern for a cluster's members."""
    # Aggregate weather stats across cluster members
    snow_vals = []
    wind_vals = []

    for member in members:
        # Member naming: clyfar000 -> need to find corresponding weather file
        # Weather files use same naming convention
        if member in weather_data:
            data = weather_data[member]
            if "snow" in data and isinstance(data["snow"], list):
                snow_vals.extend([v for v in data["snow"] if v is not None])
            if "wind" in data and isinstance(data["wind"], list):
                wind_vals.extend([v for v in data["wind"] if v is not None])

    # Characterize tendencies
    if snow_vals:
        snow_median = np.nanmedian(snow_vals)
        # Convert mm to inches for description
        snow_inches = snow_median / 25.4
        if snow_inches > 2:
            snow_tendency = f"high (>{snow_inches:.0f} inches)"
        elif snow_inches > 1:
            snow_tendency = f"moderate ({snow_inches:.1f} inches)"
        else:
            snow_tendency = f"low (<1 inch)"
    else:
        snow_tendency = "unknown"

    if wind_vals:
        wind_median = np.nanmedian(wind_vals)
        # Convert m/s to mph for description
        wind_mph = wind_median * 2.24
        if wind_mph > 10:
            wind_tendency = f"breezy (>{wind_mph:.0f} mph)"
        elif wind_mph > 5:
            wind_tendency = f"light ({wind_mph:.0f} mph)"
        else:
            wind_tendency = f"calm (<5 mph)"
    else:
        wind_tendency = "unknown"

    # Derive pattern description
    if "high" in snow_tendency and "calm" in wind_tendency:
        pattern = "stagnant cold pool"
    elif "low" in snow_tendency and "breezy" in wind_tendency:
        pattern = "active mixing"
    elif "moderate" in snow_tendency:
        pattern = "typical winter"
    else:
        pattern = "variable"

    return {
        "snow_tendency": snow_tendency,
        "wind_tendency": wind_tendency,
        "pattern": pattern,
    }


def characterize_ozone(member_poss: Dict[str, any], members: List[str]) -> Dict[str, str]:
    """Summarize Clyfar ozone pattern for a cluster's members."""
    elevated_sum = 0.0
    extreme_sum = 0.0
    count = 0

    for member in members:
        if member in member_poss:
            df = member_poss[member]
            elevated_sum += df["elevated"].sum()
            extreme_sum += df["extreme"].sum()
            count += len(df)

    if count > 0:
        avg_elevated = elevated_sum / count
        avg_extreme = extreme_sum / count
        avg_high = avg_elevated + avg_extreme

        if avg_extreme > 0.3:
            dominant = "extreme"
            risk = "very high"
        elif avg_high > 0.5:
            dominant = "elevated"
            risk = "high"
        elif avg_high > 0.3:
            dominant = "moderate"
            risk = "medium"
        else:
            dominant = "background"
            risk = "low"
    else:
        dominant = "unknown"
        risk = "unknown"

    return {
        "dominant_category": dominant,
        "risk_level": risk,
    }


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

    # Determine case directory
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

    poss_root = case_root / "possibilities"
    weather_root = case_root / "weather"

    if not poss_root.exists():
        raise SystemExit(f"Possibilities directory not found: {poss_root}")

    print(f"Generating clustering summary for: {norm_init}")

    plotter = ForecastPlotter()

    # Load all members' possibility heatmaps
    member_poss: Dict[str, any] = {}
    dates = None
    suffix = norm_init.split("_")[-1]  # HHMMZ

    for path in sorted(poss_root.glob(f"forecast_possibility_heatmap_*_{norm_init}.json")):
        parts = path.stem.split("_")
        member = parts[3]  # clyfar000
        df, _ = plotter.load_possibility(path)
        if dates is None:
            dates = df.index
        member_poss[member] = df

    if not member_poss:
        raise SystemExit(f"No possibility_heatmap files found for {norm_init}")

    # Load weather data for characterization
    weather_data: Dict[str, any] = {}
    for path in sorted(weather_root.glob(f"forecast_gefs_weather_*_{norm_init}.json")):
        parts = path.stem.split("_")
        member = parts[3]  # clyfar000
        try:
            with open(path) as f:
                data = json.load(f)
                # Extract time series from nested 'weather' key
                weather = data.get("weather", {})
                weather_data[member] = {
                    "snow": weather.get("snow", []),
                    "wind": weather.get("wind", []),
                }
        except Exception:
            pass

    # Build features and cluster
    X, members = build_possibility_features(member_poss, dates)
    X = (X - X.mean(axis=0)) / (X.std(axis=0) + 1e-6)

    k = 3
    if len(members) < k:
        k = max(1, len(members))

    labels = cluster_members(X, k)
    medoids = find_medoids(X, labels)

    # Build cluster membership map
    cluster_members_map: Dict[int, List[str]] = defaultdict(list)
    for m, label in zip(members, labels):
        cluster_members_map[label].append(m)

    # Build summary JSON
    clusters = []
    representative_members = []

    for cid in sorted(cluster_members_map):
        members_c = cluster_members_map[cid]
        frac = len(members_c) / float(len(members))
        medoid_idx = medoids[cid]
        medoid_member = members[medoid_idx]
        representative_members.append(medoid_member)

        # Characterize this cluster
        weather_char = characterize_weather(weather_data, members_c)
        ozone_char = characterize_ozone(member_poss, members_c)

        clusters.append({
            "id": int(cid),
            "members": members_c,
            "fraction": round(frac, 2),
            "medoid": medoid_member,
            "gefs_weather": weather_char,
            "clyfar_ozone": ozone_char,
        })

    # Build linkage note
    linkage_parts = []
    for c in clusters:
        weather = c["gefs_weather"]["pattern"]
        ozone = c["clyfar_ozone"]["dominant_category"]
        linkage_parts.append(f"{weather} → {ozone} ozone (Cluster {c['id']})")
    linkage_note = ". ".join(linkage_parts) + "."

    # Build spread summary
    spread_parts = []
    for c in clusters:
        spread_parts.append(f"{int(c['fraction']*100)}% {c['clyfar_ozone']['risk_level']} risk")
    spread_summary = f"{len(clusters)} clusters; " + ", ".join(spread_parts)

    summary = {
        "init": norm_init,
        "n_clusters": len(clusters),
        "clusters": clusters,
        "representative_members": representative_members,
        "linkage_note": linkage_note,
        "spread_summary": spread_summary,
    }

    # Write output
    out_path = case_root / "clustering_summary.json"
    with open(out_path, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"Wrote clustering summary to: {out_path}")
    print(f"  {len(clusters)} clusters, representatives: {representative_members}")


if __name__ == "__main__":
    if "MPLCONFIGDIR" not in os.environ:
        os.environ["MPLCONFIGDIR"] = ".mplconfig"
    main()
