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

    This one uses weighted average from the 6 hours around solar noon
    (3 either side). This is to optimally capture three forecast points,
    where we can do a weighted mean for "near-noon radiation" to mirror
    "near-zenith mean" in representative observations for solar.

    We use the hazen technique with low percentile value to capture something
    towards the maximum but there is a lot of uncertainty in solar radiation
    and the signal of time of year may be better as a replacement variable.

    The variable "approximate_0p5" is used to skip the coarser
    0.5 deg resolution GEFS forecasts (only every 6 hours; misses solar max)
    forecasts and instead use a high (?) percentile over all 0.25 degree
    forecast. (This will be separate from the issues not catching the max
    during each day, but we just want a signal). At this range, cloud cover
    is meaningless at the local scale, so let's hedge a good number using
    the previous measurements to approximate the solar insolation.

    TODO: manually set nighttime as zero, but we want daily max anyway.

    TODO:
    * After fxx=240, we don't have 3-h insolation so we should think about
    persistence or another function. Predictability is so low at that stage
    (uncertainty of sunrise/sunset way lower than cloud cover at 10-16
    days!) we could use persistence with a factor relating to humidity/cloud?

    """
    solar_ts = process_nwp_timeseries(
                        init_dt_naive, start_h, max_h, masks,
                        delta_h, variable_type='solar',
                        quantile = 0.9, member = member, do_early = do_early,
                        do_late = do_late, pc_method="hazen",
                        )

    if approximate_0p5:
        # Use 0.9 percentile from each timestamp's collection of solar stids
        # at the given time of day to form an approximate value for hours
        # where we don't have 3-h data from 0p25 GEFS.

        # Start time
        if max_h <= 240:
            return solar_ts

        datetime_arr = pd.to_datetime(solar_ts.time.values).to_pydatetime()
        # Now create a dataframe from these datetimes and the solar values
        solar_df = solar_ts.to_dataframe()
        solar_df.index = datetime_arr

        # I'm not sure why the dtype arguemnts doesn't work for me
        for h in np.arange(240+delta_h, max_h, delta_h, dtype=int):
            # Compute the representative solar value for this time
            # Subset all solar values for the first ~9 days at this hour of day
            timestamp = init_dt_naive + datetime.timedelta(hours=int(h))
            hour = timestamp.hour

            pass

            subset_df = solar_df[solar_df.index.hour == hour]

            # Take quantile over the 9 or so days - seems to be too high?
            # Make dynamic e.g., maximum possible, factored by cloud cover
            approx_solar = subset_df['sdswrf'].quantile(0.5)

            # This timestamp may or may not exist
            # If it does, we want to overwrite the existing value with new one
            # If it doesn't, we want to add it to the dataframe.

            # Hard-coded snow string for now, pragmatic
            pass
            solar_df.loc[timestamp, 'sdswrf'] = approx_solar
            # solar_df = solar_df.reindex(sorted(solar_df.index))

        # Sort in chronological order (index, datetime)
        solar_ts = solar_df.sort_index()

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
                # Handle both scalar and array time coordinates
                time_val = ds.time.values
                valid_time = pd.to_datetime(
                    time_val.item() if hasattr(time_val, 'ndim') and time_val.ndim == 0 else time_val[0]
                )
            except (KeyError, IndexError, ValueError, RuntimeError) as exc:
                logger.warning(
                    "MSLP fetch failed for f%03d (%s); storing NaN",
                    fxx,
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
