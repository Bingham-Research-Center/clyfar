#!/usr/bin/env python3
"""Export and upload Clyfar's BasinWx products from artifacts already on disk.

This is the export/upload tail of ``submit_clyfar.sh``, lifted out of the inline
heredoc it used to live in. The point is that it needs no model run: it reads
the parquet tables under ``--data-root`` that a previous run wrote and pushes
the products built from them.

That matters for three things the monolith made impossible:

  * re-pushing a run after a host was unreachable, without burning 30 minutes
    of GEFS download and inference to regenerate identical files;
  * back-filling a newly added mirror from runs already computed;
  * pushing one product family while leaving the others alone (``--only``),
    where the old CLYFAR_ENABLE_UPLOAD switch was all-or-nothing.

Usage:
    python scripts/push_clyfar_products.py --init 2026033006
    python scripts/push_clyfar_products.py --init 2026033006 --only images
    python scripts/push_clyfar_products.py --init 2026033006 --no-upload

John Lawson & Claude, August 2026
"""
import argparse
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

LOG = logging.getLogger("push_clyfar_products")

CHOICES = ("forecasts", "images", "llm_outlooks")


def _load_member_tables(data_root, glob_pat, strip_suffix):
    """Load {member_name: DataFrame} from parquet files matching glob_pat."""
    import pandas as pd
    tables = {}
    for parquet in sorted(Path(data_root).glob(glob_pat)):
        tables[parquet.stem.replace(strip_suffix, "")] = pd.read_parquet(parquet)
    return tables


def push_forecasts(args, init_dt):
    """Ozone + clustering + weather JSON -> the `forecasts` bucket."""
    from export.to_basinwx import export_all_products

    dailymax_dir = Path(args.data_root) / "dailymax"
    if not dailymax_dir.is_dir():
        LOG.error("No daily-max directory at %s -- has the model run for this "
                  "init?", dailymax_dir)
        return None

    dailymax = _load_member_tables(dailymax_dir, "clyfar*_dailymax.parquet",
                                   "_dailymax")
    if not dailymax:
        LOG.error("No daily-max parquet files in %s", dailymax_dir)
        return None
    LOG.info("Loaded %d ensemble member(s) from %s", len(dailymax), dailymax_dir)

    full = _load_member_tables(args.data_root, "clyfar*_df.parquet", "_df")
    if not full:
        LOG.warning("No full-resolution member tables; weather exports will be "
                    "skipped")
        full = None

    results = export_all_products(
        dailymax_df_dict=dailymax,
        init_dt=init_dt,
        output_dir=args.export_dir,
        clyfar_df_dict=full,
        upload=args.upload,
    )
    total = sum(len(v) for v in results.values())
    LOG.info("Exported %d forecast file(s)", total)
    for key in ("possibility", "exceedance", "percentiles", "clustering",
                "weather_members", "weather_percentiles"):
        LOG.info("  %-20s %d", key, len(results.get(key, [])))
    return results


def push_figures(args, init_dt, want_images, want_outlooks):
    """PNG figures -> `images`; LLM outlook PDFs -> `llm_outlooks`.

    export_figures_to_basinwx does both in one pass and has no per-bucket
    switch, so when only one is asked for we run it and report what it did
    rather than pretending to have filtered.
    """
    from export.to_basinwx import export_figures_to_basinwx

    results = export_figures_to_basinwx(
        fig_root=args.fig_root,
        init_dt=init_dt,
        upload=args.upload,
        json_tests_root=args.json_tests_root,
    )
    LOG.info("  heatmap PNGs    %d", len(results.get("heatmaps", [])))
    LOG.info("  meteogram PNGs  %d", len(results.get("meteograms", [])))
    LOG.info("  outlook PDFs    %d", len(results.get("outlooks", [])))
    if want_images and not want_outlooks:
        LOG.info("Note: --only images also pushed any outlook PDF for this "
                 "init; export_figures_to_basinwx does not separate them.")
    return results


def main():
    parser = argparse.ArgumentParser(
        description="Export/upload Clyfar products from on-disk artifacts")
    parser.add_argument("--init", required=True,
                        type=lambda s: datetime.strptime(s, "%Y%m%d%H"),
                        help="Forecast init time, YYYYMMDDHH")
    parser.add_argument("--only", action="append", choices=CHOICES,
                        help="Restrict to one product family; repeatable. "
                             "Default: all of them.")
    parser.add_argument("--data-root",
                        default=os.environ.get(
                            "DATA_ROOT",
                            str(Path.home() / "basinwx-data" / "clyfar")))
    parser.add_argument("--fig-root", default=None,
                        help="Default: <data-root>/figures")
    parser.add_argument("--export-dir", default=None,
                        help="Default: <data-root>/basinwx_export")
    parser.add_argument("--json-tests-root", default=None,
                        help="Default: <data-root>/json_tests")
    parser.add_argument("--no-upload", dest="upload", action="store_false",
                        help="Build the files but do not push them")
    args = parser.parse_args()

    args.fig_root = args.fig_root or str(Path(args.data_root) / "figures")
    args.export_dir = args.export_dir or str(Path(args.data_root) / "basinwx_export")
    args.json_tests_root = (args.json_tests_root
                            or str(Path(args.data_root) / "json_tests"))

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(message)s",
                        datefmt="%Y-%m-%d %H:%M:%S")

    wanted = set(args.only) if args.only else set(CHOICES)
    LOG.info("init=%s  upload=%s  products=%s",
             args.init.strftime("%Y%m%d%H"), args.upload,
             ",".join(sorted(wanted)))

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    Path(args.export_dir).mkdir(parents=True, exist_ok=True)

    failed = []

    if "forecasts" in wanted:
        LOG.info("--- forecasts ---")
        if push_forecasts(args, args.init) is None:
            failed.append("forecasts")

    if wanted & {"images", "llm_outlooks"}:
        LOG.info("--- figures / outlooks ---")
        try:
            push_figures(args, args.init,
                         want_images="images" in wanted,
                         want_outlooks="llm_outlooks" in wanted)
        except Exception as exc:
            LOG.error("Figure/outlook export failed: %s", exc)
            failed.append("images/llm_outlooks")

    if failed:
        LOG.error("FAILED: %s", ", ".join(failed))
        return 1
    LOG.info("All requested products complete for init %s",
             args.init.strftime("%Y%m%d%H"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
