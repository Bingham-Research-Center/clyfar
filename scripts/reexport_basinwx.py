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
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

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


def _guess_run_dir(base_path: Path, init_dt: datetime) -> Optional[Path]:
    """Return base/init folder if one exists (handles both HHMMZ and HH00Z names)."""
    candidates = [
        base_path / init_dt.strftime("%Y%m%d_%H%MZ"),
        base_path / init_dt.strftime("%Y%m%d_%HZ"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


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
        help=(
            "Base data directory passed as --data-root to run_gefs_clyfar.py "
            "(default: ./data). Used for lookup fallbacks."
        ),
    )
    parser.add_argument(
        "--run-dir",
        default=None,
        help=(
            "Run-specific directory (e.g., data/20251218_1800Z). "
            "If omitted, the script tries to locate it under --data-root."
        ),
    )
    parser.add_argument(
        "--dailymax-dir",
        default=None,
        help="Directory containing *_dailymax.parquet files (defaults to <data-root>/dailymax).",
    )
    parser.add_argument(
        "-f",
        "--fig-root",
        default=None,
        help="Directory holding figures to upload. Defaults to <run-dir>/figures or <data-root>/figures.",
    )
    parser.add_argument(
        "-e",
        "--export-dir",
        default=None,
        help="Destination for regenerated JSON (defaults to <data-root>/basinwx_export).",
    )
    parser.add_argument(
        "--case-root",
        default="data/json_tests",
        help=(
            "Root folder for CASE_YYYYMMDD_HHMMZ directories "
            "(used when --sync-case is provided)."
        ),
    )
    parser.add_argument(
        "--sync-case",
        action="store_true",
        help="Copy regenerated JSON files into data/json_tests/CASE_<init>/ subfolders.",
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
    run_dir = (
        Path(args.run_dir).expanduser().resolve()
        if args.run_dir
        else _guess_run_dir(data_root, init_dt)
    )

    if run_dir:
        logger.info("Using run directory: %s", run_dir)
    else:
        logger.info("No run directory provided/detected; using data root fallbacks (%s)", data_root)

    if args.dailymax_dir:
        dailymax_dir = Path(args.dailymax_dir).expanduser().resolve()
    elif run_dir and (run_dir / "dailymax").exists():
        dailymax_dir = run_dir / "dailymax"
    else:
        dailymax_dir = data_root / "dailymax"

    if not dailymax_dir.exists():
        raise FileNotFoundError(
            f"Could not locate daily-max directory. "
            f"Tried {dailymax_dir}. Specify --dailymax-dir."
        )

    if args.export_dir:
        export_dir = Path(args.export_dir).expanduser()
    elif run_dir:
        export_dir = run_dir / "basinwx_export"
    else:
        export_dir = data_root / "basinwx_export"
    export_dir = export_dir.resolve()

    if args.fig_root:
        fig_root = Path(args.fig_root).expanduser()
    elif run_dir and (run_dir / "figures").exists():
        fig_root = run_dir / "figures"
    else:
        fig_root = data_root / "figures"
    fig_root = fig_root.resolve()

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

        if args.sync_case:
            case_root = Path(args.case_root).expanduser().resolve()
            case_dir = case_root / f"CASE_{init_dt.strftime('%Y%m%d_%H%MZ')}"
            (case_dir / "possibilities").mkdir(parents=True, exist_ok=True)
            (case_dir / "percentiles").mkdir(parents=True, exist_ok=True)
            (case_dir / "probs").mkdir(parents=True, exist_ok=True)

            def _copy_many(files, dest):
                for src in files:
                    src_path = Path(src)
                    target = dest / src_path.name
                    shutil.copy2(src_path, target)

            _copy_many(results.get("possibility", []), case_dir / "possibilities")
            _copy_many(results.get("percentiles", []), case_dir / "percentiles")
            _copy_many(results.get("exceedance", []), case_dir / "probs")
            logger.info("Synced JSON outputs into %s", case_dir)
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
