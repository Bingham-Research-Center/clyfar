#!/usr/bin/env python3
"""Quick PRMSL probe for the GEFS helper.

Fetches a handful of forecast hours with GEFSData.fetch_pressure and prints
basic diagnostics (min/max/NaN counts) so we can spot all-NaN failures fast.
"""

from __future__ import annotations

import argparse
import datetime as dt
import logging
from typing import Iterable, List

import numpy as np

from nwp.gefsdata import GEFSData


def _parse_init(value: str) -> dt.datetime:
    try:
        return dt.datetime.strptime(value, "%Y%m%d%H")
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"Expected init in YYYYMMDDHH format, got '{value}'"
        ) from exc


def _parse_hours(values: Iterable[int]) -> List[int]:
    hours = sorted({int(v) for v in values})
    if not hours:
        raise argparse.ArgumentTypeError("At least one forecast hour is required.")
    return hours


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Check GEFS PRMSL downloads for a few forecast hours.",
    )
    parser.add_argument(
        "-i",
        "--init",
        type=_parse_init,
        required=True,
        help="Forecast init time in YYYYMMDDHH (UTC).",
    )
    parser.add_argument(
        "-m",
        "--member",
        default="c00",
        help="GEFS member to probe (default: c00).",
    )
    parser.add_argument(
        "-p",
        "--product",
        default="atmos.25",
        help="GEFS product string (default: atmos.25).",
    )
    parser.add_argument(
        "-f",
        "--hours",
        type=int,
        nargs="+",
        default=[0, 6, 12, 24, 48],
        help="Forecast hours to sample (default: 0 6 12 24 48).",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level. Default: INFO.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(message)s",
    )
    init_time = args.init
    hours = _parse_hours(args.hours)
    var_name = getattr(GEFSData, "_PRESSURE_VAR_NAME", "prmsl")

    logging.info(
        "Checking PRMSL for %s with member %s (%s) over %d hours",
        init_time.strftime("%Y-%m-%d %H:%M"),
        args.member,
        args.product,
        len(hours),
    )
    failures = 0
    for hour in hours:
        try:
            ds = GEFSData.fetch_pressure(
                init_time,
                hour,
                product=args.product,
                member=args.member,
                remove_grib=True,
            )
        except Exception as exc:
            failures += 1
            logging.error("f%03d failed: %s", hour, exc)
            continue

        data = ds[var_name].values
        data = np.asarray(data)
        total = data.size
        finite_mask = np.isfinite(data)
        valid_values = data[finite_mask]
        nan_count = int(total - finite_mask.sum())

        if valid_values.size:
            min_val = float(valid_values.min() / 100.0)
            max_val = float(valid_values.max() / 100.0)
        else:
            min_val = float("nan")
            max_val = float("nan")

        logging.info(
            "f%03d stats: min %.1f hPa | max %.1f hPa | NaNs %d/%d",
            hour,
            min_val,
            max_val,
            nan_count,
            total,
        )

    if failures:
        logging.warning(
            "Finished with %d/%d failures", failures, len(hours)
        )
        return 2 if failures == len(hours) else 1

    logging.info("All requested hours succeeded.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
