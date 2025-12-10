"""
Lightweight plotting helpers for BasinWx forecast JSON outputs.

Targets the same visual feel as the existing heatmaps/GEFS plots
(`viz/possibility_funcs.py`) and keeps everything in Matplotlib for
operational use. Works with the three export products:
- Possibility heatmaps (per-member)
- Percentile scenarios (per-member p10/p50/p90)
- Exceedance probabilities (ensemble)
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


CATEGORY_COLORS: Dict[str, str] = {
    "background": "#6CA0DC",
    "moderate": "#FFD700",
    "elevated": "#FF8C00",
    "extreme": "#FF6F61",
}


def _ensure_datetime_index(dates: Sequence[str]) -> pd.DatetimeIndex:
    """Convert a list of ISO date strings to a DatetimeIndex."""
    return pd.to_datetime(pd.Index(dates))


def _estimate_step_hours(index: Iterable[pd.Timestamp]) -> Optional[float]:
    """Estimate the median timestep (in hours) for a DatetimeIndex-like object."""
    idx = pd.Index(index)
    if len(idx) < 2:
        return None
    diffs = idx.to_series().diff().dropna().dt.total_seconds() / 3600.0
    diffs = diffs[diffs > 0]
    if diffs.empty:
        return None
    return float(diffs.median())


def _missing_mask_from_dates(index: pd.DatetimeIndex, missing_dates: Sequence[str]) -> np.ndarray:
    """Return a boolean mask for entries whose date appears in missing_dates."""
    missing = set(missing_dates or [])
    if not missing:
        return np.zeros(len(index), dtype=bool)
    iso = index.strftime("%Y-%m-%d")
    return np.array([d in missing for d in iso], dtype=bool)


@dataclass
class ForecastPlotter:
    """Matplotlib plots for BasinWx forecast JSON files."""

    category_colors: Dict[str, str] = None

    def __post_init__(self) -> None:
        if self.category_colors is None:
            self.category_colors = CATEGORY_COLORS.copy()
        plt.rcParams.update(
            {
                "axes.facecolor": "#f9fafb",
                "axes.edgecolor": "#d0d7de",
                "axes.grid": True,
                "grid.color": "#d0d7de",
                "grid.linestyle": "-",
                "grid.alpha": 0.6,
                "figure.dpi": 150,
                "savefig.dpi": 300,
            }
        )

    # ---------- Data loaders ----------
    @staticmethod
    def load_possibility(path: Path) -> Tuple[pd.DataFrame, np.ndarray]:
        """Load a possibility heatmap JSON into a DataFrame and missing mask."""
        with Path(path).open() as f:
            data = json.load(f)
        dates = _ensure_datetime_index(data["forecast_dates"])
        df = pd.DataFrame(data["heatmap"], index=dates)
        df = df[["background", "moderate", "elevated", "extreme"]]
        missing_mask = _missing_mask_from_dates(dates, data.get("missing_dates", []))
        return df, missing_mask

    @staticmethod
    def load_percentiles(path: Path) -> pd.DataFrame:
        """Load percentile scenarios JSON into a DataFrame (p10/p50/p90 columns)."""
        with Path(path).open() as f:
            data = json.load(f)
        dates = _ensure_datetime_index(data["forecast_dates"])
        scenarios = data["scenarios"]
        df = pd.DataFrame(
            {"p10": scenarios["p10"], "p50": scenarios["p50"], "p90": scenarios["p90"]},
            index=dates,
        )
        return df

    @staticmethod
    def load_exceedance(path: Path) -> pd.DataFrame:
        """Load exceedance probabilities JSON into a DataFrame with threshold columns."""
        with Path(path).open() as f:
            data = json.load(f)
        dates = _ensure_datetime_index(data["forecast_dates"])
        probs = data["exceedance_probabilities"]
        cols = {}
        for k, v in probs.items():
            # Expect keys like "30ppb"
            try:
                thresh = int(k.replace("ppb", ""))
            except ValueError:
                thresh = k
            cols[thresh] = v
        df = pd.DataFrame(cols, index=dates)
        df = df.reindex(sorted(df.columns), axis=1)
        return df

    # ---------- Plot helpers ----------
    def plot_possibility_stack(
        self, df: pd.DataFrame, missing_mask: Optional[np.ndarray] = None, title: str = ""
    ):
        """Stacked area view of category possibilities (same palette as heatmaps)."""
        fig, ax = plt.subplots(figsize=(10, 4))
        bottom = np.zeros(len(df))
        for cat in ["background", "moderate", "elevated", "extreme"]:
            values = df[cat].fillna(0.0).to_numpy()
            ax.fill_between(
                df.index,
                bottom,
                bottom + values,
                step="mid",
                color=self.category_colors[cat],
                alpha=0.75,
                label=cat,
            )
            bottom += values

        if missing_mask is not None and missing_mask.any():
            ax.fill_between(
                df.index,
                0,
                1,
                where=missing_mask,
                color="#c1c7cd",
                alpha=0.3,
                hatch="///",
                label="missing",
                step="mid",
            )

        ax.set_ylim(0, 1.05)
        ax.set_ylabel("Possibility (0-1)")
        ax.set_title(title or "Ozone category possibilities")
        self._add_day_10_marker(ax, df.index)
        ax.legend(loc="upper right", ncol=2, fontsize=8)
        fig.tight_layout()
        return fig, ax

    def plot_exceedance_lines(self, df: pd.DataFrame, title: str = ""):
        """Line plot for exceedance probabilities by threshold."""
        fig, ax = plt.subplots(figsize=(10, 3.5))
        palette = plt.cm.Blues(np.linspace(0.35, 0.95, len(df.columns)))
        for color, col in zip(palette, df.columns):
            ax.plot(df.index, df[col], marker="o", markersize=3, linewidth=1.5, color=color, label=f">{col} ppb")
        ax.set_ylim(0, 1.05)
        ax.set_ylabel("Probability")
        ax.set_title(title or "Probability of exceeding thresholds")
        self._add_day_10_marker(ax, df.index)
        ax.legend(loc="upper right", ncol=2, fontsize=8)
        fig.tight_layout()
        return fig, ax

    def plot_percentile_fan(
        self,
        df: pd.DataFrame,
        member_label: str = "",
        spaghetti: Optional[List[pd.DataFrame]] = None,
        title: str = "",
    ):
        """Fan chart for p10/p50/p90, optional spaghetti overlay for other members."""
        fig, ax = plt.subplots(figsize=(10, 3.5))
        ax.fill_between(df.index, df["p10"], df["p90"], color="#a6c8ff", alpha=0.35, label="p10–p90")
        ax.plot(df.index, df["p50"], color="#0f62fe", linewidth=2, label="p50")

        if spaghetti:
            for other in spaghetti:
                ax.plot(other.index, other["p50"], color="#9ca3af", alpha=0.4, linewidth=0.8)

        label = f"Member: {member_label}" if member_label else "Percentiles"
        ax.set_ylabel("Ozone (ppb)")
        ax.set_title(title or label)
        self._add_day_10_marker(ax, df.index)
        ax.legend(loc="upper right", fontsize=8)
        fig.tight_layout()
        return fig, ax

    def plot_percentile_spaghetti(
        self,
        member_percentiles: Dict[str, pd.DataFrame],
        title: str = "",
        line_label: str = "p50",
    ):
        """Spaghetti of per-member percentiles (default: p50), plus ensemble envelope.

        Assumes each DataFrame has columns p10/p50/p90 and aligned dates.
        """
        if not member_percentiles:
            fig, ax = plt.subplots(figsize=(10, 3))
            ax.text(0.5, 0.5, "No percentile data", ha="center", va="center", transform=ax.transAxes)
            return fig, ax

        # Align indices
        first = next(iter(member_percentiles.values()))
        index = first.index
        df_concat = pd.DataFrame(
            {m: df[line_label] for m, df in member_percentiles.items()}
        )
        # Per-day ensemble envelope on chosen percentile (p50 by default)
        q10 = df_concat.quantile(0.10, axis=1)
        q50 = df_concat.quantile(0.50, axis=1)
        q90 = df_concat.quantile(0.90, axis=1)

        fig, ax = plt.subplots(figsize=(10, 3.5))
        # Spaghetti
        for m, series in df_concat.items():
            ax.plot(index, series, color="#9ca3af", alpha=0.5, linewidth=0.8)

        ax.fill_between(index, q10, q90, color="#fde68a", alpha=0.4, label="ensemble p10–p90 (p50 across members)")
        ax.plot(index, q50, color="#d97706", linewidth=2, label="ensemble median (p50 across members)")

        ax.set_ylabel("Ozone (ppb)")
        ax.set_title(title or f"Ensemble {line_label} spaghetti")
        self._add_day_10_marker(ax, index)
        ax.legend(loc="upper right", fontsize=8)
        fig.tight_layout()
        return fig, ax

    def plot_percentile_spaghetti_union(
        self,
        member_percentiles: Dict[str, pd.DataFrame],
        title: str = "",
    ):
        """Spaghetti with union envelope (min p10 .. max p90 across members), outlined.

        Highlights a conservative “OR/union” band: the lowest p10 across all members
        to the highest p90 across all members for each forecast day. Outlines the
        upper boundary to make the worst-case trajectory easy to spot.
        """
        if not member_percentiles:
            fig, ax = plt.subplots(figsize=(10, 3))
            ax.text(0.5, 0.5, "No percentile data", ha="center", va="center", transform=ax.transAxes)
            return fig, ax

        first = next(iter(member_percentiles.values()))
        index = first.index

        # Align and collect p10/p50/p90 per member
        p10_df = pd.DataFrame({m: df["p10"].reindex(index) for m, df in member_percentiles.items()})
        p50_df = pd.DataFrame({m: df["p50"].reindex(index) for m, df in member_percentiles.items()})
        p90_df = pd.DataFrame({m: df["p90"].reindex(index) for m, df in member_percentiles.items()})

        union_lower = p10_df.min(axis=1)
        union_upper = p90_df.max(axis=1)
        union_mid = p50_df.median(axis=1)

        fig, ax = plt.subplots(figsize=(10, 3.5))
        # Spaghetti (p50)
        for m, series in p50_df.items():
            ax.plot(index, series, color="#9ca3af", alpha=0.5, linewidth=0.8)

        # Union envelope
        ax.fill_between(
            index,
            union_lower,
            union_upper,
            color="#fecdd3",
            alpha=0.35,
            label="union p10–p90 (across members)",
        )
        ax.plot(index, union_upper, color="#be123c", linewidth=2.0, linestyle="-", label="max p90 (union ceiling)")
        ax.plot(index, union_mid, color="#db2777", linewidth=1.5, linestyle="--", label="median p50 (across members)")

        ax.set_ylabel("Ozone (ppb)")
        ax.set_title(title or "Ensemble spaghetti with union envelope")
        self._add_day_10_marker(ax, index)
        ax.legend(loc="upper right", fontsize=8)
        fig.tight_layout()
        return fig, ax

    def plot_cluster_mean_possibility_heatmap(
        self,
        cluster_members: Dict[str, pd.DataFrame],
        title: str = "",
    ):
        """Heatmap of mean category possibilities across members in a cluster.

        Expects each DataFrame to have columns background/moderate/elevated/extreme
        and a DatetimeIndex of forecast dates.
        """
        if not cluster_members:
            fig, ax = plt.subplots(figsize=(8, 3))
            ax.text(0.5, 0.5, "No cluster data", ha="center", va="center", transform=ax.transAxes)
            return fig, ax

        # Align dates across members
        all_dates = sorted(
            set().union(*(df.index.to_pydatetime() for df in cluster_members.values()))
        )
        if not all_dates:
            fig, ax = plt.subplots(figsize=(8, 3))
            ax.text(0.5, 0.5, "No dates", ha="center", va="center", transform=ax.transAxes)
            return fig, ax

        index = _ensure_datetime_index([d.isoformat() for d in all_dates])
        cats = ["background", "moderate", "elevated", "extreme"]

        # Build mean matrix: categories × time
        mat = np.zeros((len(cats), len(index)))
        for j, cat in enumerate(cats):
            values_per_member = []
            for df in cluster_members.values():
                s = df.get(cat)
                if s is None:
                    continue
                s_aligned = s.reindex(index)
                values_per_member.append(s_aligned.to_numpy(dtype=float))
            if values_per_member:
                mat[j, :] = np.nanmean(np.vstack(values_per_member), axis=0)
            else:
                mat[j, :] = np.nan

        fig, ax = plt.subplots(figsize=(10, 3.5))
        y = np.arange(len(cats) + 1)
        x = np.arange(len(index) + 1)
        # Simple colormap from white to category color per row
        for j, cat in enumerate(cats):
            cmap = mcolors.LinearSegmentedColormap.from_list(
                f"{cat}_cmap", ["white", self.category_colors[cat]]
            )
            layer = np.full((len(cats), len(index)), np.nan)
            layer[j, :] = mat[j, :]
            X, Y = np.meshgrid(x, y)
            ax.pcolormesh(
                X,
                Y,
                layer,
                cmap=cmap,
                vmin=0,
                vmax=1,
                shading="auto",
            )

        ax.set_yticks(np.arange(len(cats)) + 0.5)
        ax.set_yticklabels(cats)
        ax.set_xticks(np.arange(len(index)))
        ax.set_xticklabels([d.strftime("%d %b") for d in index], rotation=45, ha="right")
        ax.set_xlabel("Date")
        ax.set_ylabel("Category")
        ax.set_title(title or "Cluster mean category possibilities")
        self._add_day_10_marker(ax, index)
        fig.tight_layout()
        return fig, ax

    def plot_cluster_highrisk_fraction(
        self,
        cluster_members: Dict[str, pd.DataFrame],
        threshold: float = 0.5,
        title: str = "",
    ):
        """Fraction of cluster members in high-risk states over time.

        High-risk is defined as P(elevated + extreme) > threshold for a given day.
        """
        if not cluster_members:
            fig, ax = plt.subplots(figsize=(8, 3))
            ax.text(0.5, 0.5, "No cluster data", ha="center", va="center", transform=ax.transAxes)
            return fig, ax

        # Align dates
        all_dates = sorted(
            set().union(*(df.index.to_pydatetime() for df in cluster_members.values()))
        )
        index = _ensure_datetime_index([d.isoformat() for d in all_dates])

        frac = []
        for d in index:
            count_high = 0
            total = 0
            for df in cluster_members.values():
                if d not in df.index:
                    continue
                row = df.loc[d]
                val = float(row.get("elevated", 0.0)) + float(row.get("extreme", 0.0))
                total += 1
                if val > threshold:
                    count_high += 1
            frac.append(count_high / total if total > 0 else 0.0)

        fig, ax = plt.subplots(figsize=(10, 3))
        ax.plot(index, frac, marker="o", linewidth=1.5, color="#b91c1c")
        ax.set_ylim(0, 1.05)
        ax.set_ylabel("Fraction of members")
        ax.set_xlabel("Date")
        ax.set_title(title or f"Fraction of members with P(elevated+extreme)>{threshold}")
        ax.set_xticks(np.arange(len(index)))
        ax.set_xticklabels([d.strftime("%d %b") for d in index], rotation=45, ha="right")
        self._add_day_10_marker(ax, index)
        fig.tight_layout()
        return fig, ax

    @staticmethod
    def _add_day_10_marker(ax, index: pd.DatetimeIndex) -> None:
        """Add a faint marker at ~10 forecast days to match heatmap cue."""
        step_hours = _estimate_step_hours(index)
        if step_hours and step_hours > 0:
            xpos = 240.0 / step_hours
            if xpos <= len(index):
                ax.axvline(index[int(xpos)], color="grey", linestyle="--", alpha=0.5)
                ax.text(
                    index[int(xpos)],
                    ax.get_ylim()[1],
                    "10 days",
                    ha="left",
                    va="top",
                    fontsize=8,
                    color="darkgray",
                )


# Example (local json_tests):
# plotter = ForecastPlotter()
# df_poss, miss = plotter.load_possibility(Path("data/json_tests/forecast_possibility_heatmap_clyfar000_20251207_0000Z.json"))
# plotter.plot_possibility_stack(df_poss, miss, title="Clyfar000 · 20251207 00Z")
# df_exc = plotter.load_exceedance(Path("data/json_tests/forecast_exceedance_probabilities_20251207_0000Z.json"))
# plotter.plot_exceedance_lines(df_exc, title="Exceedance · 20251207 00Z")
# df_pct = plotter.load_percentiles(Path("data/json_tests/forecast_percentile_scenarios_clyfar000_20251207_0000Z.json"))
# plotter.plot_percentile_fan(df_pct, member_label="clyfar000", title="Percentiles · 20251207 00Z")
