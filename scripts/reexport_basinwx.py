#!/usr/bin/env python3
"""Regenerate BasinWx export artifacts from existing daily-max parquet files.

This script is useful when :mod:`run_gefs_clyfar.py` completes the heavy lifting
(GEFS download, FIS inference, parquet saves) but fails during the export phase.
It reloads the saved daily-max tables and re-runs the JSON + PNG export helpers
without re-processing the ensemble.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict

import pandas as pd

# Ensure repo root is on sys.path when invoked as a script
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from export.to_basinwx import export_all_products, export_figures_to_basinwx

logger = logging.getLogger(__name__)


def _load_dailymax_tables(dailymax_dir: Path) -> Dict[str, pd.DataFrame]:
    """Load saved daily-max parquet tables into the structure expected by exporters."""
    if not dailymax_dir.exists():
        raise FileNotFoundError(f"Daily-max directory not found: {dailymax_dir}")

    dailymax_df_dict: Dict[str, pd.DataFrame] = {}
    parquet_files = sorted(dailymax_dir.glob("*_dailymax.parquet"))

    if not parquet_files:
        raise FileNotFoundError(
            f"No *_dailymax.parquet files found under {dailymax_dir}"
        )

    for parquet_path in parquet_files:
        member_name = parquet_path.stem.replace("_dailymax", "")
        try:
            df = pd.read_parquet(parquet_path)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("Failed to read %s: %s", parquet_path, exc)
            continue

        if df.empty:
            logger.warning("Skipping empty daily-max table: %s", parquet_path)
            continue

        if not isinstance(df.index, pd.DatetimeIndex):
            idx = df.index if "time" not in df.columns else df["time"]
            df.index = pd.to_datetime(idx)

        df = df.sort_index()
        dailymax_df_dict[member_name] = df

    if not dailymax_df_dict:
        raise RuntimeError("No valid daily-max tables could be loaded")

    logger.info("Loaded %d daily-max tables from %s", len(dailymax_df_dict), dailymax_dir)
    return dailymax_df_dict


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Regenerate BasinWx export artifacts using saved daily-max tables."
    )
    parser.add_argument(
        "-i",
        "--init-time",
        required=True,
        help="Initialization time in YYYYMMDDHH (UTC) used for the original run.",
    )
    parser.add_argument(
        "-d",
        "--data-root",
        default="./data",
        help="Path passed as --data-root to run_gefs_clyfar.py (default: ./data).",
    )
    parser.add_argument(
        "--dailymax-dir",
        default=None,
        help="Directory containing *_dailymax.parquet files (defaults to <data-root>/dailymax).",
    )
    parser.add_argument(
        "-f",
        "--fig-root",
        default="./figures",
        help="Path passed as --fig-root (for locating PNGs).",
    )
    parser.add_argument(
        "-e",
        "--export-dir",
        default=None,
        help="Destination for regenerated JSON (defaults to <data-root>/basinwx_export).",
    )
    parser.add_argument(
        "--skip-json",
        action="store_true",
        help="Skip JSON exports (possibility/percentile/exceedance).",
    )
    parser.add_argument(
        "--skip-figures",
        action="store_true",
        help="Skip PNG uploads; only rebuild JSON when combined with --upload.",
    )
    parser.add_argument(
        "--upload",
        action="store_true",
        help="Upload regenerated files to BasinWx (requires DATA_UPLOAD_API_KEY).",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=8,
        help="Max worker threads for uploads.",
    )
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    args = parse_args()
    init_dt = datetime.strptime(args.init_time, "%Y%m%d%H")

    data_root = Path(args.data_root).expanduser().resolve()
    dailymax_dir = (
        Path(args.dailymax_dir).expanduser().resolve()
        if args.dailymax_dir
        else data_root / "dailymax"
    )
    export_dir = (
        Path(args.export_dir).expanduser().resolve()
        if args.export_dir
        else data_root / "basinwx_export"
    )
    fig_root = Path(args.fig_root).expanduser().resolve()

    dailymax_df_dict = _load_dailymax_tables(dailymax_dir)

    if not args.skip_json:
        export_dir.mkdir(parents=True, exist_ok=True)
        logger.info(
            "Regenerating JSON exports under %s (upload=%s)", export_dir, args.upload
        )
        results = export_all_products(
            dailymax_df_dict=dailymax_df_dict,
            init_dt=init_dt,
            output_dir=str(export_dir),
            upload=args.upload,
            max_workers=args.max_workers,
        )
        total = sum(len(v) for v in results.values())
        logger.info(
            "Created %d JSON files (%d possibility, %d percentiles, %d exceedance)",
            total,
            len(results.get("possibility", [])),
            len(results.get("percentiles", [])),
            len(results.get("exceedance", [])),
        )
    else:
        logger.info("Skipping JSON regeneration per --skip-json flag")

    if not args.skip_figures:
        logger.info(
            "Re-uploading figure assets from %s (upload=%s)", fig_root, args.upload
        )
        fig_results = export_figures_to_basinwx(
            fig_root=str(fig_root),
            init_dt=init_dt,
            upload=args.upload,
            max_workers=args.max_workers,
        )
        logger.info(
            "Processed %d heatmaps + %d meteograms",
            len(fig_results.get("heatmaps", [])),
            len(fig_results.get("meteograms", [])),
        )
    else:
        logger.info("Skipping PNG handling per --skip-figures flag")


if __name__ == "__main__":
    main()
