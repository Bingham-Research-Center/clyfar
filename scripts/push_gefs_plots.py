#!/usr/bin/env python3
"""Push GEFS meteogram PNGs to BasinWx, independently of a Clyfar run.

Clyfar's own export path (``export.to_basinwx.export_figures_to_basinwx``) sweeps
heatmaps, meteograms and LLM outlook PDFs together and only runs as the tail of
the 2 h ``submit_clyfar.sh`` Slurm job. That welds the GEFS weather plots to the
ozone model: out of ozone season the model is off, so the meteograms stop too,
even though nothing about them needs the fuzzy inference.

This pushes the meteograms alone. It reads whatever
``run_gefs_clyfar.py --no-clyfar`` has already written and uploads it, so it can
be re-run against an old init without recomputing anything.

Fan-out comes straight from brc_tools rather than ``export.to_basinwx`` so that
this script carries no dependency on the clyfar fan-out work (clyfar#21): the
first URL is the primary and its failure is fatal, the rest are best-effort
mirrors.

Usage:
    python scripts/push_gefs_plots.py --init 2026082718
    python scripts/push_gefs_plots.py --init 2026082718 --dry-run

John Lawson & Claude, August 2026
"""
import argparse
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

LOG = logging.getLogger("push_gefs_plots")

DEFAULT_FIG_ROOT = Path(
    os.environ.get("FIG_ROOT",
                   Path.home() / "basinwx-data" / "clyfar" / "figures"))
DEFAULT_DATA_TYPE = "images"

# meteogram_UB-repr_wind_20260330-0600_GEFS.png -- see utils.create_meteogram_fname
FNAME_TEMPLATE = "meteogram_*_{init}_{model}.png"


def find_meteograms(fig_root, init_dt, model="GEFS"):
    """Return this init's meteogram PNGs, sorted, newest-run-agnostic.

    Only files carrying this init stamp are returned: the meteograms directory
    accumulates every past run, and uploading the lot each cycle would re-push
    thousands of files.
    """
    meteogram_dir = Path(fig_root) / "meteograms"
    if not meteogram_dir.is_dir():
        LOG.error("No meteogram directory at %s", meteogram_dir)
        return []
    pattern = FNAME_TEMPLATE.format(init=init_dt.strftime("%Y%m%d-%H%M"),
                                    model=model)
    return sorted(meteogram_dir.glob(pattern))


def main():
    parser = argparse.ArgumentParser(
        description="Upload GEFS meteogram PNGs for one init time to BasinWx")
    parser.add_argument(
        "--init", required=True,
        type=lambda s: datetime.strptime(s, "%Y%m%d%H"),
        help="Forecast init time, YYYYMMDDHH")
    parser.add_argument(
        "--fig-root", default=str(DEFAULT_FIG_ROOT),
        help=f"Figure root holding meteograms/ (default: {DEFAULT_FIG_ROOT})")
    parser.add_argument(
        "--model", default="GEFS", help="Model tag in the filename (default: GEFS)")
    parser.add_argument(
        "--data-type", default=DEFAULT_DATA_TYPE,
        help=f"Upload bucket (default: {DEFAULT_DATA_TYPE})")
    parser.add_argument(
        "--server-url", default=None,
        help="Single-host override (default: fan out to every configured site)")
    parser.add_argument(
        "--dry-run", action="store_true", help="List what would upload, then stop")
    parser.add_argument(
        "--allow-empty", action="store_true",
        help="Exit 0 when no meteogram matches, instead of failing")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S")

    pngs = find_meteograms(args.fig_root, args.init, args.model)
    if not pngs:
        msg = (f"No {args.model} meteograms for init "
               f"{args.init:%Y-%m-%d %H:%M}Z under {args.fig_root}/meteograms")
        if args.allow_empty:
            LOG.warning("%s -- continuing (--allow-empty)", msg)
            return 0
        # Loud by default: an empty push almost always means the GEFS stage
        # failed upstream, and silence there is what hid the 2026 outage.
        LOG.error(msg)
        return 1

    LOG.info("Found %d meteogram(s) for init %s", len(pngs),
             args.init.strftime("%Y%m%d-%H%M"))
    for p in pngs:
        LOG.info("  %s (%.1f MB)", p.name, p.stat().st_size / 1e6)

    if args.dry_run:
        LOG.info("Dry run -- nothing uploaded")
        return 0

    try:
        from brc_tools.download.push_data import load_config_urls, send_json_to_all
    except ImportError as exc:
        LOG.error("Cannot import brc_tools (%s). Install it: "
                  "pip install -e /path/to/brc-tools", exc)
        return 1

    api_key, config_urls = load_config_urls()
    urls = [args.server_url.rstrip("/")] if args.server_url else config_urls
    LOG.info("Uploading to %d host(s): primary=%s mirrors=%s",
             len(urls), urls[0], urls[1:])

    failures = 0
    for png in pngs:
        try:
            send_json_to_all(urls, str(png), args.data_type, api_key)
        except Exception as exc:
            # send_json_to_all raises only when the PRIMARY host fails.
            LOG.error("Primary upload failed for %s: %s", png.name, exc)
            failures += 1

    if failures:
        LOG.error("%d/%d meteogram(s) failed on the primary host",
                  failures, len(pngs))
        return 1

    LOG.info("Uploaded %d meteogram(s) to %s", len(pngs), args.data_type)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
