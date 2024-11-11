"""Functions to create representative obs for the Basin from a collection of stations' data.
"""

import os

import pandas as pd
import numpy as np


def do_repval_mslp(df, stids, vrbl_col="sea_level_pressure", stid_col="stid"):
    """Create representative values of mean sea level pressure data.

    Notes:
        This is currently the variable "sea_level_pressure" from the station KVEL,
        ignoring "pressure" and "altimeter". The row/datetime index
        is in UTC and we need to shift to local time (US Mountain) considering
        the daylight savings change.

    Args:
        df (pd.DataFrame): The data frame with data reported from
            various stids, reporting frequencies, and non-NaN variables
        stids (list): The list of station IDs to consider for this calculation
        vrbl_col (str): The column name for the variable of interest
        stid_col (str): The column name for the station ID

    Returns:
        repr_df (pd.DataFrame): Time series of representative values of MSLP
                                    for the Basin
    """
    # Subset to just the stids and the two columns for the variable and station ID
    # (Those keys are set in the function signature)
    df = df[df[stid_col].isin(stids)][[vrbl_col, stid_col]]

    # We need to convert the index to local time
    df.index = df.index.tz_convert("US/Mountain")

    # We first reduce the dataset to daily values for each station computed
    # as the median of that station's values for that day.
    df = df.groupby(stid_col).resample('D').median()

    # We then take the median over all stations for each day to create the representative value
    repr_df = df.groupby(level=1).median()

    return repr_df

def do_repval_wind(df, stids, vrbl_col="wind_speed", stid_col="stid"):
    """Create representative values of wind speed from a set of stations.

    Args:
        df (pd.DataFrame): The data frame with the wind speed data where columns are the stations

    """
    # Subset to just the stids and the two columns for the variable and station ID
    df = df[df[stid_col].isin(stids)][[vrbl_col, stid_col]]

    # Convert to local time zone from UTC (US/Mountain)
    df.index = df.index.tz_convert("US/Mountain")

    # First get 75th percentile of each station midnight to midnight local time
    daily_75th = df.groupby(stid_col).resample("D").quantile(0.75)

    # Then the 95th percentile of those values
    repr_df = daily_75th.groupby(level=1).quantile(0.75)

    return repr_df

def do_repval_snow(df, stids, vrbl_col="snow_depth", stid_col="stid"):
    """Create representative values of snow from set of Uinta Basin stations.

    Notes:
        We use the stations "COOP*" in the Basin.

    Args:
        df (pd.DataFrame): The data frame with the snow data for all COOP stations

    """
    # Subset to just the stids and the two columns for the variable and station ID
    df = df[df[stid_col].isin(stids)][[vrbl_col, stid_col]]

    # Convert to local time zone from UTC (US/Mountain)
    df.index = df.index.tz_convert("US/Mountain")

    # Compute 95th percentile of snow depth for each station's reports midnight to midnight local time
    daily_95th = df.groupby(stid_col).resample("D").quantile(0.95)

    # Then the 95th percentile of those values
    repr_df = daily_95th.groupby(level=1).quantile(0.95)

    return repr_df

def compute_nearzenithmean(df, solar_stids, vrbl_col="solar_radiation",
                            stid_col="stid"):
    """Compute the near-zenith mean insolation for each station.

    Args:
        df (pd.DataFrame): The data frame with the insolation data where
            columns are the stations
        solar_stids (list): The list of station IDs for solar radiation
        vrbl_col (str): The column name for the variable of interest
        stid_col (str): The column name for the station ID

    Returns:
        df_daily_solar_nzm (pd.DataFrame): The near-zenith mean insolation data
    """
    # Create a dictionary to store this "near-zenith mean" (nzm) for each station
    daily_solar_nzm = dict()

    for stid in solar_stids:
        # Get the time series for this station, only for the variable column
        sub_df = df.loc[df[stid_col] == stid, vrbl_col].dropna()  # Added .dropna()

        # For each station, compute mean from obs within each local day for the variable column
        daily_solar_nzm[stid] = sub_df.between_time("10:00", "14:00").resample("D").mean()

    # Create dataframe
    df_daily_solar_nzm = pd.concat(daily_solar_nzm, axis=0, ignore_index=False)
    df_daily_solar_nzm = do_nzm_filtering(df_daily_solar_nzm, solar_stids)
    return df_daily_solar_nzm

def do_nzm_filtering(df, solar_stids, window=7):
    """Filter the near-zenith mean insolation data by adding a rolling mean.

    Note:
        The first "window" days will be NaN due to the window. Start
         a"window" days early.

    TODO: add a week for the operational model before starting Clyfar

    Args:
        df (pd.DataFrame): Dataframe with the near-zenith mean insolation data
        solar_stids (list): The list of station IDs for solar radiation
        window (int): The window size for the rolling mean

    Returns:
        filtered_df (pd.DataFrame): Filtered near-zenith mean insolation data
    """
    all_filtered = {}
    for stid in solar_stids:
        sub_df = df.loc[stid].dropna()
        filtered_sub_df = sub_df.rolling(window=window).mean()
        all_filtered[stid] = filtered_sub_df
    filtered_df = pd.concat(all_filtered, axis=0, ignore_index=False)
    return filtered_df

def do_repval_solar(df, stids, vrbl_col="solar_radiation", stid_col="stid"):
    """Create representative values of insolation using "near-zenith mean"
        from four stations.

    Args:
        df (pd.DataFrame): The data frame with the insolation data where
            columns are the stations

    Returns:
        repr_df (pd.DataFrame): The representative values of insolation

    """
    # Subset to just the stids and the two columns for the variable and station ID
    df = df[df[stid_col].isin(stids)][[vrbl_col, stid_col]]

    # Convert to local time zone from UTC (US/Mountain)
    df.index = df.index.tz_convert("US/Mountain")

    # Compute near-zenith mean for each station midnight to midnight local time
    df_daily_solar_nzm = compute_nearzenithmean(df, stids)

    repr_df = df_daily_solar_nzm.groupby(level=1).quantile(0.95)

    return repr_df

def do_repval_ozone(df, stids, vrbl_col="ozone_concentration", stid_col="stid"):
    """Create representative values of ozone concentration from set of stations.

    Args:
        df (pd.DataFrame): The data rame with the ozone data where columns are
            station IDs (stid), ozone_concentration is the observed data, and
            the index is a timestamp.
        stids (list): The list of station IDs to consider for this calculation
        vrbl_col (str): The column name for the variable of interest
        stid_col (str): The column name for the station ID

    Returns:
        result (pd.DataFrame): The representative values of ozone concentration
    """
    # Subset to just the stids and the two columns for variable & station ID
    df = df[df[stid_col].isin(stids)][[vrbl_col, stid_col]]

    # Remove extreme values
    df.loc[df[vrbl_col] > 140, vrbl_col] = np.nan
    df.loc[df[vrbl_col] < 5, vrbl_col] = np.nan

    # Convert to local time zone from UTC (US/Mountain)
    df.index = df.index.tz_convert("US/Mountain")

    # First get the 99th percentile for each station, resampled
    # daily (midnight to midnight)
    daily_99th = df.groupby(stid_col).resample('D').quantile(0.99)

    # For each day, take the 99th percentile of the daily 99th percentiles
    # across stations for a single value per day
    repr_df = daily_99th.groupby(level=1).quantile(0.99)

    return repr_df
