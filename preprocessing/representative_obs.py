"""Functions to create representative obs for the Basin from a collection of stations' data.
"""

import os
import datetime

import pandas as pd
import numpy as np
import pytz
from astral import LocationInfo
from astral.sun import sun

MOUNTAIN_TIMEZONE = "America/Denver"
MOUNTAIN_STANDARD_TIME = datetime.timezone(
    datetime.timedelta(hours=-7), name="MST"
)
OZONE_NAAQS_LEVEL_PPB = 70.0


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

def convert_to_local_date(df, timezone=MOUNTAIN_TIMEZONE):
    """Convert a UTC-indexed frame to physical local dates.

    Args:
        df: DataFrame with UTC index

    Returns:
        DataFrame with a timezone-aware local index and a naive ``date``
        column naming the physical local calendar day.
    """
    df_local = df.copy()
    index = pd.DatetimeIndex(df_local.index)
    if index.tz is None:
        index = index.tz_localize("UTC")
    else:
        index = index.tz_convert("UTC")
    df_local.index = index.tz_convert(timezone)
    df_local['date'] = df_local.index.normalize().tz_localize(None)
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
    if isinstance(date, datetime.datetime):
        day = date.date()
    elif isinstance(date, datetime.date):
        day = date
    else:
        raise TypeError("date must be datetime.date or datetime.datetime")

    roosevelt = LocationInfo("Roosevelt", "Utah", MOUNTAIN_TIMEZONE, 40.2994, -109.9889)
    solar_times = sun(roosevelt.observer, date=day, tzinfo=tz)
    return solar_times["noon"]

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
    mountain_tz = pytz.timezone(MOUNTAIN_TIMEZONE)

    # Ensure input data is timezone-aware and in Mountain Time
    if df.index.tz is None:
        df.index = pd.to_datetime(df.index, utc=True)
    if str(df.index.tz) != mountain_tz.zone:
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

def station_ozone_mda8_windows(
    df,
    stids,
    vrbl_col="ozone_concentration",
    stid_col="stid",
    minimum_ppb=5.0,
    maximum_ppb=140.0,
    standard_timezone=MOUNTAIN_STANDARD_TIME,
    display_timezone=MOUNTAIN_TIMEZONE,
    naaqs_level_ppb=OZONE_NAAQS_LEVEL_PPB,
):
    """Return the 17 EPA-aligned station MDA8 windows for each standard day.

    The primary values retain the source precision.  Parallel audit values
    apply Appendix U's whole-ppb equivalent truncation before and after the
    moving average.  This is an EPA-aligned calculation from Synoptic data,
    not a regulatory AQS or design-value calculation.
    """
    if minimum_ppb >= maximum_ppb:
        raise ValueError("minimum_ppb must be less than maximum_ppb")

    audit_columns = [vrbl_col, stid_col]
    if "qc_flagged" in df.columns:
        audit_columns.append("qc_flagged")
    prepared = df.loc[df[stid_col].isin(stids), audit_columns].copy()
    utc_index = pd.DatetimeIndex(prepared.index)
    if utc_index.tz is None:
        utc_index = utc_index.tz_localize("UTC")
    else:
        utc_index = utc_index.tz_convert("UTC")
    numeric = pd.to_numeric(prepared[vrbl_col], errors="coerce")
    prepared["_qc_flagged"] = (
        prepared["qc_flagged"].fillna(False).astype(bool)
        if "qc_flagged" in prepared
        else False
    )
    in_range = numeric.between(minimum_ppb, maximum_ppb, inclusive="both")
    prepared["_range_rejected"] = numeric.notna() & ~in_range
    prepared["_valid_value"] = numeric.where(
        ~prepared["_qc_flagged"] & in_range
    )
    prepared["_hour_standard"] = utc_index.tz_convert(
        standard_timezone
    ).floor("h")
    hourly = (
        prepared.groupby([stid_col, "_hour_standard"], observed=True)
        .agg(
            value=("_valid_value", "mean"),
            raw_observation_count=(vrbl_col, "size"),
            qc_flagged_count=("_qc_flagged", "sum"),
            range_rejected_count=("_range_rejected", "sum"),
        )
        .sort_index()
    )
    if hourly.empty:
        return pd.DataFrame()

    rows = []
    for station in stids:
        if station not in hourly.index.get_level_values(0):
            continue
        station_hourly = hourly.xs(station, level=0)
        first_day = station_hourly.index.min().normalize()
        last_day = station_hourly.index.max().normalize()
        complete_index = pd.date_range(
            first_day,
            last_day + pd.Timedelta(days=1, hours=7),
            freq="h",
            tz=standard_timezone,
        )
        station_hourly = station_hourly.reindex(complete_index)
        for day in pd.date_range(
            first_day, last_day, freq="D", tz=standard_timezone
        ):
            for start_hour in range(7, 24):
                start = day + pd.Timedelta(hours=start_hour)
                window_hours = pd.date_range(start, periods=8, freq="h")
                window = station_hourly.reindex(window_hours)
                values = window["value"]
                valid = values.dropna().astype(float)
                valid_hour_count = int(valid.size)
                if valid_hour_count >= 6:
                    mda8_unrounded = float(valid.mean())
                    epa_untruncated = float(np.floor(valid).mean())
                    window_valid = True
                    validity_reason = "six_or_more_hours"
                else:
                    mda8_unrounded = float(valid.sum() / 8.0)
                    epa_untruncated = float(np.floor(valid).sum() / 8.0)
                    window_valid = epa_untruncated > naaqs_level_ppb
                    validity_reason = (
                        "zero_fill_exceeds_standard"
                        if window_valid
                        else "fewer_than_six_hours"
                    )
                rows.append(
                    {
                        stid_col: station,
                        "verification_day": day.tz_localize(None),
                        "window_start_standard": start,
                        "window_end_standard": start + pd.Timedelta(hours=8),
                        "window_start_utc": start.tz_convert("UTC"),
                        "window_end_utc": (
                            start + pd.Timedelta(hours=8)
                        ).tz_convert("UTC"),
                        "window_start_local": start.tz_convert(display_timezone),
                        "window_end_local": (
                            start + pd.Timedelta(hours=8)
                        ).tz_convert(display_timezone),
                        "valid_hour_count": valid_hour_count,
                        "raw_observation_count": int(
                            window["raw_observation_count"].fillna(0).sum()
                        ),
                        "qc_flagged_count": int(
                            window["qc_flagged_count"].fillna(0).sum()
                        ),
                        "range_rejected_count": int(
                            window["range_rejected_count"].fillna(0).sum()
                        ),
                        "window_valid": window_valid,
                        "window_validity_reason": validity_reason,
                        "mda8_ppb_unrounded": (
                            mda8_unrounded if window_valid else np.nan
                        ),
                        "mda8_ppb_epa_untruncated": (
                            epa_untruncated if window_valid else np.nan
                        ),
                        "mda8_ppb_epa_truncated": (
                            float(np.floor(epa_untruncated))
                            if window_valid
                            else np.nan
                        ),
                    }
                )
    return pd.DataFrame(rows)


def daily_station_ozone_mda8(
    df,
    stids,
    vrbl_col="ozone_concentration",
    stid_col="stid",
    minimum_ppb=5.0,
    maximum_ppb=140.0,
    standard_timezone=MOUNTAIN_STANDARD_TIME,
    display_timezone=MOUNTAIN_TIMEZONE,
    naaqs_level_ppb=OZONE_NAAQS_LEVEL_PPB,
):
    """Return one eligible MDA8 value per station and fixed-MST day."""
    windows = station_ozone_mda8_windows(
        df,
        stids,
        vrbl_col=vrbl_col,
        stid_col=stid_col,
        minimum_ppb=minimum_ppb,
        maximum_ppb=maximum_ppb,
        standard_timezone=standard_timezone,
        display_timezone=display_timezone,
        naaqs_level_ppb=naaqs_level_ppb,
    )
    if windows.empty:
        return windows

    rows = []
    for (station, day), group in windows.groupby(
        [stid_col, "verification_day"], observed=True, sort=True
    ):
        eligible = group.loc[group["window_valid"]].sort_values(
            "window_start_standard", kind="stable"
        )
        valid_window_count = int(len(eligible))
        selected = None
        if valid_window_count:
            selected = eligible.loc[eligible["mda8_ppb_unrounded"].idxmax()]
        exceeds_standard = bool(
            selected is not None
            and selected["mda8_ppb_epa_untruncated"] > naaqs_level_ppb
        )
        daily_valid = valid_window_count >= 13 or exceeds_standard
        daily_reason = (
            "thirteen_or_more_windows"
            if valid_window_count >= 13
            else "maximum_exceeds_standard"
            if exceeds_standard
            else "fewer_than_thirteen_windows"
        )
        row = {
            stid_col: station,
            "verification_day": day,
            "valid_window_count": valid_window_count,
            "daily_valid": daily_valid,
            "daily_validity_reason": daily_reason,
            "station_mda8_ppb": np.nan,
            "station_mda8_epa_truncated_ppb": np.nan,
            "unfiltered_station_mda8_ppb": (
                selected["mda8_ppb_unrounded"]
                if selected is not None
                else np.nan
            ),
            "selected_window_start_standard": pd.NaT,
            "selected_window_start_utc": pd.NaT,
            "selected_window_start_local": pd.NaT,
            "selected_window_valid_hour_count": pd.NA,
        }
        if daily_valid and selected is not None:
            row.update(
                {
                    "station_mda8_ppb": selected["mda8_ppb_unrounded"],
                    "station_mda8_epa_truncated_ppb": selected[
                        "mda8_ppb_epa_truncated"
                    ],
                    "selected_window_start_standard": selected[
                        "window_start_standard"
                    ],
                    "selected_window_start_utc": selected["window_start_utc"],
                    "selected_window_start_local": selected["window_start_local"],
                    "selected_window_valid_hour_count": selected[
                        "valid_hour_count"
                    ],
                }
            )
        rows.append(row)
    return pd.DataFrame(rows).sort_values(
        ["verification_day", stid_col], kind="stable"
    ).reset_index(drop=True)


def do_repval_ozone(
    df,
    stids,
    vrbl_col="ozone_concentration",
    stid_col="stid",
    spatial_quantile=0.99,
    minimum_ppb=5.0,
    maximum_ppb=140.0,
):
    """Create one Basin representative MDA8 value per fixed-MST day.

    Args:
        df (pd.DataFrame): The data frame with the ozone data where columns are
            station IDs (stid), ozone_concentration is the observed data, and
            the index is a timezone-aware UTC timestamp.
        stids (list): The list of station IDs to consider for this calculation
        vrbl_col (str): The column name for the variable of interest
        stid_col (str): The column name for the station ID

    Returns:
        pandas.Series: Basin upper-representative station MDA8 values, indexed
        by the fixed-MST verification day.
    """
    if not 0.0 <= spatial_quantile <= 1.0:
        raise ValueError("spatial_quantile must lie in [0, 1]")
    station_daily = daily_station_ozone_mda8(
        df,
        stids,
        vrbl_col=vrbl_col,
        stid_col=stid_col,
        minimum_ppb=minimum_ppb,
        maximum_ppb=maximum_ppb,
    )
    if station_daily.empty:
        return pd.Series(dtype=float, name=vrbl_col)
    eligible = station_daily.loc[station_daily["daily_valid"]]
    representative = eligible.groupby("verification_day")[
        "station_mda8_ppb"
    ].quantile(spatial_quantile)
    representative.name = vrbl_col
    return representative.sort_index()

def get_representative_obs(vrbl, n_days, stids, timezone=MOUNTAIN_TIMEZONE):
    """Helper function to download and process obs in one function.
    """
    # Synoptic validates credentials at import time in some installed versions.
    # Keep that network-capable dependency out of ordinary preprocessing imports.
    from obs.download_winters import download_most_recent

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
