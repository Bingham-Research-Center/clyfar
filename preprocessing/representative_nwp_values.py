"""Take GEFS data and create a time series as representative value"""

import importlib
import datetime
import logging

import pandas as pd
import pytz
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import xarray as xr
from metpy.units import units

from nwp.download_funcs import load_variable
from nwp.gefsdata import GEFSData
from obs.download_winters import download_most_recent
from utils.lookups import Lookup, snow_stids
from preprocessing.representative_obs import do_repval_snow, \
    get_representative_obs

LOCAL_SOLAR_TIMEZONE = "America/Denver"
SOLAR_PERSISTENCE_CUTOFF_H = 240


def _to_utc_index(index_like) -> pd.DatetimeIndex:
    """Return a UTC-aware DatetimeIndex from naive/aware input timestamps."""
    idx = pd.DatetimeIndex(pd.to_datetime(index_like))
    if idx.tz is None:
        return idx.tz_localize("UTC")
    return idx.tz_convert("UTC")


def _fill_late_solar_with_persistence(
    solar_df: pd.DataFrame,
    init_dt_naive: datetime.datetime,
    delta_h: int,
    max_h: int,
    value_col: str = "sdswrf",
    cutoff_h: int = SOLAR_PERSISTENCE_CUTOFF_H,
    local_tz: str = LOCAL_SOLAR_TIMEZONE,
) -> pd.DataFrame:
    """Fill/overwrite >cutoff solar values using deterministic local-hour persistence.

    Build an anchor lookup from valid values at or before ``cutoff_h`` by taking
    the median for each local clock hour in ``local_tz`` (America/Denver by
    default). Each forecast timestamp beyond cutoff is then assigned the anchor
    median for its matching local hour. If a local-hour bin is unavailable in
    the anchor window, use the nearest available local-hour bin (cyclic over
    24h), then fall back to the anchor-wide median (or 0.0 if anchor is empty).
    UTC->local conversion keeps behavior deterministic across MST/MDT.
    """
    if value_col not in solar_df.columns:
        raise KeyError(f"Missing required solar column '{value_col}'.")

    out = solar_df.copy()
    out.index = pd.to_datetime(out.index)

    idx_utc = _to_utc_index(out.index)
    init_utc = pd.Timestamp(init_dt_naive, tz="UTC")
    fxx = np.round((idx_utc - init_utc).total_seconds() / 3600.0).astype(int)
    out["fxx"] = fxx

    anchor_mask = (out["fxx"] <= int(cutoff_h)) & out[value_col].notna()
    anchor = out.loc[anchor_mask, value_col]
    if anchor.empty:
        # Preserve deterministic behavior if early data is unexpectedly absent.
        fallback_value = 0.0
        hour_lookup = {}
    else:
        anchor_idx_utc = idx_utc[anchor_mask]
        anchor_hours = pd.Series(
            anchor_idx_utc.tz_convert(local_tz).hour,
            index=anchor.index,
            dtype=int,
        )
        grouped = anchor.groupby(anchor_hours).median()
        hour_lookup = {int(hour): float(val) for hour, val in grouped.items()}
        fallback_value = float(anchor.median())

    available_hours = sorted(hour_lookup.keys())

    def _lookup_local_hour(local_hour: int) -> float:
        if local_hour in hour_lookup:
            return float(hour_lookup[local_hour])
        if available_hours:
            nearest_hour = min(
                available_hours,
                key=lambda h: min((h - local_hour) % 24, (local_hour - h) % 24),
            )
            return float(hour_lookup[nearest_hour])
        return float(fallback_value)

    for h in np.arange(cutoff_h + int(delta_h), int(max_h) + 1, int(delta_h), dtype=int):
        ts_utc = init_utc + pd.Timedelta(hours=int(h))
        local_hour = int(ts_utc.tz_convert(local_tz).hour)
        approx_val = _lookup_local_hour(local_hour)
        out.loc[ts_utc.tz_localize(None), value_col] = float(approx_val)
        out.loc[ts_utc.tz_localize(None), "fxx"] = int(h)

    out = out.sort_index()
    out["fxx"] = out["fxx"].astype(int)
    return out


def create_forecast_dataframe(variable_ts, variable_name,
                                init_time=None, add_h_init_time=0):
    """
    Create dataframe with the index (date/time), variable, lead hour of fcst.

    Args:
        variable_ts (
            xarray.DataArray, xarray.Dataset, pandas.DataFrame, pandas.Series
            ): Time series data for the variable.
        variable_name (str): Name of the variable to include in the dataframe.

    Returns:
        pd.DataFrame: Dataframe with columns for the variable and lead hour of forecast (fxx).
    """
    if isinstance(variable_ts, (xr.DataArray,xr.Dataset)):
        df = variable_ts.to_dataframe()
    elif isinstance(variable_ts, pd.DataFrame):
        df = variable_ts
    elif isinstance(variable_ts, pd.Series):
        df = variable_ts.to_frame()
    else:
        raise ValueError("Input variable_ts must be an xarray.Dataset, "
                         "pandas.DataFrame, or pandas.Series.")
    pass

    df.index = pd.to_datetime(df.index)
    init_time = df.index[0] if init_time is None else init_time
    df['fxx'] = np.round((df.index - init_time).total_seconds(
                            ) // 3600).astype(int)

    # Add add_h_init_time to the values in fxx
    # Used, e.g., if the dataframe given starts at a later lead forecast hour

    # If we do this, add new columns to maintain the frequency back to fxx=0
    # Assign np.nan values for those first h hours rows

    # df['fxx'] = df['fxx'] + add_h_init_time

    # if variable_name not in ["si10", "sdswrf","sde","prmsl",]:
    #     pass

    df = df[[variable_name, 'fxx']]
    return df

def get_latlon_timeseries_df(init_dt_naive, vrbl, q_str, v_key, lat, lon,
                                delta_h, max_0p25_h=240,
                                max_0p5_h=384, member='p01',
                                product="atmos.25",
                                skip_first_0p5=True,
                             ):

    print(f"Getting {vrbl} at lat {lat}, lon {lon} for {init_dt_naive}")

    print("First, get the time series for the 0p25 degree resolution")
    ds_ts_early = load_variable(init_dt_naive, 0, max_0p25_h, delta_h, q_str,
                                        product, member=member)
    ts_early = ds_ts_early.sel(method='nearest', latitude=lat,
                                       longitude=lon)

    delta_h = 6 if delta_h < 6 else delta_h
    start_hr = 240 + delta_h if skip_first_0p5 else 240
    print("Next, get the time series for the 0p5 degree resolution")
    ds_ts_later = load_variable(init_dt_naive,start_hr, max_0p5_h, delta_h,
                                    q_str,"atmos.5", member=member,)
    ts_later = ds_ts_later.sel(method='nearest', latitude=lat,
                               longitude=lon)

    # Join the two time series (0p25 / 0p5) with consistent time labels as a dataframe
    clyfar_input = xr.concat([ts_early, ts_later], dim='time')

    print("Two time series joined. Now returning a dataframe.")
    df = clyfar_input.to_dataframe()

    if 'step' not in df.columns:
        # Older Herbie/xarray fallbacks sometimes lack a 'step' column, so
        # reconstruct the lead time from the timestamp itself.
        if isinstance(df.index, pd.MultiIndex) and 'time' in df.index.names:
            time_index = df.index.get_level_values('time')
        elif isinstance(df.index, pd.DatetimeIndex):
            time_index = df.index
        elif 'time' in df.columns:
            time_index = pd.to_datetime(df['time'])
        else:
            raise KeyError(
                "Unable to derive forecast step because 'time' is missing"
            )
        time_index = pd.to_datetime(time_index)
        step = (
            (time_index - pd.Timestamp(init_dt_naive)).total_seconds() // 3600
        ).astype(int)
        df = df.copy()
        df['step'] = step

    clyfar_input = df[['step', v_key]]

    return clyfar_input

def get_grid_timeseries(init_dt_naive, start_h, max_h, q_str, masks, delta_h,
                        member='c00', skip_first_0p5=True,
                        do_early=True, do_late=True):
    """
    """
    # TODO - need to find where init time is being derived from first index
    # This isn't always true when, e.g., we skip analysis time as it
    # doesn't make sense for an accumulation value. I'd like to identify
    # dataframe time series and have a np.nan for these times so we
    # have a consistent time index for all variables/forecast times.
    # Then we can ignore a "missing" time zero for xarrays, while
    # assuming dataframes always have initialisation time as row/index zero.

    assert any([do_early, do_late]), "At least one do_early or do_late = True"
    L = Lookup()

    if do_early:
        ds_ts_early = load_variable(init_dt_naive, start_h, 240, delta_h, q_str,
                            "atmos.25", member=member,)
        try:
            if L.find_vrbl_keys(q_str)['mf_name'] == 'wind':
                ds_ts_early = ds_ts_early.herbie.with_wind("speed")
        except KeyError:
            pass
        mask_early = create_mask(ds_ts_early, masks["0p25"])
        ds_masked_early = ds_ts_early.where(mask_early)

    if do_late:
        delta_h_0p5 = max(delta_h, 6)
        start_h_0p5 = 240+delta_h_0p5 if skip_first_0p5 else 240
        ds_ts_late = load_variable(init_dt_naive, start_h_0p5, max_h,
                            delta_h_0p5,q_str,"atmos.5", member=member)
        try:
            if L.find_vrbl_keys(q_str)['mf_name'] == 'wind':
                ds_ts_late = ds_ts_late.herbie.with_wind("speed")
        except KeyError:
            pass
        mask_late = create_mask(ds_ts_late, masks["0p5"])
        ds_masked_late = ds_ts_late.where(mask_late)

    if do_early and do_late:
        return ds_masked_early, ds_masked_late
    elif do_early:
        return ds_masked_early
    elif do_late:
        return ds_masked_late

def process_nwp_timeseries(init_dt_naive: datetime.datetime,
                            start_h: int, max_h: int, masks: dict,
                            delta_h: int, variable_type: str,
                            quantile: float = 0.9, member: str ='p01',
                            do_early: bool = True, do_late: bool = True,
                            pc_method: str = "linear"):
    """
    Reduce sequence of masked GEFS grids to time series of representative values.

    Args:
        init_dt_naive (datetime.datetime): The initial datetime of the forecast.
        start_h (int): The starting forecast hour.
        max_h (int): The maximum forecast hour (inclusive)
        masks (dict): Dictionary of masks for the 0.25 and 0.5 degree grids.
        delta_h (int): The time step in hours.
        variable_type (str): The type of variable to process.
        quantile (float): The quantile to use for the forecast value.
        member (str): The GEFS member to use.
        do_early (bool): Whether to process the high-resolution (0p25)
            data (<= 240 hours).
        do_late (bool): Whether to process the lower-resolution (0p5)
            data (> 240 hours). Will skip 240 as that's covered by 0p25.
        pc_method (str): The method to use for calculating percentiles.

    Returns:
        xarray.DataArray: The time series of the processed variable. Format: ?
    """
    assert any([do_early, do_late]), "At least one do_early or do_late = True"
    L = Lookup()

    # Extract grid time series using variable-specific query
    early_series, later_series = get_grid_timeseries(
        init_dt_naive,
        start_h,
        max_h,
        L.string_dict[variable_type]["gefs_query"],
        masks,
        delta_h,
        member=member,

    )

    if do_early:
        # Process high-resolution (early) data
        mask_early = create_mask(early_series, masks["0p25"])
        masked_early = early_series.where(mask_early)
        quantile_early = masked_early.quantile(
                                quantile, dim=("latitude", "longitude"),
                                method=pc_method)

    if do_late:
        # Process lower-resolution (later) data
        mask_later = create_mask(later_series, masks["0p5"])
        masked_later = later_series.where(mask_later)
        quantile_later = masked_later.quantile(
            quantile, dim=("latitude", "longitude"),
            method=pc_method)

    # TODO - daily values such as near-noon insolation and daily wind values

    if do_early and do_late:
        # Concatenate temporal sequences now we reduced dimension
        return xr.concat([quantile_early, quantile_later], dim='time')
    elif do_early:
        return quantile_early
    elif do_late:
        return quantile_later

# Implementation for specific variables
# TODO - change the "args/kwargs" to more explicit variables for ease of use
def do_nwpval_snow(init_dt_naive: datetime.datetime,
                   start_h: int, max_h: int, masks: dict,
                   delta_h: int, member: str ='p01',
                   do_early: bool = True, do_late: bool = True,
                   initialise_with_obs = False,
                   ) -> xr.DataArray:
    """Compute a representative forecast value for snow depth in the Basin.

    We choose the method used to calculate percentiles as "hazen" because
    there are sufficient COOP stations to use this method. Just. It
    is important to capture extremes. We can consider a lower percentile or
    straight maximum if the current method is too noisy or misses extremes.

    Args:
        init_dt_naive (datetime.datetime): The initial datetime of the forecast.
        start_h (int): The starting forecast hour.
        max_h (int): The maximum forecast hour (inclusive)
        masks (dict): Dictionary of masks for the 0.25 and 0.5 degree grids.
        delta_h (int): The time step in hours.
        member (str): The GEFS member to use.
        do_early (bool): Whether to process the high-resolution (0p25)
            data (<= 240 hours).
        do_late (bool): Whether to process the lower-resolution (0p5)
            data (> 240 hours). Will skip 240 as that's covered by 0p25.
        initialise_with_obs (bool): Whether to offset the forecast by the
            current observed representative value.

    Returns:
        xarray.DataArray: The time series of snow depth in the Basin.

    """
    snow_ts = process_nwp_timeseries(
                    init_dt_naive, start_h, max_h, masks,
                    delta_h, variable_type='snow',
                    quantile = 0.75, member = member, do_early = do_early,
                    do_late = do_late, pc_method = "hazen",
                    )

    if initialise_with_obs:
        # TODO - fully test and also turn off if zero depth is reachef
        # Also we need to return the offset amount so it can be be displayed
        # TODO consider a log file with things like this?

        # Offset the timeseries by the current observed representative value.
        # This is like a "data assimilation" for the time series
        # If any snow-depth values are negative, set them to zero.

        # Create a representative snow-depth value
        # snow_raw = get_representative_obs("snow", 14, snow_stids,
        #                                         timezone="US/Mountain")

        # If turned off, or too much missing data, this is backup.
        repr_val = 0

        # Load data via Synoptic Weather API (and SynopticPy)
        recent_df = download_most_recent("snow", 7,
                                            snow_stids).df
        repr_snow = do_repval_snow(recent_df, snow_stids)

        # Use most recent value for "DA"
        repr_val = float(repr_snow.loc[repr_snow.index[-1]].squeeze())

        # Offset the timeseries by the representative value vs original value
        offset = float(snow_ts.isel(time=0).sde.values.squeeze()) - repr_val

        # positive means GEFS depth was higher
        snow_ts = snow_ts - offset

        # TODO - export this offset value for visualisations
        # Set negative snow-depths to zero
        snow_ts = snow_ts.where(snow_ts > 0, 0)

    # Convert metres -> millimetres for downstream use
    snow_ts = snow_ts * 1000.0
    return snow_ts

def do_nwpval_wind(init_dt_naive: datetime.datetime,
                   start_h: int, max_h: int, masks: dict,
                   delta_h: int, member: str ='p01',
                   do_early: bool = True, do_late: bool = True,
                   ) -> xr.DataArray:
    """Compute a representative forecast value for wind speed.

    There are sufficient stations to use the "hazen" method for percentiles.

    Args:
        init_dt_naive (datetime.datetime): The initial datetime of the forecast.
        start_h (int): The starting forecast hour.
        max_h (int): The maximum forecast hour (inclusive)
        masks (dict): Dictionary of masks for the 0.25 and 0.5 degree grids.
        delta_h (int): The time step in hours.
        member (str): The GEFS member to use.
        do_early (bool): Whether to process the high-resolution (0p25)
            data (<= 240 hours).
        do_late (bool): Whether to process the lower-resolution (0p5)
            data (> 240 hours). Will skip 240 as that's covered by 0p25.

    Returns:
        xarray.DataArray: The time series of wind depth in the Basin.
    """
    return process_nwp_timeseries(
                    init_dt_naive, start_h, max_h, masks,
                    delta_h, variable_type='wind',
                    quantile = 0.5, member = member, do_early = do_early,
                    do_late = do_late, pc_method="hazen",
                    )

# def do_nwpval_solar_alt():
#     """This version uses """

def do_nwpval_solar(init_dt_naive: datetime.datetime,
                    start_h: int, max_h: int, masks: dict,
                    delta_h: int, member: str ='p01',
                    do_early: bool = True, do_late: bool = True,
                    approximate_0p5 = True,
                    ) -> xr.DataArray:
    """Compute a representative forecast value for solar radiation.

    Base values use a basin-mask 0.9 quantile at each forecast timestamp.

    If ``approximate_0p5`` is True, all forecast hours beyond +240 are replaced
    by deterministic local-hour persistence built from the <=240h segment:
    per local clock hour (America/Denver), apply the anchor median from the
    early range. This preserves seasonal/diurnal structure while retaining a
    recent optical-depth regime proxy at extended leads.
    """
    solar_ts = process_nwp_timeseries(
                        init_dt_naive, start_h, max_h, masks,
                        delta_h, variable_type='solar',
                        quantile = 0.9, member = member, do_early = do_early,
                        do_late = do_late, pc_method="hazen",
                        )

    if approximate_0p5:
        # Keep <=240h quantile values as anchors and overwrite >240h with
        # deterministic local-hour persistence from that anchor window.

        # Start time
        if max_h <= 240:
            return solar_ts

        # Convert to dataframe and fill late range using deterministic
        # local-hour persistence anchored to <=240h values.
        solar_df = solar_ts.to_dataframe()
        solar_ts = _fill_late_solar_with_persistence(
            solar_df=solar_df,
            init_dt_naive=init_dt_naive,
            delta_h=delta_h,
            max_h=max_h,
            value_col="sdswrf",
            cutoff_h=SOLAR_PERSISTENCE_CUTOFF_H,
            local_tz=LOCAL_SOLAR_TIMEZONE,
        )

    return solar_ts

def do_nwpval_temp(init_dt_naive,
                   start_h: int, max_h: int, masks: dict,
                   delta_h: int, member: str ='p01',
                   do_early: bool = True, do_late: bool = True,
                   ) -> xr.DataArray:

    """We want the 50th percentile over all stations, for now!

    Will be replaced by pseudo-lapse-rate in the planned 1.0+ builds, but this allows plots
    of raw GEFS data.

    Temperature here is kind of useless as it's a function of height that
    is more useful as (a) a gradient to estimate pseudo-lapse-rate and (b)
    to help judgement of whether snow persists at Basin level.

    TODO: make min/max for each station, and implement variation with height
        (pseudo-lapse-rate) to go into the FIS inferences.
    """
    temp_ts = process_nwp_timeseries(
        init_dt_naive, start_h, max_h, masks,
        delta_h, variable_type='temp',
        quantile = 0.5, member = member, do_early = do_early,
        do_late = do_late, pc_method = "hazen",
    )
    # TODO - I'm not sure if this is where to convert to C but will for now
    temp_ts = temp_ts - 273.15

    return temp_ts

def do_nwpval_mslp(init_dt_naive, lat, lon, delta_h,
                     member, quantile=0.5):
    """Compute a representative forecast value for MSLP at a given lat/lon.

    Args mirror prior implementation; quantile is unused because we extract a
    single nearest gridpoint time series for KVEL.
    """
    logger = logging.getLogger(__name__)
    delta_h = max(int(delta_h), 1)
    delta_h_0p5 = max(delta_h, 6)
    max_0p25 = 240
    max_0p5 = 384
    hours_0p25 = range(0, max_0p25 + 1, delta_h)
    start_0p5 = 240 + delta_h_0p5
    hours_0p5 = range(start_0p5, max_0p5 + 1, delta_h_0p5) if start_0p5 <= max_0p5 else []
    var_name = GEFSData._PRESSURE_VAR_NAME

    def _collect_hours(hours, product):
        records = []
        for fxx in hours:
            try:
                ds = GEFSData.fetch_pressure(
                    init_dt_naive,
                    fxx,
                    product=product,
                    member=member,
                    remove_grib=True,
                )
                field = ds[var_name].sel(latitude=lat, longitude=lon, method="nearest")
                value = float(field.squeeze().values)
                # Valid time = init time + forecast hour (ds.time is init time, not valid time)
                valid_time = init_dt_naive + datetime.timedelta(hours=int(fxx))
            except Exception as exc:
                # Catch ALL exceptions - missing data at extended range is expected
                # Herbie can raise various errors for missing index files, HTTP 404s, etc.
                logger.warning(
                    "MSLP fetch failed for f%03d (%s: %s); storing NaN",
                    fxx,
                    type(exc).__name__,
                    exc,
                )
                logger.debug("Full traceback for f%03d:", fxx, exc_info=True)
                valid_time = init_dt_naive + datetime.timedelta(hours=int(fxx))
                value = np.nan
            records.append((valid_time, value))
        return records

    all_records = []
    all_records.extend(_collect_hours(hours_0p25, "atmos.25"))
    if hours_0p5:
        all_records.extend(_collect_hours(hours_0p5, "atmos.5"))

    if not all_records:
        raise RuntimeError("No forecast hours processed for MSLP time series")

    # Sort by time and drop duplicates (keep earliest)
    all_records.sort(key=lambda rec: rec[0])
    times, values = zip(*all_records)
    df = pd.DataFrame({var_name: values}, index=pd.to_datetime(times))
    df = df[~df.index.duplicated(keep="first")]
    df.sort_index(inplace=True)
    qty = (np.asarray(df[var_name].values) * units.pascal).to(units.hectopascal)
    df[var_name] = qty.magnitude
    df.attrs = df.attrs or {}
    df.attrs[var_name] = {"units": str(qty.units)}
    return df


def create_mask(ds, mask):
    broadcast_mask = xr.DataArray(
        mask,
        dims=("latitude", "longitude"),
        coords={"latitude": ds.latitude, "longitude": ds.longitude}
    ).expand_dims(dim={"time": ds.time})
    return broadcast_mask
