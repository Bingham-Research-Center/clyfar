"""Functions to create representative obs for the Basin from a collection of stations' data.
"""

import os
import datetime

import pandas as pd
import numpy as np
import pytz
from astral import LocationInfo
from astral.sun import sun

from obs.download_winters import download_most_recent

def prepare_df(df, stids, vrbl_col, stid_col):
    """Prepare dataframe with proper timezone and subset columns.

    Args:
        df: Input DataFrame with UTC index
        stids: List of station IDs to include
        vrbl_col: Name of variable column
        stid_col: Name of station ID column

    Returns:
        DataFrame with UTC index and subset columns
    """
    df = df[df[stid_col].isin(stids)][[vrbl_col, stid_col]]

    if df.index.tz is None:
        df.index = pd.to_datetime(df.index, utc=True)
    elif df.index.tz != pytz.UTC:
        df.index = df.index.tz_convert(pytz.UTC)

    return df

def convert_to_local_date(df):
    """Convert UTC index to Mountain Time and add date column.

    Args:
        df: DataFrame with UTC index

    Returns:
        DataFrame with Mountain Time index and date column
    """
    df_local = df.copy()
    df_local.index = df.index.tz_convert("US/Mountain")
    df_local['date'] = df_local.index.date + pd.Timedelta(days=1)  # Align all functions to next day
    return df_local

def do_repval_mslp(df, stids, vrbl_col="sea_level_pressure", stid_col="stid"):
    """Create representative values of mean sea level pressure data.

    Args:
        df: DataFrame with UTC index and MSLP data
        stids: List of station IDs to use
        vrbl_col: Name of MSLP column
        stid_col: Name of station ID column

    Returns:
        DataFrame with daily representative MSLP values
    """
    # Prepare dataframe
    df = prepare_df(df, stids, vrbl_col, stid_col)
    df_local = convert_to_local_date(df)

    # Compute representative values
    daily_median = (df_local.groupby([stid_col, 'date'])[vrbl_col]
                    .quantile(0.5)
                    .reset_index())

    daily_median['date'] = pd.to_datetime(daily_median['date'])
    daily_median = daily_median.set_index('date')

    # Get final representative value
    repr_df = daily_median.groupby(level=0)[vrbl_col].quantile(0.5)
    repr_df = repr_df.to_frame(name="sea_level_pressure")

    return repr_df

def do_repval_wind(df, stids, vrbl_col="wind_speed", stid_col="stid"):
    """Create representative values of wind speed from a set of stations.

    Args:
        df (pd.DataFrame): The data frame with the wind speed data where columns are
            the stations. Index should be timezone-aware UTC timestamps.

    Returns:
        repr_df (pd.DataFrame): Representative values of wind speed with date index
    """
    # Prepare dataframe
    df = prepare_df(df, stids, vrbl_col, stid_col)
    df_local = convert_to_local_date(df)

    daily_pc = (df_local.groupby([stid_col, 'date'])[vrbl_col]
                  # .quantile(0.75)
                .apply(lambda x: np.quantile(x, 0.8, method="hazen"))
                .reset_index())

    # Convert date to datetime and set as index
    daily_pc['date'] = pd.to_datetime(daily_pc['date'])
    daily_pc = daily_pc.set_index('date')

    # Then the 75th percentile of those values across stations
    repr_df = daily_pc.groupby(level=0)[vrbl_col].apply(
                lambda x: np.quantile(x, 0.75, method="hazen"),
    )


    # Convert to DataFrame with named column
    repr_df = repr_df.to_frame(name="wind_speed")
    pass

    return repr_df

def do_repval_snow(df, stids, vrbl_col="snow_depth", stid_col="stid"):
    """Create representative values of snow from set of Uinta Basin stations.

    Notes:
        We use the stations "COOP*" in the Basin.

    Args:
        df (pd.DataFrame): The data frame with the snow data for all COOP stations.
            Index should be timezone-aware UTC timestamps.

    Returns:
        repr_df (pd.DataFrame): Representative values of snow depth with date index
    """
    # Prepare dataframe
    df = prepare_df(df, stids, vrbl_col, stid_col)
    df_local = convert_to_local_date(df)

    daily_pc = (df_local.groupby([stid_col, 'date'])[vrbl_col]
                .apply(lambda x: np.quantile(x, 0.9, method="hazen"))
                  .reset_index())

    # Convert date to datetime and set as index
    daily_pc['date'] = pd.to_datetime(daily_pc['date'])
    daily_pc = daily_pc.set_index('date')

    # Then the 95th percentile of those values across stations
    repr_df = daily_pc.groupby(level=0)[vrbl_col].apply(
        lambda x: np.quantile(x, 0.9, method="hazen"),
    )

    # Convert to DataFrame with named column
    repr_df = repr_df.to_frame(name="snow_depth")

    return repr_df

def get_solar_noon(date, tz):
    """Calculate solar noon for a given date in Roosevelt, UT.

    Args:
        date: datetime.date or datetime.datetime
        tz: pytz timezone object for Mountain Time

    Returns:
        datetime: timezone-aware solar noon time
    """
    # Ensure we're working with timezone-aware datetime
    if isinstance(date, datetime.date):
        date = datetime.datetime.combine(date, datetime.time(12, 0))
    if date.tzinfo is None:
        date = tz.localize(date)

    # Convert civil noon (12:00) to local time
    local_noon = datetime.datetime.combine(date.date(), datetime.time(12, 0))
    local_noon = tz.localize(local_noon)

    # TODO JRL do we need to do this?! I don't get it. Claude is to blame.
    # Apply longitude correction (4 minutes per degree from 105°W)
    # Roosevelt is at ~110°W, so we're about 5 degrees west of the Mountain Time meridian
    lng_correction = (109.9889 - 105.0) * 4 * 60  # seconds
    solar_noon = local_noon + datetime.timedelta(seconds=lng_correction)

    return solar_noon

def compute_nearzenithmean(df, solar_stids, vrbl_col="solar_radiation",
                           stid_col="stid", window_hrs=2):
    """Compute the near-zenith mean insolation for each station.

    Args:
        df (pd.DataFrame): The data frame with the insolation data where
            columns are the stations
        solar_stids (list): The list of station IDs for solar radiation
        vrbl_col (str): The column name for the variable of interest
        stid_col (str): The column name for the station ID
        window_hrs (float): Hours before/after solar noon to include

    Returns:
        df_daily_solar_nzm (pd.DataFrame): The near-zenith mean insolation data
    """
    # Define Roosevelt, UT location
    roosevelt = LocationInfo('Roosevelt', 'Utah', 'US/Mountain',
                             40.2994, -109.9889)
    mountain_tz = pytz.timezone('US/Mountain')

    # Ensure input data is timezone-aware and in Mountain Time
    if df.index.tz is None:
        df.index = pd.to_datetime(df.index, utc=True)
    if df.index.tz != mountain_tz:
        df.index = df.index.tz_convert(mountain_tz)

    daily_solar_nzm = dict()

    for stid in solar_stids:
        # Get the time series for this station
        sub_df = df.loc[df[stid_col] == stid, vrbl_col].dropna()

        daily_means = []
        # Group by local (Mountain) date
        for name, day_data in sub_df.groupby(lambda x: x.date()):
            try:
                solar_noon = get_solar_noon(name, mountain_tz)

                # Define window around solar noon
                window_start = solar_noon - datetime.timedelta(hours=window_hrs)
                window_end = solar_noon + datetime.timedelta(hours=window_hrs)

                # Filter data within window and compute mean
                mask = (day_data.index >= window_start) & (
                            day_data.index <= window_end)
                daily_mean = day_data[mask].mean()

                if not pd.isna(daily_mean):
                    # Store with timezone-aware timestamp for midnight local time
                    midnight = mountain_tz.localize(datetime.datetime.combine(
                                            name, datetime.time()))
                    daily_means.append((midnight, daily_mean))

            except Exception as e:
                print(f"Error processing date {name} for station {stid}: {str(e)}")
                continue

        # Convert daily means to series
        if daily_means:
            daily_solar_nzm[stid] = pd.Series(
                dict(daily_means),
                name=stid
            )

    # Create dataframe
    if daily_solar_nzm:
        df_daily_solar_nzm = pd.concat(daily_solar_nzm, axis=0, ignore_index=False)
        df_daily_solar_nzm = do_nzm_filtering(df_daily_solar_nzm, solar_stids)
        return df_daily_solar_nzm
    else:
        return pd.DataFrame()

def do_nzm_filtering(df, solar_stids, window=4):
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
            columns are the stations. Index should be timezone-aware UTC timestamps.

    Returns:
        repr_df (pd.DataFrame): The representative values of insolation with date index

    """
    df = prepare_df(df, stids, vrbl_col, stid_col)

    # compute_nearzenithmean will handle timezone conversion internally
    df_daily_solar_nzm = compute_nearzenithmean(df, stids)

    # Convert the index to date before computing representative value
    df_daily_solar_nzm.index = df_daily_solar_nzm.index.get_level_values(1).date

    # Compute the representative value (across stations)
    repr_df = df_daily_solar_nzm.groupby(df_daily_solar_nzm.index).apply(
            lambda x: np.quantile(x, 0.8, method="hazen"))

    # Name a dataframe column "solar_radiation" for consistency w/ other vrbls
    repr_df = repr_df.to_frame(name="solar_radiation")

    # Convert index to datetime for consistency with other variables
    repr_df.index = pd.to_datetime(repr_df.index)

    return repr_df

def do_repval_ozone(df, stids, vrbl_col="ozone_concentration", stid_col="stid"):
    """Create representative values of ozone concentration from set of stations.

    Args:
        df (pd.DataFrame): The data frame with the ozone data where columns are
            station IDs (stid), ozone_concentration is the observed data, and
            the index is a timezone-aware UTC timestamp.
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

    # Ensure index is timezone-aware UTC if it isn't already
    if df.index.tz is None:
        df.index = pd.to_datetime(df.index, utc=True)

    # Convert to local time zone from UTC (US/Mountain)
    df_local = df.copy()
    df_local.index = df.index.tz_convert("US/Mountain")

    # Add a column for "next day" date
    df_local['date'] = df_local.index.date + pd.Timedelta(days=1)

    # First get the 99th percentile for each station and date
    # If once an hour, 24 samples good for hazen
    daily_max = (df_local.groupby([stid_col, 'date'])[vrbl_col]
                 .max()
                 .reset_index())

    # Convert date back to datetime with timezone
    daily_max['date'] = pd.to_datetime(daily_max['date'])
    daily_max = daily_max.set_index('date')

    # For each day, take the maximum from all stations
    # As we add more stations via synoptic weather, we can take percentile.
    repr_df = daily_max.groupby(level=0)[vrbl_col].quantile(0.99)

    return repr_df

def get_representative_obs(vrbl, n_days, stids, timezone="US/Mountain"):
    """Helper function to download and process obs in one function.
    """
    repr_funcs = {
        "mslp": do_repval_mslp,
        "wind": do_repval_wind,
        "snow": do_repval_snow,
        "solar": do_repval_solar,
        "ozone": do_repval_ozone,
    }

    ob = download_most_recent(vrbl, n_days, timezone=timezone,
                              stids=stids)
    repr_vals = repr_funcs[vrbl](ob.df, stids)
    return repr_vals
