#!/usr/bin/env python3
"""Deep-dive snow analysis: representative GEFS vs representative observations.

Default target case is the historical mask-diagnostics case:
  - GEFS init: 2025-01-25 00Z (YYYYMMDDHH: 2025012500)

The script reads already-exported snow parquet files from ``data/<INIT_%Y%m%d_%H%MZ>/``,
builds a local-day representative forecast summary (p10/p50/p90 across members),
and compares against representative observed snow (daily, station-reduced) using the
same core observation reduction in ``preprocessing.representative_obs.do_repval_snow``.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
import sys
from typing import Dict, Iterable, Optional

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytz

# Allow running the script directly from repo root without editable install.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from obs.obsdata import ObsData
from preprocessing.representative_obs import do_repval_snow
from utils.lookups import snow_stids


LOCAL_TZ = "America/Denver"


def _parse_init(init_str: str) -> dt.datetime:
    return dt.datetime.strptime(init_str, "%Y%m%d%H")


def _run_label(init_dt: dt.datetime) -> str:
    return init_dt.strftime("%Y%m%d_%H%MZ")


def _discover_snow_member_files(run_dir: Path, run_label: str) -> Dict[str, Path]:
    files = sorted(run_dir.glob(f"{run_label}_snow_*_df.parquet"))
    members: Dict[str, Path] = {}
    for path in files:
        stem = path.stem
        member = stem.split("_snow_")[-1].replace("_df", "")
        members[member] = path
    return members


def _load_forecast_member_series(
    member_files: Dict[str, Path], members_keep: Optional[Iterable[str]] = None
) -> Dict[str, pd.Series]:
    keep_set = None if members_keep is None else set(members_keep)
    out: Dict[str, pd.Series] = {}
    for member, path in member_files.items():
        if keep_set is not None and member not in keep_set:
            continue
        df = pd.read_parquet(path)
        if "sde" not in df.columns:
            raise KeyError(f"{path} is missing expected snow column 'sde'")
        series = df["sde"].copy()
        series.index = pd.to_datetime(series.index)
        out[member] = series
    return out


def _daily_local_max(series: pd.Series, tz_name: str) -> pd.Series:
    idx_utc = pd.to_datetime(series.index).tz_localize("UTC")
    local = series.copy()
    local.index = idx_utc.tz_convert(tz_name)
    daily = local.resample("D").max()
    daily.index = daily.index.tz_localize(None)
    return daily


def _build_forecast_representative(
    member_series: Dict[str, pd.Series], tz_name: str
) -> pd.DataFrame:
    daily_frames = {}
    for member, series in member_series.items():
        daily_frames[member] = _daily_local_max(series, tz_name)
    daily_df = pd.DataFrame(daily_frames).sort_index()
    rep = pd.DataFrame(index=daily_df.index)
    rep["forecast_p10"] = daily_df.quantile(0.10, axis=1, interpolation="linear")
    rep["forecast_p50"] = daily_df.quantile(0.50, axis=1, interpolation="linear")
    rep["forecast_p90"] = daily_df.quantile(0.90, axis=1, interpolation="linear")
    rep["forecast_mean"] = daily_df.mean(axis=1)
    rep["n_members"] = daily_df.notna().sum(axis=1).astype(int)
    return rep


def _fetch_obs_representative(
    start_utc: pd.Timestamp, end_utc: pd.Timestamp, tz_name: str
) -> pd.Series:
    local_tz = pytz.timezone(tz_name)
    start_local = start_utc.tz_convert(local_tz).to_pydatetime()
    end_local = end_utc.tz_convert(local_tz).to_pydatetime()
    obs = ObsData(start_local, end_local, "snow", stids=snow_stids, qc="all")
    rep_df = do_repval_snow(obs.df, snow_stids)
    rep = rep_df["snow_depth"].copy()
    rep.index = pd.to_datetime(rep.index)
    rep = rep.sort_index()
    return rep


def _load_obs_representative_from_file(path: Path) -> pd.Series:
    if path.suffix.lower() == ".parquet":
        df = pd.read_parquet(path)
    else:
        df = pd.read_csv(path)

    if "time" in df.columns and not isinstance(df.index, pd.DatetimeIndex):
        df = df.set_index("time")
    df.index = pd.to_datetime(df.index)

    if "snow_depth" in df.columns and "stid" in df.columns:
        if df.index.tz is None:
            df.index = df.index.tz_localize("UTC")
        rep_df = do_repval_snow(df, snow_stids)
        rep = rep_df["snow_depth"].copy()
        rep.index = pd.to_datetime(rep.index)
        return rep.sort_index()

    if "snow_depth" not in df.columns:
        raise KeyError(
            f"{path} must contain 'snow_depth' column (or stid+snow_depth for raw obs)."
        )

    rep = df["snow_depth"].copy()
    if getattr(rep.index, "tz", None) is not None:
        rep.index = rep.index.tz_convert(LOCAL_TZ).tz_localize(None)
    return rep.sort_index()


def _compute_metrics(
    rep_fcst: pd.DataFrame, rep_obs: pd.Series, init_dt: dt.datetime, tz_name: str
) -> tuple[pd.DataFrame, pd.DataFrame, Dict[str, float]]:
    merged = pd.concat(
        [rep_fcst[["forecast_p10", "forecast_p50", "forecast_p90"]], rep_obs.rename("obs")],
        axis=1,
    ).dropna(subset=["forecast_p50", "obs"])
    merged.index = pd.to_datetime(merged.index)

    init_local_day = (
        pd.Timestamp(init_dt).tz_localize("UTC").tz_convert(tz_name).tz_localize(None).normalize()
    )
    lead_days = (merged.index - init_local_day) / pd.Timedelta(days=1)
    merged["lead_day"] = np.floor(lead_days).astype(int)
    merged["bias"] = merged["forecast_p50"] - merged["obs"]
    merged["abs_error"] = merged["bias"].abs()
    merged["sq_error"] = merged["bias"] ** 2

    by_lead = (
        merged.groupby("lead_day", dropna=True)
        .agg(
            n_days=("bias", "count"),
            mean_bias_mm=("bias", "mean"),
            mae_mm=("abs_error", "mean"),
            rmse_mm=("sq_error", lambda x: float(np.sqrt(np.mean(x)))),
        )
        .reset_index()
    )

    summary = {
        "n_overlap_days": int(len(merged)),
        "mean_bias_mm": float(merged["bias"].mean()) if len(merged) else np.nan,
        "mae_mm": float(merged["abs_error"].mean()) if len(merged) else np.nan,
        "rmse_mm": float(np.sqrt(merged["sq_error"].mean())) if len(merged) else np.nan,
    }
    return merged, by_lead, summary


def _plot_case(
    init_dt: dt.datetime,
    rep_fcst: pd.DataFrame,
    rep_obs: Optional[pd.Series],
    by_lead: pd.DataFrame,
    summary: Dict[str, float],
    out_png: Path,
) -> None:
    fig, (ax0, ax1) = plt.subplots(2, 1, figsize=(12, 8), constrained_layout=True)

    x = rep_fcst.index
    ax0.fill_between(
        x,
        rep_fcst["forecast_p10"],
        rep_fcst["forecast_p90"],
        color="#8fbcd4",
        alpha=0.35,
        label="GEFS representative p10-p90",
    )
    ax0.plot(x, rep_fcst["forecast_p50"], color="#176087", lw=2.2, label="GEFS representative p50")
    if rep_obs is not None and not rep_obs.empty:
        ax0.plot(rep_obs.index, rep_obs.values, color="#b2392f", lw=2.0, label="Observed representative")

    ax0.set_title(f"Snow Representative Deep-Dive: init {init_dt:%Y-%m-%d %HZ}")
    ax0.set_ylabel("Snow depth (mm)")
    ax0.grid(alpha=0.25)
    ax0.legend(loc="best", frameon=False)

    if len(by_lead):
        ax1.bar(by_lead["lead_day"], by_lead["mean_bias_mm"], color="#3e6f8f", alpha=0.85, label="Mean bias")
        ax1.plot(by_lead["lead_day"], by_lead["mae_mm"], color="#b2392f", marker="o", label="MAE")
        ax1.set_xlabel("Lead day (local)")
        ax1.set_ylabel("Error (mm)")
        ax1.grid(alpha=0.25)
        ax1.legend(loc="best", frameon=False)
    else:
        ax1.text(
            0.02,
            0.55,
            "No overlapping observed representative days found.",
            transform=ax1.transAxes,
            fontsize=11,
        )
        ax1.axis("off")

    fig.text(
        0.01,
        0.01,
        (
            f"Summary: overlap_days={summary.get('n_overlap_days', 0)}, "
            f"mean_bias_mm={summary.get('mean_bias_mm', np.nan):.2f}, "
            f"mae_mm={summary.get('mae_mm', np.nan):.2f}, "
            f"rmse_mm={summary.get('rmse_mm', np.nan):.2f}"
        ),
        fontsize=9,
    )
    fig.savefig(out_png, dpi=150)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create snow representative forecast-vs-observed deep-dive diagnostics."
    )
    parser.add_argument("--init", default="2025012500", help="Initialization time YYYYMMDDHH.")
    parser.add_argument("--data-root", default="data", help="Root directory containing run folders.")
    parser.add_argument(
        "--out-dir",
        default="figures/v1_0_snow_deep_dive",
        help="Directory for figure and metrics outputs.",
    )
    parser.add_argument(
        "--members",
        default="",
        help="Optional comma-separated member list (e.g., p01,p02). Default uses all discovered members.",
    )
    parser.add_argument(
        "--obs-file",
        default="",
        help="Optional CSV/parquet with observed snow representative or raw stid+snow_depth data.",
    )
    parser.add_argument(
        "--allow-no-obs",
        action="store_true",
        help="Allow forecast-only output if observation retrieval fails.",
    )
    parser.add_argument("--timezone", default=LOCAL_TZ, help="Local timezone name (default America/Denver).")
    args = parser.parse_args()

    init_dt = _parse_init(args.init)
    run_label = _run_label(init_dt)
    run_dir = Path(args.data_root) / run_label
    out_dir = Path(args.out_dir) / run_label
    out_dir.mkdir(parents=True, exist_ok=True)

    if not run_dir.exists():
        raise FileNotFoundError(
            f"Run directory not found: {run_dir}. "
            f"Generate data first for init {args.init} (e.g., run_gefs_clyfar.py ...)."
        )

    member_files = _discover_snow_member_files(run_dir, run_label)
    if not member_files:
        raise FileNotFoundError(f"No snow parquet files found in {run_dir} for label {run_label}.")

    members_keep = [m.strip() for m in args.members.split(",") if m.strip()] or None
    member_series = _load_forecast_member_series(member_files, members_keep=members_keep)
    if not member_series:
        raise ValueError("No member series selected for analysis.")

    rep_fcst = _build_forecast_representative(member_series, tz_name=args.timezone)

    # Observation window spans forecast period, padded by a day to avoid boundary misses.
    fcst_start_utc = pd.Timestamp(min(s.index.min() for s in member_series.values()), tz="UTC")
    fcst_end_utc = pd.Timestamp(max(s.index.max() for s in member_series.values()), tz="UTC")
    rep_obs = pd.Series(dtype=float)
    obs_source = "none"
    try:
        if args.obs_file:
            rep_obs = _load_obs_representative_from_file(Path(args.obs_file))
            obs_source = f"file:{args.obs_file}"
        else:
            rep_obs = _fetch_obs_representative(
                fcst_start_utc - pd.Timedelta(days=1),
                fcst_end_utc + pd.Timedelta(days=1),
                tz_name=args.timezone,
            )
            obs_source = "synoptic_api"
    except Exception as exc:
        if not args.allow_no_obs:
            raise RuntimeError(
                "Observation representative retrieval failed. "
                "Provide --obs-file or rerun with --allow-no-obs."
            ) from exc
        print(f"[WARN] Observation retrieval failed, continuing forecast-only: {type(exc).__name__}: {exc}")

    merged, by_lead, summary = _compute_metrics(rep_fcst, rep_obs, init_dt, tz_name=args.timezone)

    out_png = out_dir / f"snow_repr_vs_obs_{run_label}.png"
    _plot_case(
        init_dt=init_dt,
        rep_fcst=rep_fcst,
        rep_obs=rep_obs if len(rep_obs) else None,
        by_lead=by_lead,
        summary=summary,
        out_png=out_png,
    )

    rep_fcst.to_csv(out_dir / "forecast_representative_daily.csv", index_label="date")
    if len(rep_obs):
        rep_obs.to_frame("obs_representative").to_csv(out_dir / "obs_representative_daily.csv", index_label="date")
    merged.to_csv(out_dir / "comparison_daily.csv", index_label="date")
    by_lead.to_csv(out_dir / "metrics_by_lead_day.csv", index=False)

    meta = {
        "init": args.init,
        "run_label": run_label,
        "run_dir": str(run_dir),
        "obs_source": obs_source,
        "timezone": args.timezone,
        "members_used": sorted(member_series.keys()),
        "summary_metrics": summary,
        "output_figure": str(out_png),
    }
    (out_dir / "summary.json").write_text(json.dumps(meta, indent=2))

    print(f"[OK] Wrote deep-dive outputs to {out_dir}")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
