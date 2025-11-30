"""Export Clyfar forecast data to BasinWx website.

Generates 3 data products (63 JSON files total per forecast run):
1. Possibility heatmaps (31 files): Per-member 4×N grids of category possibilities
2. Exceedance probabilities (1 file): Ensemble consensus for threshold exceedance
3. Percentile scenarios (31 files): Defuzzified ppb values per member

Environment variables required:
- DATA_UPLOAD_API_KEY: API key for BasinWx upload endpoint
- BASINWX_API_URL: Base URL for BasinWx API (default: https://basinwx.com)

Created by: John Lawson & Claude
Note: Multi-agent development environment - verify changes across repos
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Optional, List
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import numpy as np
import math

# Import from brc-tools (installed as editable package)
try:
    from brc_tools.download.push_data import send_json_to_server
except ImportError as e:
    raise ImportError(
        "Cannot import brc_tools. Ensure it's installed: "
        "pip install -e /path/to/brc-tools"
    ) from e

logger = logging.getLogger(__name__)


def _sanitize_for_json(obj):
    """Convert NaN/Inf floats to None for valid JSON serialization.

    JSON spec doesn't allow NaN or Infinity. This function is used as
    the `default` parameter for json.dump() to convert these values to null.
    """
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
    if isinstance(obj, np.floating):
        if np.isnan(obj) or np.isinf(obj):
            return None
        return float(obj)
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.ndarray):
        return [_sanitize_for_json(x) for x in obj.tolist()]
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def _sanitize_list(lst):
    """Sanitize a list to replace NaN/Inf with None."""
    return [None if (isinstance(x, (float, np.floating)) and
            (math.isnan(x) if isinstance(x, float) else np.isnan(x)))
            else x for x in lst]


# Ozone category thresholds (ppb) - from fis/v0p9.py:78-117
OZONE_CATEGORIES = {
    "background": {"min": 20, "peak_start": 30, "peak_end": 40, "max": 50},
    "moderate": {"min": 40, "peak_start": 50, "peak_end": 60, "max": 70},
    "elevated": {"min": 50, "peak_start": 60, "peak_end": 75, "max": 90},
    "extreme": {"min": 60, "peak_start": 75, "peak_end": 90, "max": 125}
}

# Default exceedance thresholds (ppb) - start of "peak" membership
EXCEEDANCE_THRESHOLDS = [30, 50, 60, 75]  # background, moderate, elevated, extreme


def export_possibility_heatmaps(
    dailymax_df_dict: Dict[str, pd.DataFrame],
    init_dt: datetime,
    output_dir: str,
    upload: bool = True
) -> List[str]:
    """Export per-member possibility heatmaps (31 JSON files).

    Each file contains a 4×N grid where:
    - 4 rows = ozone categories (background, moderate, elevated, extreme)
    - N columns = forecast days (~15-17 days)
    - Values = possibility (0.0 to 1.0)

    Args:
        dailymax_df_dict: Dictionary mapping member names to daily-max DataFrames
        init_dt: Forecast initialization datetime (naive UTC)
        output_dir: Directory to save JSON files
        upload: If True, upload to BasinWx API

    Returns:
        List of file paths created
    """
    os.makedirs(output_dir, exist_ok=True)
    created_files = []

    init_str = init_dt.strftime('%Y%m%d_%H%MZ')
    categories = ["background", "moderate", "elevated", "extreme"]

    for member_name, df in dailymax_df_dict.items():
        # Extract possibility columns
        heatmap_data = {}
        for cat in categories:
            if cat not in df.columns:
                logger.warning(f"Category '{cat}' not in {member_name} DataFrame")
                heatmap_data[cat] = [0.0] * len(df)
            else:
                # Convert to list, handle NaN
                values = df[cat].fillna(0.0).tolist()
                heatmap_data[cat] = values

        # Get forecast dates (index as ISO strings)
        forecast_dates = df.index.strftime('%Y-%m-%d').tolist()

        payload = {
            "metadata": {
                "init_datetime": init_dt.isoformat() + "Z",
                "member": member_name,
                "product_type": "possibility_heatmap",
                "categories": categories,
                "num_days": len(df),
                "data_source": "Clyfar v0.9.5",
                "units": "possibility (0-1)"
            },
            "forecast_dates": forecast_dates,
            "heatmap": heatmap_data
        }

        filename = f"forecast_possibility_heatmap_{member_name}_{init_str}.json"
        filepath = os.path.join(output_dir, filename)

        with open(filepath, 'w') as f:
            json.dump(payload, f, indent=2, default=_sanitize_for_json)

        logger.info(f"Created {filename} ({len(df)} days)")
        created_files.append(filepath)

        # Upload to BasinWx
        if upload:
            _upload_to_basinwx(filepath, "forecasts")

    return created_files


def export_exceedance_probabilities(
    dailymax_df_dict: Dict[str, pd.DataFrame],
    init_dt: datetime,
    output_dir: str,
    thresholds: Optional[List[float]] = None,
    percentile_col: str = "ozone_50pc",
    upload: bool = True
) -> str:
    """Export ensemble exceedance probabilities (1 JSON file).

    For each threshold and forecast day, compute the fraction of ensemble
    members whose ozone forecast exceeds that threshold.

    Args:
        dailymax_df_dict: Dictionary mapping member names to daily-max DataFrames
        init_dt: Forecast initialization datetime (naive UTC)
        output_dir: Directory to save JSON file
        thresholds: Ozone thresholds in ppb (default: [30, 50, 60, 75])
        percentile_col: Which percentile column to use for exceedance (default: ozone_50pc)
        upload: If True, upload to BasinWx API

    Returns:
        File path created
    """
    os.makedirs(output_dir, exist_ok=True)

    if thresholds is None:
        thresholds = EXCEEDANCE_THRESHOLDS

    init_str = init_dt.strftime('%Y%m%d_%H%MZ')

    # Collect all member forecasts into a 3D structure
    # Shape: (n_members, n_days)
    member_forecasts = []
    forecast_dates = None

    for member_name, df in dailymax_df_dict.items():
        if percentile_col not in df.columns:
            logger.warning(f"{percentile_col} not in {member_name} DataFrame, skipping")
            continue

        values = df[percentile_col].fillna(np.nan).values
        member_forecasts.append(values)

        if forecast_dates is None:
            forecast_dates = df.index.strftime('%Y-%m-%d').tolist()

    if not member_forecasts:
        raise ValueError("No valid member forecasts found for exceedance calculation")

    # Convert to numpy array: (n_members, n_days)
    forecasts_array = np.array(member_forecasts)
    n_members = len(member_forecasts)

    # Compute exceedance probabilities for each threshold
    exceedance_data = {}
    for threshold in thresholds:
        # For each day, count how many members exceed threshold
        exceeds = forecasts_array > threshold  # Boolean array
        prob_exceed = np.nanmean(exceeds, axis=0)  # Fraction exceeding (0-1)
        exceedance_data[f"{int(threshold)}ppb"] = prob_exceed.tolist()

    payload = {
        "metadata": {
            "init_datetime": init_dt.isoformat() + "Z",
            "product_type": "exceedance_probabilities",
            "num_members": n_members,
            "num_days": len(forecast_dates),
            "thresholds_ppb": thresholds,
            "percentile_used": percentile_col,
            "data_source": "Clyfar v0.9.5",
            "units": "probability (0-1)"
        },
        "forecast_dates": forecast_dates,
        "exceedance_probabilities": exceedance_data
    }

    filename = f"forecast_exceedance_probabilities_{init_str}.json"
    filepath = os.path.join(output_dir, filename)

    with open(filepath, 'w') as f:
        json.dump(payload, f, indent=2, default=_sanitize_for_json)

    logger.info(f"Created {filename} (thresholds: {thresholds} ppb)")

    # Upload to BasinWx
    if upload:
        _upload_to_basinwx(filepath, "forecasts")

    return filepath


def export_percentile_scenarios(
    dailymax_df_dict: Dict[str, pd.DataFrame],
    init_dt: datetime,
    output_dir: str,
    percentiles: Optional[List[int]] = None,
    upload: bool = True
) -> List[str]:
    """Export per-member percentile scenarios (31 JSON files).

    Each file contains defuzzified ozone values (ppb) for different percentiles
    over the forecast period.

    Args:
        dailymax_df_dict: Dictionary mapping member names to daily-max DataFrames
        init_dt: Forecast initialization datetime (naive UTC)
        output_dir: Directory to save JSON files
        percentiles: Percentiles to include (default: [10, 50, 90])
        upload: If True, upload to BasinWx API

    Returns:
        List of file paths created
    """
    os.makedirs(output_dir, exist_ok=True)
    created_files = []

    if percentiles is None:
        percentiles = [10, 50, 90]

    init_str = init_dt.strftime('%Y%m%d_%H%MZ')
    percentile_cols = [f"ozone_{p}pc" for p in percentiles]

    for member_name, df in dailymax_df_dict.items():
        scenario_data = {}

        for pct, col in zip(percentiles, percentile_cols):
            if col not in df.columns:
                logger.warning(f"{col} not in {member_name} DataFrame")
                scenario_data[f"p{pct}"] = [np.nan] * len(df)
            else:
                values = df[col].fillna(np.nan).tolist()
                scenario_data[f"p{pct}"] = values

        # Get forecast dates
        forecast_dates = df.index.strftime('%Y-%m-%d').tolist()

        payload = {
            "metadata": {
                "init_datetime": init_dt.isoformat() + "Z",
                "member": member_name,
                "product_type": "percentile_scenarios",
                "percentiles": percentiles,
                "num_days": len(df),
                "data_source": "Clyfar v0.9.5",
                "units": "ppb (ozone concentration)"
            },
            "forecast_dates": forecast_dates,
            "scenarios": scenario_data
        }

        filename = f"forecast_percentile_scenarios_{member_name}_{init_str}.json"
        filepath = os.path.join(output_dir, filename)

        with open(filepath, 'w') as f:
            json.dump(payload, f, indent=2, default=_sanitize_for_json)

        logger.info(f"Created {filename} ({len(df)} days)")
        created_files.append(filepath)

        # Upload to BasinWx
        if upload:
            _upload_to_basinwx(filepath, "forecasts")

    return created_files


def export_all_products(
    dailymax_df_dict: Dict[str, pd.DataFrame],
    init_dt: datetime,
    output_dir: str,
    upload: bool = True
) -> Dict[str, List[str]]:
    """Export all 3 data products (63 JSON files total).

    Convenience function to generate all forecast products in one call.

    Args:
        dailymax_df_dict: Dictionary mapping member names to daily-max DataFrames
        init_dt: Forecast initialization datetime (naive UTC)
        output_dir: Directory to save JSON files
        upload: If True, upload all files to BasinWx API

    Returns:
        Dictionary with keys 'possibility', 'exceedance', 'percentiles' mapping to file lists
    """
    logger.info(f"Exporting all Clyfar forecast products for {init_dt}")

    results = {
        "possibility": export_possibility_heatmaps(dailymax_df_dict, init_dt, output_dir, upload),
        "exceedance": [export_exceedance_probabilities(dailymax_df_dict, init_dt, output_dir, upload=upload)],
        "percentiles": export_percentile_scenarios(dailymax_df_dict, init_dt, output_dir, upload=upload)
    }

    total_files = len(results["possibility"]) + len(results["exceedance"]) + len(results["percentiles"])
    logger.info(f"Export complete: {total_files} JSON files created")

    return results


def _upload_to_basinwx(filepath: str, data_type: str):
    """Upload JSON file to BasinWx API.

    Args:
        filepath: Path to JSON file
        data_type: Data type for API endpoint (e.g., 'forecasts')
    """
    api_key = os.getenv('DATA_UPLOAD_API_KEY')
    if not api_key:
        logger.warning("DATA_UPLOAD_API_KEY not set, skipping upload")
        return

    api_url = os.getenv('BASINWX_API_URL', 'https://basinwx.com')

    try:
        send_json_to_server(
            server_address=api_url,
            fpath=filepath,
            file_data=data_type,  # data_type is 'forecasts', not JSON content
            API_KEY=api_key
        )
        logger.info(f"Uploaded {os.path.basename(filepath)} to {api_url}")

    except Exception as e:
        logger.error(f"Failed to upload {filepath}: {e}")


def upload_png_to_basinwx(png_path: str) -> bool:
    """Upload a PNG image to BasinWx API.

    Args:
        png_path: Path to PNG file

    Returns:
        True if upload succeeded, False otherwise
    """
    import requests
    import socket

    api_key = os.getenv('DATA_UPLOAD_API_KEY')
    if not api_key:
        logger.warning("DATA_UPLOAD_API_KEY not set, skipping PNG upload")
        return False

    api_url = os.getenv('BASINWX_API_URL', 'https://basinwx.com')
    upload_url = f"{api_url}/api/upload/images"
    hostname = socket.getfqdn()

    try:
        with open(png_path, 'rb') as f:
            files = {'file': (os.path.basename(png_path), f, 'image/png')}
            headers = {'x-api-key': api_key, 'x-client-hostname': hostname}
            response = requests.post(upload_url, files=files, headers=headers)

        if response.status_code == 200:
            logger.info(f"Uploaded PNG: {os.path.basename(png_path)}")
            return True
        else:
            logger.error(f"PNG upload failed ({response.status_code}): {response.text}")
            return False

    except Exception as e:
        logger.error(f"Failed to upload PNG {png_path}: {e}")
        return False


def export_figures_to_basinwx(
    fig_root: str,
    init_dt: datetime,
    upload: bool = True,
    max_workers: int = 8
) -> Dict[str, List[str]]:
    """Export heatmap and meteogram PNGs to BasinWx.

    Looks for figures in:
    - {fig_root}/heatmap/*.png
    - {fig_root}/*.png (meteograms)

    Args:
        fig_root: Root directory containing figures
        init_dt: Forecast initialization datetime
        upload: If True, upload to BasinWx API
        max_workers: Max parallel upload threads (default 8)

    Returns:
        Dictionary with 'heatmaps' and 'meteograms' keys mapping to file lists
    """
    results = {"heatmaps": [], "meteograms": []}
    all_pngs = []

    # Collect heatmap PNGs
    heatmap_dir = os.path.join(fig_root, "heatmap")
    if os.path.isdir(heatmap_dir):
        for f in os.listdir(heatmap_dir):
            if f.endswith('.png'):
                fpath = os.path.join(heatmap_dir, f)
                results["heatmaps"].append(fpath)
                all_pngs.append(fpath)

    # Collect meteogram PNGs in root
    if os.path.isdir(fig_root):
        for f in os.listdir(fig_root):
            if f.endswith('.png') and 'meteogram' in f.lower():
                fpath = os.path.join(fig_root, f)
                results["meteograms"].append(fpath)
                all_pngs.append(fpath)

    logger.info(f"Found {len(results['heatmaps'])} heatmaps, "
                f"{len(results['meteograms'])} meteograms")

    # Parallel upload
    if upload and all_pngs:
        logger.info(f"Uploading {len(all_pngs)} PNGs with {max_workers} workers...")
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(upload_png_to_basinwx, p): p for p in all_pngs}
            success = 0
            for future in as_completed(futures):
                if future.result():
                    success += 1
        logger.info(f"Uploaded {success}/{len(all_pngs)} PNGs")

    return results


# Example usage for integration into run_gefs_clyfar.py:
"""
from export.to_basinwx import export_all_products

# After running Clyfar inference...
if upload_to_website:
    export_all_products(
        dailymax_df_dict=dailymax_df_dict,
        init_dt=init_dt_dict['naive'],
        output_dir=os.path.join(clyfar_data_root, 'basinwx_export'),
        upload=True
    )
"""
