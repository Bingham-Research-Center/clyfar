"""Functions to create representative obs for the Basin from a collection of stations' data.
"""

import os

import pandas as pd
import numpy as np


def do_repval_mslp(df):
    """Create representative values of mean sea level pressure from KVEL data.

    Notes:
        This is the variable "sea_level_pressure" from the station KVEL,
        ignoring "pressure" and "altimeter". Further, we note the index
        is in UTC and we need to shift to local time (US Mountain) considering
        the daylight savings change.

    Args:
        df (pd.DataFrame): The data frame with the KVEL data.

    Returns:
        repr_df (pd.DataFrame): The representative values of MSLP for the Basin
    """
    # We need to convert the index to local time
    df.index = df.index.tz_convert("US/Mountain")

    # We take the median of daily values for KVEL
    repr_df = df.resample("D").median()

    # We then take the median of those values
    # repr_df = repr_df.median(axis=1)

    return repr_df


def do_repval_ozone(df):
    """Create representative values of ozone concentration from multiple reliable stations.

    Args:
        df (pd.DataFrame): The data frame with the ozone data where columns are station IDs
            (stid), and ozone_concentration, and the index is a timestamp.
    """
    # Remove extreme values
    df.loc[df["ozone_concentration"] > 140, "ozone_concentration"] = np.nan
    df.loc[df["ozone_concentration"] < 5, "ozone_concentration"] = np.nan

    # Convert to local time zone from UTC (US/Mountain)
    df.index = df.index.tz_convert("US/Mountain")

    # First get the 99th percentile for each station, resampled daily (midnight to midnight)
    daily_99th = df.groupby('stid').resample('D').quantile(0.99)

    # For each day, take the 99th percentile of the daily 99th percentiles across stations for a single value per day
    result = daily_99th.groupby(level=1).quantile(0.99)

    return result


def do_repval_wind(df):
    """Create representative values of wind speed from the Uinta Basin stations.

    Notes:
        We use the stations DURU1, A1622, SPMU1, QV4, WAXU1, E8302, KVEL, QRS, MYT5.

    Args:
        df (pd.DataFrame): The data frame with the wind speed data where columns are the stations

    """
    # Convert to local time zone from UTC (US/Mountain)
    df.index = df.index.tz_convert("US/Mountain")

    # First get 75th percentile of each station midnight to midnight local time
    df = df.groupby('stid').resample("D").quantile(0.75)

    # Then the 95th percentile of those values
    return df.groupby(level=1).quantile(0.75)


def do_repval_snow(df):
    """Create representative values of snow from the Uinta Basin stations.

    Notes:
        We use the stations "COOP*" in the Basin.

    Args:
        df (pd.DataFrame): The data frame with the snow data for all COOP stations

    """
    # Convert to local time zone from UTC (US/Mountain)
    df.index = df.index.tz_convert("US/Mountain")

    # Compute 95th percentile of snow depth for each station's reports midnight to midnight local time
    df = df.groupby("stid").resample("D").quantile(0.95)

    # Then the 95th percentile of those values
    return df.groupby(level=1).quantile(0.95)


def compute_nearzenithmean(df, solar_stids):
    # Convert to local time zone from UTC (US/Mountain)
    df.index = df.index.tz_convert("US/Mountain")

    # Create a dictionary to store this "near-zenith mean" (nzm) for each station
    daily_solar_nzm = dict()

    for stid in solar_stids:
        # Get the time series for this station, only for solar radiation
        sub_df = df.loc[df["stid"] == stid]["solar_radiation"]

        # For each station, compute mean from obs within each local day for each column (variable)
        daily_solar_nzm[stid] = sub_df.between_time("10:00", "14:00").resample("D").mean()

    # Create dataframe
    df_daily_solar_nzm = pd.concat(daily_solar_nzm, axis=0, ignore_index=False)
    df_daily_solar_nzm = do_nzm_filtering(df_daily_solar_nzm, solar_stids)
    return df_daily_solar_nzm


def do_nzm_filtering(df, solar_stids):
    """Filter the near-zenith mean insolation data by adding a rolling mean.

    Note:
        The first six days will be NaN due to the window. Start a week early.
        TODO: add a week for the operational model before starting Clyfar

    Args:
        df (pd.DataFrame): The data frame with the near-zenith mean insolation data
        solar_stids (list): The list of station IDs for solar radiation
    """
    all_filtered = {}
    for stid in solar_stids:
        sub_df = df.loc[stid]
        filtered_sub_df = sub_df.rolling(window=7).mean()
        all_filtered[stid] = filtered_sub_df
    filtered_df = pd.concat(all_filtered, axis=0, ignore_index=False)
    return filtered_df


def do_repval_solar(df):
    """Create representative values of insolation using "near-zenith mean" from four stations.

    Args:
        df (pd.DataFrame): The data frame with the insolation data where columns are the stations

    """
    # Convert to local time zone from UTC (US/Mountain)
    df.index = df.index.tz_convert("US/Mountain")

    solar_stids = ["DURU1", "A1622", "SPMU1", "WAXU1"]

    # Compute near-zenith mean for each station midnight to midnight local time
    df_daily_solar_nzm = compute_nearzenithmean(df, solar_stids)

    # 95th percentile
    return df_daily_solar_nzm.groupby(level=1).quantile(0.95)

