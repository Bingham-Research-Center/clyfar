"""Take GEFS data and create a time series as representative value"""

import importlib
import datetime

import pandas as pd
import pytz
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import xarray as xr

from nwp.download_funcs import load_variable
from obs.download_winters import download_most_recent
from utils.lookups import Lookup

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
    clyfar_input = clyfar_input.to_dataframe()[['step', v_key]]

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
        if L.find_vrbl_keys(q_str)['mf_name'] == 'wind':
            ds_ts_early = ds_ts_early.herbie.with_wind("speed")
        mask_early = create_mask(ds_ts_early, masks["0p25"])
        ds_masked_early = ds_ts_early.where(mask_early)

    if do_late:
        delta_h_0p5 = max(delta_h, 6)
        start_h_0p5 = 240+delta_h_0p5 if skip_first_0p5 else 240
        ds_ts_late = load_variable(init_dt_naive, start_h_0p5, max_h,
                            delta_h_0p5,q_str,"atmos.5", member=member)
        if L.find_vrbl_keys(q_str)['mf_name'] == 'wind':
            ds_ts_late = ds_ts_late.herbie.with_wind("speed")
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

    Returns:
        xarray.DataArray: The time series of snow depth in the Basin.

    """
    snow_ts = process_nwp_timeseries(
                    init_dt_naive, start_h, max_h, masks,
                    delta_h, variable_type='snow',
                    quantile = 0.9, member = member, do_early = do_early,
                    do_late = do_late, pc_method = "hazen",
                    )
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
                    quantile = 0.9, member = member, do_early = do_early,
                    do_late = do_late, pc_method="hazen",
                    )

def do_nwpval_solar(init_dt_naive: datetime.datetime,
                    start_h: int, max_h: int, masks: dict,
                    delta_h: int, member: str ='p01',
                    do_early: bool = True, do_late: bool = True,
                    ) -> xr.DataArray:
    """Compute a representative forecast value for solar radiation.

    This one uses weighted average from the 6 hours around solar noon
    (3 either side). This is to optimally capture three forecast points,
    where we can do a weighted mean for "near-noon radiation" to mirror
    "near-zenith mean" in representative observations for solar.

    We use the hazen technique with low percentile value to capture something
    towards the maximum but there is a lot of uncertainty in solar radiation
    and the signal of time of year may be better as a replacement variable.

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
    return solar_ts

def do_nwpval_mslp(init_dt_naive, lat, lon, delta_h,
                     member, quantile=0.5):
    """Compute a representative forecast value for MSLP at a given lat/lon.

    In future, this may use a mask instead of lat/lon point extraction.

    We use nearest neighbour extraction for the lat/lon point. Too much
    uniertainty to justify point interpolation.

    TODO - quantile used to pick value for each day? Median (50)?

    Args:
        init_dt_naive (datetime): The initial datetime of the forecast.
        lat (float): The latitude of the point.
        lon (float): The longitude of the point.
        member (str): The GEFS member to use.
        quantile (float): The quantile to use for the forecast value. This
            is currently unused as MSLP uses a single value (one station)

    Returns:
        xarray.DataArray: The time series of MSLP at the point.

    """
    L = Lookup()
    ds_ts = get_latlon_timeseries_df(init_dt_naive, "mslp",
                                     L.string_dict["mslp"]["gefs_query"],
                                     L.string_dict["mslp"]["array_name"],
                                     lat, lon, delta_h, member=member,)
    # Group by local day (ensure it is in local time to do midnight to midnight)

    # Reduce time series of multiple times by taking median for day
    # pc_ts = ds_ts.quantile(quantile, dim=("latitude", "longitude"))

    # Currently only using KVEL so just return this!
    pc_ts = ds_ts
    return pc_ts


def create_mask(ds, mask):
    broadcast_mask = xr.DataArray(
        mask,
        dims=("latitude", "longitude"),
        coords={"latitude": ds.latitude, "longitude": ds.longitude}
    ).expand_dims(dim={"time": ds.time})
    return broadcast_mask