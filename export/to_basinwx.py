"""Export Clyfar forecast data to BasinWx website.

Generates 6 data products (up to 96 JSON files per forecast run):
1. Possibility heatmaps (31 files): Per-member 4×N grids of category possibilities
2. Exceedance probabilities (1 file): Ensemble consensus for threshold exceedance
3. Percentile scenarios (31 files): Defuzzified ppb values per member
4. GEFS weather members (31 files): Per-member weather time series (snow, mslp, wind, solar, temp)
5. GEFS weather percentiles (1 file): Ensemble p10/p50/p90 for weather variables
6. Scenario clustering summary (1 file): Null-first scenario structure for Ffion/LLM context

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

from utils.scenario_clustering import build_clustering_summary

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


# Precision settings for each variable type (decimal places)
# These reduce JSON size by ~54% while maintaining meaningful precision
PRECISION = {
    # Weather variables
    "snow": 0,      # integer mm (1mm ≈ 0.04 inches)
    "wind": 1,      # 0.1 m/s (0.1 m/s ≈ 0.2 mph)
    "temp": 1,      # 0.1 °C
    "mslp": 1,      # 0.1 hPa
    "solar": 0,     # integer W/m²
    # Ozone and probability
    "ozone": 1,     # 0.1 ppb
    "possibility": 2,  # 0.01 (1% resolution)
    "probability": 2,  # 0.01 (1% resolution)
}


def _round_value(value, var_type: str):
    """Round a value to meaningful precision for its variable type.

    Args:
        value: The numeric value (or None/NaN)
        var_type: Key into PRECISION dict (e.g., "snow", "possibility")

    Returns:
        Rounded float, int (if precision=0), or None
    """
    if value is None:
        return None
    if isinstance(value, (float, np.floating)) and (np.isnan(value) or np.isinf(value)):
        return None

    precision = PRECISION.get(var_type, 2)  # default to 2 decimals
    rounded = round(float(value), precision)

    # Return int if precision is 0 for cleaner JSON
    if precision == 0:
        return int(rounded)
    return rounded


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

# GEFS weather variable metadata
WEATHER_VARIABLES = {
    "snow": {"units": "mm", "description": "Snow depth"},
    "mslp": {"units": "hPa", "description": "Mean sea level pressure"},
    "wind": {"units": "m/s", "description": "Wind speed"},
    "solar": {"units": "W/m²", "description": "Solar radiation"},
    "temp": {"units": "°C", "description": "Temperature"}
}


def _identify_missing_dates(df: pd.DataFrame, categories: List[str]) -> List[str]:
    """Identify dates where all category values are NaN (missing data).

    Args:
        df: DataFrame with date index and category columns
        categories: List of category column names

    Returns:
        List of ISO date strings where data is missing
    """
    missing_dates = []
    for i in range(len(df.index)):
        all_nan = True
        for cat in categories:
            if cat in df.columns:
                val = df[cat].iloc[i]
                # Check if value is NaN
                try:
                    if not (pd.isna(val) or (isinstance(val, float) and math.isnan(val))):
                        all_nan = False
                        break
                except (TypeError, ValueError):
                    all_nan = False
                    break
        if all_nan:
            missing_dates.append(df.index[i].strftime('%Y-%m-%d'))
    return missing_dates


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

    Missing data (all categories NaN for a date) is marked in metadata
    for frontend tooltip display ("time unavailable at present").

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
        # Identify missing dates for tooltip support
        missing_dates = _identify_missing_dates(df, categories)

        # Extract possibility columns with precision rounding
        heatmap_data = {}
        for cat in categories:
            if cat not in df.columns:
                logger.warning(f"Category '{cat}' not in {member_name} DataFrame")
                heatmap_data[cat] = [None] * len(df)  # Use null for missing
            else:
                # Convert to list with meaningful precision (2 decimals)
                heatmap_data[cat] = [
                    _round_value(v, "possibility") for v in df[cat].values
                ]

        # Get forecast dates (index as ISO strings)
        forecast_dates = df.index.strftime('%Y-%m-%d').tolist()

        payload = {
            "metadata": {
                "init_datetime": init_dt.isoformat() + "Z",
                "member": member_name,
                "product_type": "possibility_heatmap",
                "categories": categories,
                "num_days": len(df),
                "num_missing": len(missing_dates),
                "data_source": "Clyfar v0.9.5",
                "units": "possibility (0-1)"
            },
            "forecast_dates": forecast_dates,
            "missing_dates": missing_dates,  # For frontend tooltip: "time unavailable at present"
            "heatmap": heatmap_data
        }

        filename = f"forecast_possibility_heatmap_{member_name}_{init_str}.json"
        filepath = os.path.join(output_dir, filename)

        with open(filepath, 'w') as f:
            json.dump(payload, f, indent=2, default=_sanitize_for_json)

        logger.debug(f"Created {filename} ({len(df)} days, {len(missing_dates)} missing)")
        created_files.append(filepath)

    logger.info(f"Created {len(created_files)} possibility heatmap files")
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

    # Collect valid members and keep a union of all available forecast dates so we can
    # align variable-length inputs (some members occasionally miss the last day or two).
    valid_members: List[pd.DataFrame] = []
    all_dates_index: Optional[pd.DatetimeIndex] = None

    for member_name, df in dailymax_df_dict.items():
        if percentile_col not in df.columns:
            logger.warning(f"{percentile_col} not in {member_name} DataFrame, skipping")
            continue

        valid_members.append(df)
        all_dates_index = df.index if all_dates_index is None else all_dates_index.union(df.index)

    if not valid_members:
        raise ValueError("No valid member forecasts found for exceedance calculation")

    all_dates_index = all_dates_index.sort_values()
    forecast_dates = all_dates_index.strftime('%Y-%m-%d').tolist()

    # Convert to numpy array aligned on the union of dates: (n_members, n_days)
    member_forecasts = []
    for df in valid_members:
        reindexed = df.reindex(all_dates_index)[percentile_col].astype(float)
        member_forecasts.append(reindexed.to_numpy())

    forecasts_array = np.vstack(member_forecasts)
    n_members = len(member_forecasts)

    # Compute exceedance probabilities for each threshold
    exceedance_data = {}
    for threshold in thresholds:
        # For each day, count how many members exceed threshold
        exceeds = forecasts_array > threshold  # Boolean array
        exceeds = np.where(np.isnan(forecasts_array), np.nan, exceeds.astype(float))
        prob_exceed = np.nanmean(exceeds, axis=0)  # Fraction exceeding (0-1)
        # Round probabilities to 2 decimals (1% resolution)
        exceedance_data[f"{int(threshold)}ppb"] = [
            _round_value(v, "probability") for v in prob_exceed
        ]

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
                scenario_data[f"p{pct}"] = [None] * len(df)
            else:
                # Round ozone to 1 decimal (0.1 ppb precision)
                scenario_data[f"p{pct}"] = [
                    _round_value(v, "ozone") for v in df[col].values
                ]

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

        logger.debug(f"Created {filename} ({len(df)} days)")
        created_files.append(filepath)

    logger.info(f"Created {len(created_files)} percentile scenario files")
    return created_files


def export_gefs_weather_members(
    clyfar_df_dict: Dict[str, pd.DataFrame],
    init_dt: datetime,
    output_dir: str,
    upload: bool = True
) -> List[str]:
    """Export per-member GEFS weather time series (31 JSON files).

    Each file contains all 5 weather variables (snow, mslp, wind, solar, temp)
    as hourly time series for one ensemble member.

    Args:
        clyfar_df_dict: Dictionary mapping member names to full-resolution DataFrames
        init_dt: Forecast initialization datetime (naive UTC)
        output_dir: Directory to save JSON files
        upload: If True, upload to BasinWx API

    Returns:
        List of file paths created
    """
    os.makedirs(output_dir, exist_ok=True)
    created_files = []

    init_str = init_dt.strftime('%Y%m%d_%H%MZ')
    weather_vars = list(WEATHER_VARIABLES.keys())

    for member_name, df in clyfar_df_dict.items():
        weather_data = {}

        for var in weather_vars:
            if var not in df.columns:
                logger.warning(f"Weather variable '{var}' not in {member_name} DataFrame")
                weather_data[var] = []
            else:
                # Convert to list with precision rounding per variable type
                weather_data[var] = [
                    _round_value(v, var) for v in df[var].values
                ]

        # Get forecast times (index as ISO strings)
        forecast_times = df.index.strftime('%Y-%m-%dT%H:%M:%SZ').tolist()

        payload = {
            "metadata": {
                "init_datetime": init_dt.isoformat() + "Z",
                "member": member_name,
                "product_type": "gefs_weather",
                "variables": {var: WEATHER_VARIABLES[var] for var in weather_vars},
                "num_timesteps": len(df),
                "data_source": "GEFS via Clyfar v0.9.5"
            },
            "forecast_times": forecast_times,
            "weather": weather_data
        }

        filename = f"forecast_gefs_weather_{member_name}_{init_str}.json"
        filepath = os.path.join(output_dir, filename)

        with open(filepath, 'w') as f:
            json.dump(payload, f, indent=2, default=_sanitize_for_json)

        logger.debug(f"Created {filename} ({len(df)} timesteps)")
        created_files.append(filepath)

    logger.info(f"Created {len(created_files)} GEFS weather member files")
    return created_files


def export_gefs_weather_percentiles(
    clyfar_df_dict: Dict[str, pd.DataFrame],
    init_dt: datetime,
    output_dir: str,
    percentiles: Optional[List[int]] = None,
    upload: bool = True
) -> str:
    """Export ensemble weather percentiles (1 JSON file).

    For each weather variable, compute p10/p50/p90 across the ensemble
    at each timestep.

    Args:
        clyfar_df_dict: Dictionary mapping member names to full-resolution DataFrames
        init_dt: Forecast initialization datetime (naive UTC)
        output_dir: Directory to save JSON file
        percentiles: Percentiles to compute (default: [10, 50, 90])
        upload: If True, upload to BasinWx API

    Returns:
        File path created
    """
    os.makedirs(output_dir, exist_ok=True)

    if percentiles is None:
        percentiles = [10, 50, 90]

    init_str = init_dt.strftime('%Y%m%d_%H%MZ')
    weather_vars = list(WEATHER_VARIABLES.keys())

    # Find common time index across all members
    all_times_index: Optional[pd.DatetimeIndex] = None
    valid_dfs = []
    for member_name, df in clyfar_df_dict.items():
        valid_dfs.append(df)
        all_times_index = df.index if all_times_index is None else all_times_index.union(df.index)

    if not valid_dfs:
        raise ValueError("No valid member DataFrames found for weather percentiles")

    all_times_index = all_times_index.sort_values()
    forecast_times = all_times_index.strftime('%Y-%m-%dT%H:%M:%SZ').tolist()

    # Compute percentiles for each weather variable
    percentile_data = {}
    for var in weather_vars:
        # Stack all members for this variable: (n_members, n_times)
        member_values = []
        for df in valid_dfs:
            if var in df.columns:
                reindexed = df.reindex(all_times_index)[var].astype(float)
                member_values.append(reindexed.to_numpy())

        if not member_values:
            logger.warning(f"No data for weather variable '{var}'")
            percentile_data[var] = {f"p{p}": [] for p in percentiles}
            continue

        values_array = np.vstack(member_values)

        # Compute percentiles at each timestep with precision rounding
        var_percentiles = {}
        for p in percentiles:
            pct_values = np.nanpercentile(values_array, p, axis=0)
            # Round based on variable type
            var_percentiles[f"p{p}"] = [
                _round_value(v, var) for v in pct_values
            ]

        percentile_data[var] = var_percentiles

    payload = {
        "metadata": {
            "init_datetime": init_dt.isoformat() + "Z",
            "product_type": "gefs_weather_percentiles",
            "num_members": len(valid_dfs),
            "num_timesteps": len(forecast_times),
            "percentiles": percentiles,
            "variables": {var: WEATHER_VARIABLES[var] for var in weather_vars},
            "data_source": "GEFS via Clyfar v0.9.5"
        },
        "forecast_times": forecast_times,
        "weather_percentiles": percentile_data
    }

    filename = f"forecast_gefs_weather_percentiles_{init_str}.json"
    filepath = os.path.join(output_dir, filename)

    with open(filepath, 'w') as f:
        json.dump(payload, f, indent=2, default=_sanitize_for_json)

    logger.info(f"Created {filename} ({len(forecast_times)} timesteps, {len(percentiles)} percentiles)")
    return filepath


def export_clustering_summary(
    dailymax_df_dict: Dict[str, pd.DataFrame],
    init_dt: datetime,
    output_dir: str,
    clyfar_df_dict: Optional[Dict[str, pd.DataFrame]] = None,
) -> str:
    """Export a null-first scenario clustering summary JSON.

    This is produced from the same member-level dailymax data used by ozone exports
    so it can be uploaded as a first-class forecast product.

    Args:
        dailymax_df_dict: Dictionary mapping member names to daily-max DataFrames
        init_dt: Forecast initialization datetime (naive UTC)
        output_dir: Directory to save JSON file
        clyfar_df_dict: Optional full-resolution member DataFrames for weather context

    Returns:
        File path created
    """
    os.makedirs(output_dir, exist_ok=True)
    init_str = init_dt.strftime('%Y%m%d_%H%MZ')

    member_poss: Dict[str, pd.DataFrame] = {}
    member_percentiles: Dict[str, pd.DataFrame] = {}

    for member_name, df in dailymax_df_dict.items():
        needed_poss = {"background", "moderate", "elevated", "extreme"}
        if not needed_poss.issubset(df.columns):
            logger.warning(
                "Skipping %s in clustering summary due to missing possibility columns",
                member_name,
            )
            continue

        p50_col = "ozone_50pc" if "ozone_50pc" in df.columns else "p50"
        p90_col = "ozone_90pc" if "ozone_90pc" in df.columns else "p90"
        if p50_col not in df.columns or p90_col not in df.columns:
            logger.warning(
                "Skipping %s in clustering summary due to missing percentile columns",
                member_name,
            )
            continue

        member_poss[member_name] = df[["background", "moderate", "elevated", "extreme"]].astype(float)
        member_percentiles[member_name] = pd.DataFrame(
            {"p50": df[p50_col].astype(float), "p90": df[p90_col].astype(float)},
            index=df.index,
        )

    if not member_poss:
        raise ValueError("No valid member possibility data available for clustering summary export")
    if not member_percentiles:
        raise ValueError("No valid member percentile data available for clustering summary export")

    weather_data: Dict[str, Dict[str, List[float]]] = {}
    if clyfar_df_dict is not None:
        for member_name, df in clyfar_df_dict.items():
            weather_data[member_name] = {
                "snow": [float(v) if pd.notna(v) else None for v in df.get("snow", pd.Series(dtype=float)).tolist()],
                "wind": [float(v) if pd.notna(v) else None for v in df.get("wind", pd.Series(dtype=float)).tolist()],
            }

    summary = build_clustering_summary(
        norm_init=init_str,
        member_poss=member_poss,
        member_percentiles=member_percentiles,
        weather_data=weather_data,
    )

    filename = f"forecast_clustering_summary_{init_str}.json"
    filepath = os.path.join(output_dir, filename)
    with open(filepath, 'w') as f:
        json.dump(summary, f, indent=2, default=_sanitize_for_json)

    logger.info(f"Created {filename}")
    return filepath


def export_all_products(
    dailymax_df_dict: Dict[str, pd.DataFrame],
    init_dt: datetime,
    output_dir: str,
    clyfar_df_dict: Optional[Dict[str, pd.DataFrame]] = None,
    upload: bool = True,
    max_workers: int = 8
) -> Dict[str, List[str]]:
    """Export all forecast data products (64-96 JSON files total).

    Convenience function to generate all forecast products in one call.
    Files are created first, then uploaded in parallel for better performance.

    Products:
    - Ozone (63 files): possibility heatmaps (31), exceedance (1), percentiles (31)
    - Clustering (1 file): null-first scenario clustering summary
    - Weather (32 files, optional): GEFS weather members (31), percentiles (1)

    Args:
        dailymax_df_dict: Dictionary mapping member names to daily-max DataFrames
        init_dt: Forecast initialization datetime (naive UTC)
        output_dir: Directory to save JSON files
        clyfar_df_dict: Optional full-resolution DataFrames for weather export
        upload: If True, upload all files to BasinWx API in parallel
        max_workers: Max parallel upload threads (default 8)

    Returns:
        Dictionary with keys mapping to file lists:
        - 'possibility', 'exceedance', 'percentiles' (always)
        - 'clustering' (always)
        - 'weather_members', 'weather_percentiles' (if clyfar_df_dict provided)
    """
    logger.info(f"Exporting all Clyfar forecast products for {init_dt}")

    # Step 1: Create ozone JSON files
    results = {
        "possibility": export_possibility_heatmaps(dailymax_df_dict, init_dt, output_dir),
        "exceedance": [export_exceedance_probabilities(dailymax_df_dict, init_dt, output_dir)],
        "percentiles": export_percentile_scenarios(dailymax_df_dict, init_dt, output_dir),
        "clustering": [
            export_clustering_summary(
                dailymax_df_dict=dailymax_df_dict,
                init_dt=init_dt,
                output_dir=output_dir,
                clyfar_df_dict=clyfar_df_dict,
            )
        ],
    }

    # Step 2: Create weather JSON files if full-resolution data provided
    if clyfar_df_dict is not None:
        results["weather_members"] = export_gefs_weather_members(
            clyfar_df_dict, init_dt, output_dir)
        results["weather_percentiles"] = [export_gefs_weather_percentiles(
            clyfar_df_dict, init_dt, output_dir)]

    total_files = sum(len(v) for v in results.values())
    logger.info(f"Created {total_files} JSON files")

    # Step 3: Upload all files in parallel
    if upload:
        all_files = []
        for file_list in results.values():
            all_files.extend(file_list)
        _parallel_upload_jsons(all_files, "forecasts", max_workers=max_workers)

    return results


def _upload_to_basinwx(filepath: str, data_type: str) -> bool:
    """Upload JSON file to BasinWx API.

    Args:
        filepath: Path to JSON file
        data_type: Data type for API endpoint (e.g., 'forecasts')

    Returns:
        True if upload succeeded, False otherwise
    """
    api_key = os.getenv('DATA_UPLOAD_API_KEY')
    if not api_key:
        logger.warning("DATA_UPLOAD_API_KEY not set, skipping upload")
        return False

    api_url = os.getenv('BASINWX_API_URL', 'https://basinwx.com')

    try:
        send_json_to_server(
            server_address=api_url,
            fpath=filepath,
            file_data=data_type,  # data_type is 'forecasts', not JSON content
            API_KEY=api_key
        )
        logger.debug(f"Uploaded {os.path.basename(filepath)} to {api_url}")
        return True

    except Exception as e:
        logger.error(f"Failed to upload {filepath}: {e}")
        return False


def _parallel_upload_jsons(filepaths: List[str], data_type: str, max_workers: int = 8) -> int:
    """Upload multiple JSON files in parallel.

    Args:
        filepaths: List of JSON file paths to upload
        data_type: Data type for API endpoint (e.g., 'forecasts')
        max_workers: Max parallel upload threads (default 8)

    Returns:
        Number of successful uploads
    """
    if not filepaths:
        return 0

    api_key = os.getenv('DATA_UPLOAD_API_KEY')
    if not api_key:
        logger.warning("DATA_UPLOAD_API_KEY not set, skipping all uploads")
        return 0

    logger.info(f"Uploading {len(filepaths)} JSON files with {max_workers} workers...")

    success = 0
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_upload_to_basinwx, fp, data_type): fp for fp in filepaths}
        for future in as_completed(futures):
            if future.result():
                success += 1

    logger.info(f"Uploaded {success}/{len(filepaths)} JSON files")
    return success


def _upload_single_png(png_path: str, session, upload_url: str, headers: dict) -> bool:
    """Upload a single PNG using a shared session.

    Args:
        png_path: Path to PNG file
        session: requests.Session object (shared across threads)
        upload_url: API endpoint URL
        headers: Request headers (api key, hostname)

    Returns:
        True if upload succeeded, False otherwise
    """
    try:
        with open(png_path, 'rb') as f:
            files = {'file': (os.path.basename(png_path), f, 'image/png')}
            response = session.post(upload_url, files=files, headers=headers, timeout=60)

        if response.status_code == 200:
            logger.info(f"Uploaded PNG: {os.path.basename(png_path)}")
            return True
        else:
            logger.error(f"PNG upload failed ({response.status_code}): {response.text}")
            return False

    except Exception as e:
        logger.error(f"Failed to upload PNG {png_path}: {e}")
        return False


def upload_png_to_basinwx(png_path: str) -> bool:
    """Upload a PNG image to BasinWx API (standalone version).

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
    headers = {'x-api-key': api_key, 'x-client-hostname': hostname}

    with requests.Session() as session:
        return _upload_single_png(png_path, session, upload_url, headers)


def upload_pdf_to_basinwx(pdf_path: str) -> bool:
    """Upload a PDF file to BasinWx API.

    Args:
        pdf_path: Path to PDF file

    Returns:
        True if upload succeeded, False otherwise
    """
    return upload_outlook_to_basinwx(pdf_path)


def upload_outlook_to_basinwx(file_path: str) -> bool:
    """Upload an LLM outlook file (PDF or markdown) to BasinWx API.

    Args:
        file_path: Path to PDF or markdown file

    Returns:
        True if upload succeeded, False otherwise
    """
    import requests
    import socket

    api_key = os.getenv('DATA_UPLOAD_API_KEY')
    if not api_key:
        logger.warning("DATA_UPLOAD_API_KEY not set, skipping outlook upload")
        return False

    api_url = os.getenv('BASINWX_API_URL', 'https://basinwx.com')
    upload_url = f"{api_url}/api/upload/llm_outlooks"
    hostname = socket.getfqdn()
    headers = {'x-api-key': api_key, 'x-client-hostname': hostname}

    # Detect MIME type from extension
    ext = os.path.splitext(file_path)[1].lower()
    mime_types = {'.pdf': 'application/pdf', '.md': 'text/markdown'}
    mime_type = mime_types.get(ext, 'application/octet-stream')

    try:
        with requests.Session() as session:
            with open(file_path, 'rb') as f:
                files = {'file': (os.path.basename(file_path), f, mime_type)}
                response = session.post(upload_url, files=files, headers=headers, timeout=60)

            if response.status_code == 200:
                logger.info(f"Uploaded outlook: {os.path.basename(file_path)}")
                return True
            else:
                logger.error(f"Outlook upload failed ({response.status_code}): {response.text}")
                return False

    except Exception as e:
        logger.error(f"Failed to upload outlook {file_path}: {e}")
        return False


def upload_json_to_basinwx(filepath: str, data_type: str = "forecasts") -> bool:
    """Upload a JSON file to BasinWx API.

    Args:
        filepath: Path to JSON file
        data_type: Data type for API routing (default 'forecasts')

    Returns:
        True if upload succeeded, False otherwise
    """
    return _upload_to_basinwx(filepath, data_type)


def export_figures_to_basinwx(
    fig_root: str,
    init_dt: datetime,
    upload: bool = True,
    max_workers: int = 8,
    json_tests_root: Optional[str] = None
) -> Dict[str, List[str]]:
    """Export heatmap and meteogram PNGs, plus LLM outlook PDFs, to BasinWx.

    Only uploads files matching the current init_dt to avoid re-uploading old runs.

    Looks for figures in:
    - {fig_root}/heatmap/*.png (heatmaps)
    - {fig_root}/meteograms/*.png (new standard location)
    - {fig_root}/{YYYYMMDD_HHZ}/*.png (legacy dated subdirs)
    - {fig_root}/*.png (root fallback)

    Looks for PDFs in:
    - {json_tests_root}/CASE_{init}/llm_text/*.pdf (LLM outlook PDFs)

    Args:
        fig_root: Root directory containing figures
        init_dt: Forecast initialization datetime (used to filter files)
        upload: If True, upload to BasinWx API
        max_workers: Max parallel upload threads (default 8)
        json_tests_root: Optional path to json_tests directory for PDF uploads

    Returns:
        Dictionary with 'heatmaps', 'meteograms', and 'outlooks' keys mapping to file lists
    """
    results = {"heatmaps": [], "meteograms": [], "outlooks": []}
    all_pngs = []

    # Generate init time patterns to match in filenames
    # Filename patterns: heatmap_UB-dailymax_ozone_20251130-1800_clyfar030.png
    #                    meteogram_UB-repr_temp_20251130-1800_GEFS.png
    init_pattern = init_dt.strftime('%Y%m%d-%H%M')  # e.g., "20251130-1800"
    init_pattern_alt = init_dt.strftime('%Y%m%d_%H')  # e.g., "20251130_18" for folder names

    logger.info(f"Filtering PNGs for init time: {init_pattern}")

    def matches_init_time(filename: str) -> bool:
        """Check if filename contains the current run's init time."""
        return init_pattern in filename or init_pattern_alt in filename

    # Collect heatmap PNGs from {fig_root}/heatmap/
    heatmap_dir = os.path.join(fig_root, "heatmap")
    if os.path.isdir(heatmap_dir):
        for f in os.listdir(heatmap_dir):
            if f.endswith('.png') and matches_init_time(f):
                fpath = os.path.join(heatmap_dir, f)
                results["heatmaps"].append(fpath)
                all_pngs.append(fpath)

    # Collect meteogram PNGs from multiple locations
    meteogram_dirs = [
        fig_root,  # Root fallback
        os.path.join(fig_root, "meteograms"),  # New standard location (GEFS meteograms)
        os.path.join(fig_root, "optim_pessim"),  # Optimist/pessimist percentile meteograms
    ]

    # Also check the dated subdirectory for THIS run only (legacy support)
    dated_subdir = os.path.join(fig_root, init_dt.strftime('%Y%m%d_%H%MZ'))
    if os.path.isdir(dated_subdir):
        meteogram_dirs.append(dated_subdir)

    # Search all meteogram directories
    seen_files = set()  # Avoid duplicates
    for mdir in meteogram_dirs:
        if os.path.isdir(mdir):
            for f in os.listdir(mdir):
                if f.endswith('.png') and 'meteogram' in f.lower() and f not in seen_files:
                    if matches_init_time(f):
                        fpath = os.path.join(mdir, f)
                        results["meteograms"].append(fpath)
                        all_pngs.append(fpath)
                        seen_files.add(f)

    logger.info(f"Found {len(results['heatmaps'])} heatmaps, "
                f"{len(results['meteograms'])} meteograms for {init_pattern}")

    # Collect LLM outlook files (PDFs + markdown) from json_tests directory
    all_outlook_files = []
    if json_tests_root:
        init_str = init_dt.strftime('%Y%m%d_%H%MZ')
        case_dir = os.path.join(json_tests_root, f"CASE_{init_str}")
        llm_text_dir = os.path.join(case_dir, "llm_text")
        if os.path.isdir(llm_text_dir):
            for f in os.listdir(llm_text_dir):
                if f.startswith('LLM-OUTLOOK-') and f.endswith(('.pdf', '.md')):
                    fpath = os.path.join(llm_text_dir, f)
                    results["outlooks"].append(fpath)
                    all_outlook_files.append(fpath)
            if all_outlook_files:
                logger.info(f"Found {len(all_outlook_files)} outlook files in {llm_text_dir}")

    # Parallel upload with shared session for proper connection cleanup
    if upload and all_pngs:
        import requests
        import socket

        api_key = os.getenv('DATA_UPLOAD_API_KEY')
        if not api_key:
            logger.warning("DATA_UPLOAD_API_KEY not set, skipping PNG uploads")
            return results

        api_url = os.getenv('BASINWX_API_URL', 'https://basinwx.com')
        upload_url = f"{api_url}/api/upload/images"
        hostname = socket.getfqdn()
        headers = {'x-api-key': api_key, 'x-client-hostname': hostname}

        logger.info(f"Uploading {len(all_pngs)} PNGs with {max_workers} workers...")

        # Use a shared session for connection pooling and proper cleanup
        session = requests.Session()
        try:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    executor.submit(_upload_single_png, p, session, upload_url, headers): p
                    for p in all_pngs
                }
                success = 0
                for future in as_completed(futures):
                    if future.result():
                        success += 1
            logger.info(f"Uploaded {success}/{len(all_pngs)} PNGs")
        finally:
            # Explicitly close session to ensure all connections are cleaned up
            session.close()

    # Upload outlook files (PDFs + markdown) to llm_outlooks endpoint
    if upload and all_outlook_files:
        outlook_success = 0
        for fpath in all_outlook_files:
            if upload_outlook_to_basinwx(fpath):
                outlook_success += 1
        logger.info(f"Uploaded {outlook_success}/{len(all_outlook_files)} outlook files")

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
