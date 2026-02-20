"""Scenario clustering helpers for Ffion/Clyfar ensemble summaries.

Implements a deterministic two-stage approach:
1) Reserve cluster 0 for strict background-only Clyfar members.
2) Cluster remaining members over an adaptive non-background active window.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Sequence, Tuple

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import pdist, squareform


BLOCK_NAMES = ("days_1_5", "days_6_10", "days_11_15")
BLOCK_BOUNDS = ((0, 5), (5, 10), (10, None))
BLOCK_WEIGHTS = np.array([0.55, 0.30, 0.15], dtype=float)

# Stage-1 strict null-selection (cluster 0)
STRICT_BACKGROUND_TARGET = 1.0
STRICT_OTHER_TARGET = 0.0
STRICT_TOLERANCE = 1e-6

# Stage-2 clustering defaults
DISTANCE_WEIGHTS = {"possibility": 0.60, "percentile": 0.40}
K_MIN = 1
K_MAX = 3


def _block_ranges(n_steps: int) -> List[Tuple[str, int, int, float]]:
    """Return valid block ranges and normalized weights for ``n_steps``."""
    ranges: List[Tuple[str, int, int, float]] = []
    weights: List[float] = []

    for i, ((start, end), name) in enumerate(zip(BLOCK_BOUNDS, BLOCK_NAMES)):
        if start >= n_steps:
            continue
        stop = n_steps if end is None else min(end, n_steps)
        if stop <= start:
            continue
        ranges.append((name, start, stop, float(BLOCK_WEIGHTS[i])))
        weights.append(float(BLOCK_WEIGHTS[i]))

    if not ranges:
        return []

    denom = float(np.sum(weights))
    if denom <= 0:
        # Should never happen with static positive block weights.
        return [(name, a, b, 1.0 / len(ranges)) for name, a, b, _ in ranges]
    return [(name, a, b, w / denom) for name, a, b, w in ranges]


def _blockwise_means(values: np.ndarray) -> Dict[str, float]:
    """Compute block means for a single 1D trajectory."""
    out: Dict[str, float] = {name: float("nan") for name in BLOCK_NAMES}
    for name, start, stop, _ in _block_ranges(len(values)):
        segment = values[start:stop]
        if segment.size == 0:
            out[name] = float("nan")
        else:
            out[name] = float(np.nanmean(segment))
    return out


def _weighted_from_block_means(block_means: Dict[str, float]) -> float:
    """Compute weighted mean from block means, renormalizing valid blocks."""
    valid_vals: List[float] = []
    valid_weights: List[float] = []
    for name, weight in zip(BLOCK_NAMES, BLOCK_WEIGHTS):
        value = block_means.get(name, float("nan"))
        if np.isnan(value):
            continue
        valid_vals.append(float(value))
        valid_weights.append(float(weight))

    if not valid_vals:
        return float("nan")
    w = np.array(valid_weights, dtype=float)
    w = w / w.sum()
    return float(np.dot(np.array(valid_vals, dtype=float), w))


def _daily_weights(n_steps: int) -> np.ndarray:
    """Return per-day weights so each 5-day block contributes by design weight."""
    out = np.zeros(n_steps, dtype=float)
    for _, start, stop, weight in _block_ranges(n_steps):
        block_len = stop - start
        # sqrt() so Euclidean distance contributes roughly as configured block weight
        out[start:stop] = np.sqrt(weight / block_len)
    return out


def _zscore_columns(X: np.ndarray) -> np.ndarray:
    """Column-wise z-score with epsilon stabilization."""
    mu = X.mean(axis=0)
    sigma = X.std(axis=0) + 1e-6
    return (X - mu) / sigma


def _fill_nan_with_col_median(X: np.ndarray) -> np.ndarray:
    """Replace NaNs with per-column median (or 0 if fully missing)."""
    out = X.copy()
    for j in range(out.shape[1]):
        col = out[:, j]
        if np.isnan(col).all():
            out[:, j] = 0.0
            continue
        if np.isnan(col).any():
            med = np.nanmedian(col)
            col[np.isnan(col)] = med
            out[:, j] = col
    return out


def _pairwise_euclidean(X: np.ndarray) -> np.ndarray:
    """Return square pairwise Euclidean distance matrix."""
    if len(X) == 0:
        return np.zeros((0, 0), dtype=float)
    if len(X) == 1:
        return np.zeros((1, 1), dtype=float)
    return squareform(pdist(X, metric="euclidean"))


def _silhouette_from_distance(D: np.ndarray, labels: np.ndarray) -> float:
    """Compute average silhouette from a precomputed distance matrix."""
    n = len(labels)
    unique = np.unique(labels)
    if n < 3 or len(unique) < 2 or len(unique) >= n:
        return -1.0

    s_vals: List[float] = []
    for i in range(n):
        label_i = labels[i]
        same_idx = np.where(labels == label_i)[0]
        if len(same_idx) <= 1:
            return -1.0

        same_wo_i = same_idx[same_idx != i]
        a_i = float(np.mean(D[i, same_wo_i])) if len(same_wo_i) else 0.0

        b_i = float("inf")
        for other in unique:
            if other == label_i:
                continue
            other_idx = np.where(labels == other)[0]
            if len(other_idx) == 0:
                continue
            b_i = min(b_i, float(np.mean(D[i, other_idx])))

        if not np.isfinite(b_i):
            return -1.0

        denom = max(a_i, b_i)
        s_i = 0.0 if denom <= 0 else (b_i - a_i) / denom
        s_vals.append(float(s_i))

    if not s_vals:
        return -1.0
    return float(np.mean(s_vals))


def _cluster_from_distance(D: np.ndarray, k: int) -> np.ndarray:
    """Cluster using agglomerative average linkage on precomputed distance."""
    n = D.shape[0]
    if n == 0:
        return np.array([], dtype=int)
    if n == 1 or k <= 1:
        return np.ones(n, dtype=int)
    k = min(k, n)
    Z = linkage(squareform(D, checks=False), method="average")
    return fcluster(Z, k, criterion="maxclust")


def _min_cluster_size(labels: np.ndarray) -> int:
    """Return size of the smallest cluster."""
    if len(labels) == 0:
        return 0
    _, counts = np.unique(labels, return_counts=True)
    return int(counts.min())


def _distance_quantiles(D: np.ndarray) -> Dict[str, float]:
    """Return compact quantiles from the upper triangle of a distance matrix."""
    n = D.shape[0]
    if n <= 1:
        return {
            "n_pairs": 0,
            "min": 0.0,
            "p25": 0.0,
            "median": 0.0,
            "p75": 0.0,
            "max": 0.0,
        }
    iu = np.triu_indices(n, k=1)
    vals = D[iu]
    if vals.size == 0:
        return {
            "n_pairs": 0,
            "min": 0.0,
            "p25": 0.0,
            "median": 0.0,
            "p75": 0.0,
            "max": 0.0,
        }
    return {
        "n_pairs": int(vals.size),
        "min": round(float(np.min(vals)), 4),
        "p25": round(float(np.quantile(vals, 0.25)), 4),
        "median": round(float(np.median(vals)), 4),
        "p75": round(float(np.quantile(vals, 0.75)), 4),
        "max": round(float(np.max(vals)), 4),
    }


def _nearest_neighbor_diagnostics(
    D: np.ndarray,
    members: List[str],
    top_n: int = 5,
) -> Dict[str, Any]:
    """Summarize nearest-neighbor distances for non-null members."""
    n = D.shape[0]
    if n <= 1:
        return {
            "median": 0.0,
            "p75": 0.0,
            "max": 0.0,
            "top_members": [],
        }

    nn_vals: List[float] = []
    member_pairs: List[Tuple[str, float]] = []
    for i, member in enumerate(members):
        row = D[i].copy()
        row[i] = np.inf
        nearest = float(np.min(row))
        nn_vals.append(nearest)
        member_pairs.append((member, nearest))

    member_pairs_sorted = sorted(member_pairs, key=lambda x: x[1], reverse=True)
    return {
        "median": round(float(np.median(np.array(nn_vals, dtype=float))), 4),
        "p75": round(float(np.quantile(np.array(nn_vals, dtype=float), 0.75)), 4),
        "max": round(float(np.max(np.array(nn_vals, dtype=float))), 4),
        "top_members": [
            {"member": m, "nearest_distance": round(float(v), 4)}
            for m, v in member_pairs_sorted[:max(0, int(top_n))]
        ],
    }


def _choose_k(D: np.ndarray) -> Tuple[np.ndarray, Dict[str, Any]]:
    """Select cluster count in [1, 3] with silhouette and min-size guard."""
    n = D.shape[0]
    if n <= 1:
        labels = np.ones(n, dtype=int)
        return labels, {
            "selected_k": 1,
            "min_cluster_size_required": 1,
            "scores": {},
            "fallback_used": False,
        }

    if n <= 2:
        labels = np.ones(n, dtype=int)
        return labels, {
            "selected_k": 1,
            "min_cluster_size_required": 1,
            "scores": {},
            "fallback_used": False,
        }

    max_k = min(K_MAX, n - 1)
    min_k = max(2, K_MIN)
    if max_k < min_k:
        labels = np.ones(n, dtype=int)
        return labels, {
            "selected_k": 1,
            "min_cluster_size_required": 1,
            "scores": {},
            "fallback_used": False,
        }

    min_size_required = 2 if n >= 6 else 1
    scores: Dict[int, float] = {}
    all_scores: Dict[int, float] = {}
    best_labels: np.ndarray | None = None
    best_k: int | None = None
    best_score = -2.0

    for k in range(min_k, max_k + 1):
        labels_k = _cluster_from_distance(D, k)
        score = _silhouette_from_distance(D, labels_k)
        all_scores[k] = score
        if _min_cluster_size(labels_k) < min_size_required:
            continue
        scores[k] = score
        if score > best_score:
            best_score = score
            best_k = k
            best_labels = labels_k

    if best_labels is not None and best_k is not None:
        return best_labels, {
            "selected_k": int(best_k),
            "min_cluster_size_required": int(min_size_required),
            "scores": {str(k): round(v, 4) for k, v in all_scores.items()},
            "scores_passing_min_size": {str(k): round(v, 4) for k, v in scores.items()},
            "min_size_guard_relaxed": False,
            "fallback_used": False,
        }

    # Soft fallback: if all candidate k violate min-size, still preserve structure.
    if all_scores:
        fallback_k = max(
            sorted(all_scores.keys()),
            key=lambda k: (all_scores[k], -k),
        )
        labels_fb = _cluster_from_distance(D, fallback_k)
        return labels_fb, {
            "selected_k": int(fallback_k),
            "min_cluster_size_required": int(min_size_required),
            "scores": {str(k): round(v, 4) for k, v in all_scores.items()},
            "scores_passing_min_size": {},
            "min_size_guard_relaxed": True,
            "fallback_used": True,
        }

    # Hard fallback for degenerate/no-score conditions.
    fallback_k = 1
    if fallback_k == 1:
        labels_fb = np.ones(n, dtype=int)
    else:
        labels_fb = _cluster_from_distance(D, fallback_k)

    return labels_fb, {
        "selected_k": int(fallback_k),
        "min_cluster_size_required": int(min_size_required),
        "scores": {},
        "scores_passing_min_size": {},
        "min_size_guard_relaxed": False,
        "fallback_used": True,
    }


def _classify_risk(
    weighted_non_background: float,
    weighted_high: float,
    weighted_extreme: float,
) -> Tuple[str, str]:
    """Return (dominant_category, risk_level) from weighted risk summaries."""
    if (
        np.isnan(weighted_non_background)
        or np.isnan(weighted_high)
        or np.isnan(weighted_extreme)
    ):
        return "unknown", "unknown"
    if weighted_extreme >= 0.30:
        return "extreme", "very high"
    if weighted_high >= 0.50:
        return "elevated", "high"
    if weighted_non_background >= 0.30:
        return "moderate", "medium"
    return "background", "low"


def _weather_profile(weather_data: Dict[str, Dict[str, Sequence[float]]], members: List[str]) -> Dict[str, Any]:
    """Summarize snow/wind tendencies for members in a cluster."""
    snow_vals: List[float] = []
    wind_vals: List[float] = []
    for m in members:
        payload = weather_data.get(m, {})
        snow = payload.get("snow", [])
        wind = payload.get("wind", [])
        snow_vals.extend([float(v) for v in snow if v is not None and np.isfinite(v)])
        wind_vals.extend([float(v) for v in wind if v is not None and np.isfinite(v)])

    if snow_vals:
        snow_mm = float(np.nanmedian(np.array(snow_vals, dtype=float)))
        snow_in = snow_mm / 25.4
        if snow_in > 2.0:
            snow_tendency = f"high (>{snow_in:.0f} inches)"
        elif snow_in > 1.0:
            snow_tendency = f"moderate ({snow_in:.1f} inches)"
        else:
            snow_tendency = "low (<1 inch)"
    else:
        snow_tendency = "unknown"

    if wind_vals:
        wind_ms = float(np.nanmedian(np.array(wind_vals, dtype=float)))
        wind_mph = wind_ms * 2.24
        if wind_mph > 10:
            wind_tendency = f"breezy (>{wind_mph:.0f} mph)"
        elif wind_mph > 5:
            wind_tendency = f"light ({wind_mph:.0f} mph)"
        else:
            wind_tendency = "calm (<5 mph)"
    else:
        wind_tendency = "unknown"

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


def _member_metrics(member_poss: Dict[str, pd.DataFrame], members: List[str], index: pd.Index) -> Dict[str, Dict[str, Any]]:
    """Compute per-member null metrics from possibility trajectories."""
    metrics: Dict[str, Dict[str, Any]] = {}
    for m in members:
        df = member_poss[m].reindex(index)
        bg = np.nan_to_num(df["background"].to_numpy(dtype=float), nan=0.0)
        moderate = np.nan_to_num(df["moderate"].to_numpy(dtype=float), nan=0.0)
        elev = np.nan_to_num(df["elevated"].to_numpy(dtype=float), nan=0.0)
        ext = np.nan_to_num(df["extreme"].to_numpy(dtype=float), nan=0.0)
        high = elev + ext
        non_background = moderate + high

        moderate_blocks = _blockwise_means(moderate)
        high_blocks = _blockwise_means(high)
        non_background_blocks = _blockwise_means(non_background)
        ext_blocks = _blockwise_means(ext)
        bg_blocks = _blockwise_means(bg)

        weighted_moderate = _weighted_from_block_means(moderate_blocks)
        weighted_high = _weighted_from_block_means(high_blocks)
        weighted_non_background = _weighted_from_block_means(non_background_blocks)
        weighted_extreme = _weighted_from_block_means(ext_blocks)
        weighted_background = _weighted_from_block_means(bg_blocks)

        # Lower score means more strict-background / less non-background signal.
        null_score = (
            weighted_non_background
            + 0.60 * weighted_extreme
            - 0.30 * weighted_background
        )

        metrics[m] = {
            "weighted_moderate": float(weighted_moderate),
            "weighted_high": float(weighted_high),
            "weighted_non_background": float(weighted_non_background),
            "weighted_extreme": float(weighted_extreme),
            "weighted_background": float(weighted_background),
            "block_means": {
                "moderate": moderate_blocks,
                "high": high_blocks,
                "non_background": non_background_blocks,
                "extreme": ext_blocks,
                "background": bg_blocks,
            },
            "null_score": float(null_score),
        }
    return metrics


def _is_strict_background_member(df: pd.DataFrame) -> bool:
    """Return True when all lead days are background-only within numeric tolerance."""
    if df.empty:
        return False
    values = df[["background", "moderate", "elevated", "extreme"]].to_numpy(dtype=float)
    if not np.isfinite(values).all():
        return False
    background = values[:, 0]
    others = values[:, 1:]
    return bool(
        np.all(background >= (STRICT_BACKGROUND_TARGET - STRICT_TOLERANCE))
        and np.all(others <= (STRICT_OTHER_TARGET + STRICT_TOLERANCE))
    )


def _active_window_mask(
    member_poss: Dict[str, pd.DataFrame],
    members: List[str],
    index: pd.Index,
) -> np.ndarray:
    """Return per-day mask where any member has non-background possibility."""
    n_steps = len(index)
    if n_steps == 0 or not members:
        return np.zeros(0, dtype=bool)

    active = np.zeros(n_steps, dtype=bool)
    for m in members:
        df = member_poss[m].reindex(index)
        moderate = np.nan_to_num(df["moderate"].to_numpy(dtype=float), nan=0.0)
        elevated = np.nan_to_num(df["elevated"].to_numpy(dtype=float), nan=0.0)
        extreme = np.nan_to_num(df["extreme"].to_numpy(dtype=float), nan=0.0)
        active |= (
            (moderate > (STRICT_OTHER_TARGET + STRICT_TOLERANCE))
            | (elevated > (STRICT_OTHER_TARGET + STRICT_TOLERANCE))
            | (extreme > (STRICT_OTHER_TARGET + STRICT_TOLERANCE))
        )
    return active


def _all_members_background(
    member_poss: Dict[str, pd.DataFrame],
    members: List[str],
    index: pd.Index,
) -> bool:
    """Return True if every member is strict-background across all lead days."""
    for m in members:
        if not _is_strict_background_member(member_poss[m].reindex(index)):
            return False
    return True


def _build_feature_matrices(
    member_poss: Dict[str, pd.DataFrame],
    member_percentiles: Dict[str, pd.DataFrame],
    members: List[str],
    index: pd.Index,
    active_mask: np.ndarray | None = None,
) -> Tuple[np.ndarray, np.ndarray]:
    """Build standardized Clyfar possibility/percentile feature matrices."""
    n_steps = len(index)
    if (
        active_mask is None
        or len(active_mask) != n_steps
        or not np.any(active_mask)
    ):
        mask = np.ones(n_steps, dtype=bool)
    else:
        mask = active_mask.astype(bool)

    # Equalized active-window weighting for scenario branching.
    day_w = np.zeros(n_steps, dtype=float)
    day_w[mask] = 1.0 / np.sqrt(float(mask.sum()))

    poss_rows: List[np.ndarray] = []
    pct_rows: List[np.ndarray] = []

    for m in members:
        poss_df = member_poss[m].reindex(index)
        pct_df = member_percentiles[m].reindex(index)

        moderate = np.nan_to_num(poss_df["moderate"].to_numpy(dtype=float), nan=0.0)
        elevated = np.nan_to_num(poss_df["elevated"].to_numpy(dtype=float), nan=0.0)
        extreme = np.nan_to_num(poss_df["extreme"].to_numpy(dtype=float), nan=0.0)
        non_background = moderate + elevated + extreme
        poss_vec = np.concatenate([
            moderate * day_w,
            elevated * day_w,
            extreme * day_w,
            non_background * day_w,
        ])
        poss_rows.append(poss_vec)

        p50 = pct_df["p50"].to_numpy(dtype=float)
        p90 = pct_df["p90"].to_numpy(dtype=float)
        pct_vec = np.concatenate([p50 * day_w, p90 * day_w])
        pct_rows.append(pct_vec)

    X_poss = _zscore_columns(_fill_nan_with_col_median(np.vstack(poss_rows)))
    X_pct = _zscore_columns(_fill_nan_with_col_median(np.vstack(pct_rows)))
    return X_poss, X_pct


def _cluster_profile(
    cid: int,
    kind: str,
    members_c: List[str],
    medoid: str,
    metrics: Dict[str, Dict[str, Any]],
    weather_data: Dict[str, Dict[str, Sequence[float]]],
) -> Dict[str, Any]:
    """Build cluster-level profile payload."""
    weighted_non_background = float(
        np.mean([metrics[m]["weighted_non_background"] for m in members_c])
    )
    weighted_moderate = float(np.mean([metrics[m]["weighted_moderate"] for m in members_c]))
    weighted_high = float(np.mean([metrics[m]["weighted_high"] for m in members_c]))
    weighted_extreme = float(np.mean([metrics[m]["weighted_extreme"] for m in members_c]))
    weighted_background = float(np.mean([metrics[m]["weighted_background"] for m in members_c]))
    dominant, risk = _classify_risk(
        weighted_non_background,
        weighted_high,
        weighted_extreme,
    )

    block_summary: Dict[str, Dict[str, float]] = {}
    for metric_name in ("moderate", "high", "non_background", "extreme", "background"):
        block_summary[metric_name] = {
            name: float(
                np.mean([metrics[m]["block_means"][metric_name].get(name, np.nan) for m in members_c])
            )
            for name in BLOCK_NAMES
        }

    return {
        "id": int(cid),
        "kind": kind,
        "members": sorted(members_c),
        "fraction": 0.0,  # populated later with total member count
        "medoid": medoid,
        "clyfar_ozone": {
            "dominant_category": dominant,
            "risk_level": risk,
        },
        "risk_profile": {
            "weighted_non_background": round(weighted_non_background, 3),
            "weighted_moderate": round(weighted_moderate, 3),
            "weighted_high": round(weighted_high, 3),
            "weighted_extreme": round(weighted_extreme, 3),
            "weighted_background": round(weighted_background, 3),
            "block_means": {
                metric_name: {k: round(v, 3) for k, v in values.items()}
                for metric_name, values in block_summary.items()
            },
        },
        "gefs_weather": _weather_profile(weather_data, members_c),
    }


def build_clustering_summary(
    norm_init: str,
    member_poss: Dict[str, pd.DataFrame],
    member_percentiles: Dict[str, pd.DataFrame],
    weather_data: Dict[str, Dict[str, Sequence[float]]] | None = None,
) -> Dict[str, Any]:
    """Build deterministic null-first clustering summary payload."""
    if weather_data is None:
        weather_data = {}

    if not member_poss:
        raise ValueError("No possibility members provided.")
    if not member_percentiles:
        raise ValueError("No percentile members provided.")

    members_poss = set(member_poss.keys())
    members_pct = set(member_percentiles.keys())
    members = sorted(members_poss & members_pct)
    dropped_missing_pct = sorted(members_poss - members_pct)
    dropped_missing_poss = sorted(members_pct - members_poss)
    if not members:
        raise ValueError("No common members between possibility and percentile inputs.")

    # Use possibility index as canonical daily horizon.
    first_member = members[0]
    index = member_poss[first_member].index
    for m in members[1:]:
        index = index.union(member_poss[m].index)
    index = pd.DatetimeIndex(index).sort_values()

    metrics = _member_metrics(member_poss, members, index)
    active_mask = _active_window_mask(member_poss, members, index)
    active_day_count = int(active_mask.sum())

    null_members = sorted(
        [
            m for m in members
            if _is_strict_background_member(member_poss[m].reindex(index))
        ]
    )
    strict_all_background = len(null_members) == len(members)
    null_meta = {
        "fallback_used": False,
        "selected_by_threshold": len(null_members),
        "target_size": len(null_members),
        "strict_all_background": strict_all_background,
    }
    null_set = set(null_members)
    non_null_members = [m for m in members if m not in null_set]

    labels_by_member: Dict[str, int] = {}
    clusters_by_id: Dict[int, List[str]] = defaultdict(list)
    medoid_by_cluster: Dict[int, str] = {}

    # Cluster 0 is always reserved for null/background-dominated members.
    if null_members:
        labels_by_member.update({m: 0 for m in null_members})
        clusters_by_id[0] = sorted(null_members)
        medoid_by_cluster[0] = sorted(null_members, key=lambda x: metrics[x]["null_score"])[0]

    clustering_meta: Dict[str, Any] = {
        "selected_k": 0,
        "min_cluster_size_required": 1,
        "scores": {},
        "scores_passing_min_size": {},
        "min_size_guard_relaxed": False,
        "fallback_used": False,
    }
    distance_diagnostics: Dict[str, Any] = {
        "non_null_members": int(len(non_null_members)),
        "possibility": _distance_quantiles(np.zeros((len(non_null_members), len(non_null_members)))),
        "percentile": _distance_quantiles(np.zeros((len(non_null_members), len(non_null_members)))),
        "combined": _distance_quantiles(np.zeros((len(non_null_members), len(non_null_members)))),
        "nearest_neighbor": _nearest_neighbor_diagnostics(
            np.zeros((len(non_null_members), len(non_null_members))),
            non_null_members,
        ),
    }

    if not non_null_members:
        clustering_meta["selected_k"] = 0
    elif len(non_null_members) == 1:
        labels_by_member[non_null_members[0]] = 1
        clusters_by_id[1] = [non_null_members[0]]
        medoid_by_cluster[1] = non_null_members[0]
        clustering_meta["selected_k"] = 1
    elif len(non_null_members) >= 2:
        X_poss, X_pct = _build_feature_matrices(
            member_poss=member_poss,
            member_percentiles=member_percentiles,
            members=non_null_members,
            index=index,
            active_mask=active_mask,
        )
        D_poss = _pairwise_euclidean(X_poss)
        D_pct = _pairwise_euclidean(X_pct)
        D = (
            DISTANCE_WEIGHTS["possibility"] * D_poss
            + DISTANCE_WEIGHTS["percentile"] * D_pct
        )
        distance_diagnostics = {
            "non_null_members": int(len(non_null_members)),
            "possibility": _distance_quantiles(D_poss),
            "percentile": _distance_quantiles(D_pct),
            "combined": _distance_quantiles(D),
            "nearest_neighbor": _nearest_neighbor_diagnostics(D, non_null_members),
        }
        labels_stage2, clustering_meta = _choose_k(D)

        # Raw IDs from scipy are 1..k but we remap by severity.
        raw_to_members: Dict[int, List[str]] = defaultdict(list)
        for m, raw_id in zip(non_null_members, labels_stage2):
            raw_to_members[int(raw_id)].append(m)

        # Medoids in raw cluster-id space.
        raw_medoids: Dict[int, str] = {}
        for raw_id, members_c in raw_to_members.items():
            idx = [non_null_members.index(m) for m in members_c]
            sub = D[np.ix_(idx, idx)]
            sums = sub.sum(axis=1)
            medoid_local = int(np.argmin(sums))
            raw_medoids[raw_id] = members_c[medoid_local]

        # Order non-null clusters by increasing non-background severity.
        ordered_raw = sorted(
            raw_to_members.keys(),
            key=lambda raw: (
                float(np.mean([metrics[m]["weighted_non_background"] for m in raw_to_members[raw]])),
                float(np.mean([metrics[m]["weighted_high"] for m in raw_to_members[raw]])),
            ),
        )

        for new_id, raw_id in enumerate(ordered_raw, start=1):
            members_c = sorted(raw_to_members[raw_id])
            clusters_by_id[new_id] = members_c
            medoid_by_cluster[new_id] = raw_medoids[raw_id]
            for m in members_c:
                labels_by_member[m] = new_id

    total_members = len(members)
    clusters: List[Dict[str, Any]] = []
    for cid in sorted(clusters_by_id.keys()):
        members_c = clusters_by_id[cid]
        kind = "null" if cid == 0 else "scenario"
        profile = _cluster_profile(
            cid=cid,
            kind=kind,
            members_c=members_c,
            medoid=medoid_by_cluster[cid],
            metrics=metrics,
            weather_data=weather_data,
        )
        profile["fraction"] = round(len(members_c) / float(total_members), 3)
        clusters.append(profile)

    representative_members = [c["medoid"] for c in clusters]

    linkage_note_parts = []
    for c in clusters:
        linkage_note_parts.append(
            f"{c['gefs_weather']['pattern']} → {c['clyfar_ozone']['dominant_category']} ozone (Cluster {c['id']})"
        )
    linkage_note = ". ".join(linkage_note_parts) + "." if linkage_note_parts else ""

    spread_parts = []
    for c in clusters:
        frac_pct = int(round(100 * c["fraction"]))
        spread_parts.append(f"{frac_pct}% {c['clyfar_ozone']['risk_level']} risk")

    summary = {
        "schema_version": "1.2",
        "init": norm_init,
        "method": {
            "stage_1": {
                "name": "strict_background_only",
                "strict_all_background": {
                    "background_target": STRICT_BACKGROUND_TARGET,
                    "other_target": STRICT_OTHER_TARGET,
                    "tolerance": STRICT_TOLERANCE,
                },
                "active_window": {
                    "name": "ensemble_non_background_days",
                    "active_days": active_day_count,
                    "total_days": len(index),
                },
            },
            "stage_2": {
                "name": "agglomerative_average_precomputed_distance",
                "k_min": K_MIN,
                "k_max": K_MAX,
                "selected_k": int(clustering_meta["selected_k"]),
                "silhouette_scores": clustering_meta.get("scores", {}),
                "scores_passing_min_size": clustering_meta.get("scores_passing_min_size", {}),
                "min_size_guard_relaxed": bool(clustering_meta.get("min_size_guard_relaxed", False)),
                "fallback_used": bool(clustering_meta.get("fallback_used", False)),
                "distance_weights": DISTANCE_WEIGHTS,
                "distance_diagnostics": distance_diagnostics,
            },
            "time_blocks": {
                "names": list(BLOCK_NAMES),
                "weights": [float(x) for x in BLOCK_WEIGHTS],
            },
        },
        "n_members": total_members,
        "n_clusters": len(clusters),
        "clusters": clusters,
        "representative_members": representative_members,
        "member_assignment": {m: int(labels_by_member[m]) for m in sorted(labels_by_member)},
        "linkage_note": linkage_note,
        "spread_summary": f"{len(clusters)} clusters; {', '.join(spread_parts)}",
        "quality_flags": {
            "null_fallback_applied": bool(null_meta["fallback_used"]),
            "null_selected_by_threshold": int(null_meta["selected_by_threshold"]),
            "null_target_size": int(null_meta["target_size"]),
            "strict_all_background": bool(null_meta.get("strict_all_background", False)),
            "strict_null_members": int(len(null_members)),
            "non_null_members": int(len(non_null_members)),
            "active_window_days": active_day_count,
            "min_size_guard_relaxed": bool(clustering_meta.get("min_size_guard_relaxed", False)),
            "dropped_members_missing_percentiles": dropped_missing_pct,
            "dropped_members_missing_possibilities": dropped_missing_poss,
        },
    }
    return summary
