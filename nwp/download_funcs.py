"""Helper functions to do mass downloading of NWP weather data.
"""
import datetime
import os
import time
from functools import wraps
import requests
from urllib3.exceptions import ReadTimeoutError

import numpy as np
import pandas as pd
import xarray as xr

from nwp.gefsdata import GEFSData

def load_variable(init_dt, start_h, max_h, delta_h, q_str, product,
                  member='c00', remove_grib=False,):
    """
    Generalized function to load a variable from GEFS data.

    If product (e.g., 0.25 deg) isn't available (past 240 hours), use 0.5 deg.
    This will be interpolated onto the same finer grid of 0.25 deg. If product
    is 0.5 deg, it will be used as is.

    Args:
        init_dt (datetime.datetime): Initial datetime.
        max_h (int): Maximum forecast hour.
        delta_h (int): Time step in hours.
        q_str (str): Query string for the variable.
        product (str): Product type (e.g., "atmos.5", "atmos.25").
        member (str): Ensemble member (default is 'c00').
        remove_grib (bool): Whether to remove the GRIB file after loading (default is True).

    Returns:
        xarray.Dataset: Concatenated dataset along the time dimension.
    """
    # Initialize an empty list to store each data slice
    data_slices = []

    # Get a time series for each grid cell in this member
    if product == "atmos.5":
        delta_h = max(delta_h, 6)
    fchrs = [int(x) for x in np.arange(start_h, max_h+1, delta_h)]
    # fchr2 = np.arange(240+delta_h_0p5, max_h+1, delta_h_0p5, dtype=int)
    pass

    for nf, f in enumerate(fchrs):
        # Now we do this above when selecting the forecast hours
        if f < start_h:
            continue

        # Hard coding the limit of forecast hours for 0.25 degree data
        # Also assuming we only use GEFS, not e.g. HRRR
        # TODO change hard coding when using non-GEFS data
        resol = "atmos.5" if f>240 else product
        ds_ts = GEFSData.get_cropped_data(init_dt, fxx=f, q_str=q_str, product=resol,
                                          remove_grib=remove_grib, member=member)
        ds_ts = ds_ts.assign_coords(time=init_dt + datetime.timedelta(hours=f))
        data_slices.append(ds_ts)

    # Concatenate the list of data slices along a new time dimension
    ds_time_series = xr.concat(data_slices, dim='time')

    # Note this means the grids are different for the 0.5 and 0.25 degree data?
    # TODO check lat/lon where relevant.
    return ds_time_series

def check_and_create_latlon_files(deg_res, fdir='./data/geog'):
    """Check if lat/lon files exist for a given resolution, and create them if not.

    Args:
        deg_res (str): Degree resolution (e.g., "0p25", "0p5").
        fdir (str): Directory to save the files (default is 'data').

    Returns:
        dict: Dictionary with latitudes and longitudes arrays.
    """
    if not os.path.exists(fdir):
        os.makedirs(fdir)

    lat_file = os.path.join(fdir, f"gefs{deg_res}_latitudes.parquet")
    lon_file = os.path.join(fdir, f"gefs{deg_res}_longitudes.parquet")

    if os.path.exists(lat_file) and os.path.exists(lon_file):
        lats = pd.read_parquet(lat_file).values
        lons = pd.read_parquet(lon_file).values
    else:
        ds_ts = load_variable(datetime.datetime(2023, 2, 3, 0, 0, 0),
                              start_h=0, max_h=0, q_str=":PRMSL", delta_h=3,
                              product=f"atmos.{deg_res[2:]}", member='p01',)
        lats = ds_ts.latitude.values
        lons = ds_ts.longitude.values

        # Create a meshgrid so we have indices for our grid
        lons, lats = np.meshgrid(lons, lats)

        # Save these dataframes for loading in future in parquet form
        pd.DataFrame(lats).to_parquet(lat_file)
        pd.DataFrame(lons).to_parquet(lon_file)

    return {'latitudes': lats, 'longitudes': lons}

def retry_download_backoff(retries=3, backoff_in_seconds=1):
    """Retry a function with exponential backoff. Use as decorator.

    Args:
        retries (int): Number of retries.
        backoff_in_seconds (int): Initial backoff time in seconds.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            x = 0
            while True:
                try:
                    return func(*args, **kwargs)
                except (requests.exceptions.ReadTimeout,
                        requests.exceptions.ConnectionError,
                        ReadTimeoutError) as e:
                    if x == retries:
                        raise e
                    sleep = (backoff_in_seconds * 2 ** x +
                             np.random.uniform(0, 1))
                    time.sleep(sleep)
                    x += 1
                    print(f"Retry {x} after {sleep:.1f}s sleep")
        return wrapper
    return decorator
