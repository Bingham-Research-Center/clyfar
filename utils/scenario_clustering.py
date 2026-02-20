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
MISSING_DATA_POLICY = "ignore_missing_days"
SINGLETON_POLICY = "evidence_gated_lenient"
SINGLETON_MIN_PASS_CRITERIA = 2
SINGLETON_P90_RISK_LIFT_PPB = 4.0
SINGLETON_NON_BACKGROUND_LIFT = 0.01


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


def _zscore_columns(X: np.ndarray, valid_mask: np.ndarray | None = None) -> np.ndarray:
    """Column-wise z-score with epsilon stabilization, preserving missing entries."""
    out = X.astype(float).copy()
    if valid_mask is None:
        valid = np.isfinite(out)
    else:
        valid = valid_mask.astype(bool) & np.isfinite(out)

    for j in range(out.shape[1]):
        idx = valid[:, j]
        if not np.any(idx):
            out[:, j] = np.nan
            continue
        col = out[idx, j]
        mu = float(np.mean(col))
        sigma = float(np.std(col)) + 1e-6
        out[idx, j] = (col - mu) / sigma
        out[~idx, j] = np.nan
    return out


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


def _pairwise_euclidean_masked(X: np.ndarray, valid_mask: np.ndarray) -> np.ndarray:
    """Return pairwise Euclidean distance while ignoring invalid dimensions."""
    n, d = X.shape
    if n == 0:
        return np.zeros((0, 0), dtype=float)
    if n == 1:
        return np.zeros((1, 1), dtype=float)

    valid = valid_mask.astype(bool) & np.isfinite(X)
    D = np.zeros((n, n), dtype=float)
    for i in range(n):
        xi = X[i]
        vi = valid[i]
        for j in range(i + 1, n):
            xj = X[j]
            mask = vi & valid[j]
            m = int(np.sum(mask))
            if m == 0:
                dist = 0.0
            else:
                diff = xi[mask] - xj[mask]
                # Rescale by observed dimension fraction to keep distances comparable.
                dist = float(np.linalg.norm(diff) * np.sqrt(float(d) / float(m)))
            D[i, j] = dist
            D[j, i] = dist
    return D


def _build_member_valid_day_masks(
    member_poss: Dict[str, pd.DataFrame],
    members: List[str],
    index: pd.Index,
    member_missing_masks: Dict[str, Sequence[bool]] | None = None,
) -> Dict[str, np.ndarray]:
    """Return per-member valid-day masks aligned to the canonical index."""
    if member_missing_masks is None:
        member_missing_masks = {}

    out: Dict[str, np.ndarray] = {}
    for m in members:
        df = member_poss[m].reindex(index)
        values = df[["background", "moderate", "elevated", "extreme"]].to_numpy(dtype=float)
        valid = np.isfinite(values).all(axis=1)

        raw_missing = member_missing_masks.get(m)
        if raw_missing is not None:
            raw = np.asarray(raw_missing, dtype=bool).reshape(-1)
            missing_aligned: np.ndarray | None = None
            if len(raw) == len(member_poss[m].index):
                series = pd.Series(raw, index=member_poss[m].index)
                missing_aligned = series.reindex(index, fill_value=False).to_numpy(dtype=bool)
            elif len(raw) == len(index):
                missing_aligned = raw
            if missing_aligned is not None:
                valid &= ~missing_aligned

        out[m] = valid
    return out


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


def _member_metrics(
    member_poss: Dict[str, pd.DataFrame],
    members: List[str],
    index: pd.Index,
    member_valid_day_masks: Dict[str, np.ndarray] | None = None,
) -> Dict[str, Dict[str, Any]]:
    """Compute per-member null metrics from possibility trajectories."""
    if member_valid_day_masks is None:
        member_valid_day_masks = {}

    metrics: Dict[str, Dict[str, Any]] = {}
    for m in members:
        df = member_poss[m].reindex(index)
        valid = member_valid_day_masks.get(m)
        if valid is None or len(valid) != len(df):
            values = df[["background", "moderate", "elevated", "extreme"]].to_numpy(dtype=float)
            valid = np.isfinite(values).all(axis=1)
        valid = valid.astype(bool)

        bg = df["background"].to_numpy(dtype=float)
        moderate = df["moderate"].to_numpy(dtype=float)
        elev = df["elevated"].to_numpy(dtype=float)
        ext = df["extreme"].to_numpy(dtype=float)
        bg[~valid] = np.nan
        moderate[~valid] = np.nan
        elev[~valid] = np.nan
        ext[~valid] = np.nan
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
        null_score_raw = (
            weighted_non_background
            + 0.60 * weighted_extreme
            - 0.30 * weighted_background
        )
        null_score = float(null_score_raw) if np.isfinite(null_score_raw) else float("inf")

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


def _is_strict_background_member(df: pd.DataFrame, valid_day_mask: np.ndarray | None = None) -> bool:
    """Return True when all lead days are background-only within numeric tolerance."""
    if df.empty:
        return False
    values = df[["background", "moderate", "elevated", "extreme"]].to_numpy(dtype=float)
    finite_row = np.isfinite(values).all(axis=1)
    if valid_day_mask is None:
        valid = finite_row
    else:
        valid = valid_day_mask.astype(bool)
        if len(valid) != len(df):
            valid = finite_row
        else:
            valid &= finite_row

    if not np.any(valid):
        return False
    background = values[valid, 0]
    others = values[valid, 1:]
    return bool(
        np.all(background >= (STRICT_BACKGROUND_TARGET - STRICT_TOLERANCE))
        and np.all(others <= (STRICT_OTHER_TARGET + STRICT_TOLERANCE))
    )


def _active_window_mask(
    member_poss: Dict[str, pd.DataFrame],
    members: List[str],
    index: pd.Index,
    member_valid_day_masks: Dict[str, np.ndarray] | None = None,
) -> np.ndarray:
    """Return per-day mask where any member has non-background possibility."""
    if member_valid_day_masks is None:
        member_valid_day_masks = {}

    n_steps = len(index)
    if n_steps == 0 or not members:
        return np.zeros(0, dtype=bool)

    active = np.zeros(n_steps, dtype=bool)
    for m in members:
        df = member_poss[m].reindex(index)
        valid = member_valid_day_masks.get(m)
        if valid is None or len(valid) != len(df):
            values = df[["background", "moderate", "elevated", "extreme"]].to_numpy(dtype=float)
            valid = np.isfinite(values).all(axis=1)
        moderate = df["moderate"].to_numpy(dtype=float)
        elevated = df["elevated"].to_numpy(dtype=float)
        extreme = df["extreme"].to_numpy(dtype=float)
        member_active = (
            (moderate > (STRICT_OTHER_TARGET + STRICT_TOLERANCE))
            | (elevated > (STRICT_OTHER_TARGET + STRICT_TOLERANCE))
            | (extreme > (STRICT_OTHER_TARGET + STRICT_TOLERANCE))
        ) & valid.astype(bool)
        active |= member_active
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
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
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
    poss_valid_rows: List[np.ndarray] = []
    pct_rows: List[np.ndarray] = []
    pct_valid_rows: List[np.ndarray] = []

    for m in members:
        poss_df = member_poss[m].reindex(index)
        pct_df = member_percentiles[m].reindex(index)
        values = poss_df[["background", "moderate", "elevated", "extreme"]].to_numpy(dtype=float)
        valid_day = np.isfinite(values).all(axis=1)
        member_w = day_w.copy()
        member_w[~valid_day] = 0.0

        moderate = poss_df["moderate"].to_numpy(dtype=float)
        elevated = poss_df["elevated"].to_numpy(dtype=float)
        extreme = poss_df["extreme"].to_numpy(dtype=float)
        poss_vec = np.concatenate([
            moderate * member_w,
            elevated * member_w,
            extreme * member_w,
        ])
        poss_valid = np.concatenate([
            valid_day & (member_w > 0),
            valid_day & (member_w > 0),
            valid_day & (member_w > 0),
        ])
        poss_rows.append(poss_vec)
        poss_valid_rows.append(poss_valid)

        p50 = pct_df["p50"].to_numpy(dtype=float)
        p90 = pct_df["p90"].to_numpy(dtype=float)
        pct_vec = np.concatenate([p50 * member_w, p90 * member_w])
        pct_valid = np.concatenate([
            valid_day & np.isfinite(p50) & (member_w > 0),
            valid_day & np.isfinite(p90) & (member_w > 0),
        ])
        pct_rows.append(pct_vec)
        pct_valid_rows.append(pct_valid)

    poss_valid_mat = np.vstack(poss_valid_rows)
    pct_valid_mat = np.vstack(pct_valid_rows)
    X_poss = _zscore_columns(np.vstack(poss_rows), poss_valid_mat)
    X_pct = _zscore_columns(np.vstack(pct_rows), pct_valid_mat)
    return X_poss, poss_valid_mat, X_pct, pct_valid_mat


def _member_p90_peak(
    member_percentiles: Dict[str, pd.DataFrame],
    member: str,
    index: pd.Index,
    valid_day_mask: np.ndarray | None,
) -> float:
    """Return observed p90 peak for a member, excluding invalid/missing days."""
    df = member_percentiles[member].reindex(index)
    p90 = df["p90"].to_numpy(dtype=float)
    if valid_day_mask is None or len(valid_day_mask) != len(p90):
        valid = np.isfinite(p90)
    else:
        valid = valid_day_mask.astype(bool) & np.isfinite(p90)
    if not np.any(valid):
        return float("nan")
    return float(np.max(p90[valid]))


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


def _default_cluster_evidence(kind: str) -> Dict[str, Any]:
    """Return default evidence payload for non-singleton or non-scenario clusters."""
    if kind != "scenario":
        return {
            "singleton_evidence_score": 1.0,
            "singleton_evidence_passed": True,
            "evidence_reasons": ["not_applicable_non_scenario"],
        }
    return {
        "singleton_evidence_score": 1.0,
        "singleton_evidence_passed": True,
        "evidence_reasons": ["not_applicable_non_singleton"],
    }


def _evaluate_singleton_clusters(
    clusters_by_id: Dict[int, List[str]],
    medoid_by_cluster: Dict[int, str],
    non_null_members: List[str],
    D: np.ndarray | None,
    metrics: Dict[str, Dict[str, Any]],
    member_percentiles: Dict[str, pd.DataFrame],
    member_valid_day_masks: Dict[str, np.ndarray],
    index: pd.Index,
    nearest_neighbor_p75: float,
) -> Tuple[Dict[int, Dict[str, Any]], Dict[int, Dict[str, Any]], int]:
    """Build singleton evidence and display payloads for scenario clusters."""
    evidence_by_cluster: Dict[int, Dict[str, Any]] = {}
    display_by_cluster: Dict[int, Dict[str, Any]] = {}
    weak_singletons = 0

    for cid in sorted(clusters_by_id.keys()):
        kind = "null" if cid == 0 else "scenario"
        members_c = clusters_by_id[cid]
        evidence_by_cluster[cid] = _default_cluster_evidence(kind)
        display_by_cluster[cid] = {"status": "primary", "warning_code": None}

        if kind != "scenario" or len(members_c) != 1:
            continue
        if D is None or len(non_null_members) <= 1:
            continue

        member = members_c[0]
        idx_by_member = {m: i for i, m in enumerate(non_null_members)}
        member_idx = idx_by_member.get(member)
        if member_idx is None:
            continue

        nearest_distance = float("nan")
        if D.shape[0] == len(non_null_members):
            row = D[member_idx].copy()
            row[member_idx] = np.inf
            nearest_distance = float(np.min(row))

        other_scenario_ids = [
            c for c, mems in clusters_by_id.items()
            if c != cid and c != 0 and len(mems) > 0
        ]
        nearest_cluster_id: int | None = None
        nearest_cluster_mean_distance = float("inf")
        for other_id in other_scenario_ids:
            other_members = clusters_by_id[other_id]
            other_indices = [idx_by_member[m] for m in other_members if m in idx_by_member]
            if not other_indices:
                continue
            d_mean = float(np.mean([D[member_idx, j] for j in other_indices]))
            if d_mean < nearest_cluster_mean_distance:
                nearest_cluster_mean_distance = d_mean
                nearest_cluster_id = other_id

        singleton_peak = _member_p90_peak(
            member_percentiles=member_percentiles,
            member=member,
            index=index,
            valid_day_mask=member_valid_day_masks.get(member),
        )

        nearest_medoid_peak = float("nan")
        nearest_cluster_wnb_mean = float("nan")
        if nearest_cluster_id is not None:
            nearest_medoid = medoid_by_cluster.get(nearest_cluster_id)
            if nearest_medoid is not None and nearest_medoid in member_percentiles:
                nearest_medoid_peak = _member_p90_peak(
                    member_percentiles=member_percentiles,
                    member=nearest_medoid,
                    index=index,
                    valid_day_mask=member_valid_day_masks.get(nearest_medoid),
                )
            nearest_members = clusters_by_id.get(nearest_cluster_id, [])
            vals = [
                metrics[m]["weighted_non_background"] for m in nearest_members
                if m in metrics and np.isfinite(metrics[m]["weighted_non_background"])
            ]
            if vals:
                nearest_cluster_wnb_mean = float(np.mean(np.array(vals, dtype=float)))

        criterion_separation = (
            np.isfinite(nearest_distance)
            and np.isfinite(nearest_neighbor_p75)
            and nearest_distance >= nearest_neighbor_p75
        )
        criterion_risk_lift = (
            np.isfinite(singleton_peak)
            and np.isfinite(nearest_medoid_peak)
            and (singleton_peak - nearest_medoid_peak) >= SINGLETON_P90_RISK_LIFT_PPB
        )
        singleton_wnb = float(metrics.get(member, {}).get("weighted_non_background", np.nan))
        criterion_poss_lift = (
            np.isfinite(singleton_wnb)
            and np.isfinite(nearest_cluster_wnb_mean)
            and (singleton_wnb - nearest_cluster_wnb_mean) >= SINGLETON_NON_BACKGROUND_LIFT
        )

        criteria = {
            "separation_nearest_vs_nn_p75": {
                "passed": bool(criterion_separation),
                "nearest_distance": round(float(nearest_distance), 4) if np.isfinite(nearest_distance) else None,
                "nearest_neighbor_p75": round(float(nearest_neighbor_p75), 4) if np.isfinite(nearest_neighbor_p75) else None,
            },
            "p90_risk_lift_vs_nearest_medoid": {
                "passed": bool(criterion_risk_lift),
                "singleton_p90_peak": round(float(singleton_peak), 3) if np.isfinite(singleton_peak) else None,
                "nearest_medoid_p90_peak": round(float(nearest_medoid_peak), 3) if np.isfinite(nearest_medoid_peak) else None,
                "required_lift_ppb": SINGLETON_P90_RISK_LIFT_PPB,
            },
            "possibility_lift_vs_nearest_cluster_mean": {
                "passed": bool(criterion_poss_lift),
                "singleton_weighted_non_background": round(float(singleton_wnb), 4) if np.isfinite(singleton_wnb) else None,
                "nearest_cluster_weighted_non_background_mean": (
                    round(float(nearest_cluster_wnb_mean), 4)
                    if np.isfinite(nearest_cluster_wnb_mean) else None
                ),
                "required_lift": SINGLETON_NON_BACKGROUND_LIFT,
            },
        }
        pass_count = int(sum(int(v["passed"]) for v in criteria.values()))
        passed = pass_count >= SINGLETON_MIN_PASS_CRITERIA
        reasons = [name for name, payload in criteria.items() if payload["passed"]]
        if not reasons:
            reasons = ["no_criteria_passed"]

        evidence_by_cluster[cid] = {
            "singleton_evidence_score": round(float(pass_count) / 3.0, 3),
            "singleton_evidence_passed": bool(passed),
            "evidence_reasons": reasons,
            "criteria": criteria,
            "nearest_cluster_id": int(nearest_cluster_id) if nearest_cluster_id is not None else None,
        }
        if not passed:
            weak_singletons += 1
            display_by_cluster[cid] = {
                "status": "deemphasized",
                "warning_code": "weak_singleton_evidence",
            }

    return evidence_by_cluster, display_by_cluster, weak_singletons


def build_clustering_summary(
    norm_init: str,
    member_poss: Dict[str, pd.DataFrame],
    member_percentiles: Dict[str, pd.DataFrame],
    weather_data: Dict[str, Dict[str, Sequence[float]]] | None = None,
    member_missing_masks: Dict[str, Sequence[bool]] | None = None,
) -> Dict[str, Any]:
    """Build deterministic null-first clustering summary payload."""
    if weather_data is None:
        weather_data = {}
    if member_missing_masks is None:
        member_missing_masks = {}

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

    member_valid_day_masks = _build_member_valid_day_masks(
        member_poss=member_poss,
        members=members,
        index=index,
        member_missing_masks=member_missing_masks,
    )
    metrics = _member_metrics(
        member_poss=member_poss,
        members=members,
        index=index,
        member_valid_day_masks=member_valid_day_masks,
    )
    active_mask = _active_window_mask(
        member_poss=member_poss,
        members=members,
        index=index,
        member_valid_day_masks=member_valid_day_masks,
    )
    active_day_count = int(active_mask.sum())

    null_members = sorted(
        [
            m for m in members
            if _is_strict_background_member(
                member_poss[m].reindex(index),
                valid_day_mask=member_valid_day_masks.get(m),
            )
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
    D_non_null: np.ndarray | None = None
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
        X_poss, valid_poss, X_pct, valid_pct = _build_feature_matrices(
            member_poss=member_poss,
            member_percentiles=member_percentiles,
            members=non_null_members,
            index=index,
            active_mask=active_mask,
        )
        D_poss = _pairwise_euclidean_masked(X_poss, valid_poss)
        D_pct = _pairwise_euclidean_masked(X_pct, valid_pct)
        D = (
            DISTANCE_WEIGHTS["possibility"] * D_poss
            + DISTANCE_WEIGHTS["percentile"] * D_pct
        )
        D_non_null = D.copy()
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

    nearest_neighbor_p75 = float(
        distance_diagnostics.get("nearest_neighbor", {}).get("p75", 0.0)
    )
    cluster_evidence, cluster_display, weak_singletons = _evaluate_singleton_clusters(
        clusters_by_id=clusters_by_id,
        medoid_by_cluster=medoid_by_cluster,
        non_null_members=non_null_members,
        D=D_non_null,
        metrics=metrics,
        member_percentiles=member_percentiles,
        member_valid_day_masks=member_valid_day_masks,
        index=index,
        nearest_neighbor_p75=nearest_neighbor_p75,
    )

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
        profile["evidence"] = cluster_evidence.get(cid, _default_cluster_evidence(kind))
        profile["display"] = cluster_display.get(
            cid,
            {"status": "primary", "warning_code": None},
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
        "schema_version": "1.3",
        "init": norm_init,
        "method": {
            "stage_1": {
                "name": "strict_background_only",
                "missing_data_policy": MISSING_DATA_POLICY,
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
                "singleton_policy": SINGLETON_POLICY,
                "singleton_evidence_thresholds": {
                    "min_pass_criteria": SINGLETON_MIN_PASS_CRITERIA,
                    "separation_rule": "nearest_distance >= nearest_neighbor_p75",
                    "p90_lift_ppb": SINGLETON_P90_RISK_LIFT_PPB,
                    "weighted_non_background_lift": SINGLETON_NON_BACKGROUND_LIFT,
                },
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
            "weak_singleton_clusters": int(weak_singletons),
            "dropped_members_missing_percentiles": dropped_missing_pct,
            "dropped_members_missing_possibilities": dropped_missing_poss,
        },
    }
    return summary
