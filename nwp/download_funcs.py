"""Helper functions to do mass downloading of NWP weather data.
"""
import datetime
import os


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
    """Check if lat/lon files exist for a given resolution, and create them if not."""

    def generate_and_store():
        ds_ts = load_variable(datetime.datetime(2023, 2, 3, 0, 0, 0),
                              start_h=0, max_h=0, q_str=":PRMSL", delta_h=3,
                              product=f"atmos.{deg_res[2:]}", member='p01')
        lat_arr = ds_ts.latitude.values
        lon_arr = ds_ts.longitude.values
        lon_grid, lat_grid = np.meshgrid(lon_arr, lat_arr)
        lat_df = pd.DataFrame(lat_grid)
        lon_df = pd.DataFrame(lon_grid)
        lat_df.columns = lat_df.columns.astype(str)
        lon_df.columns = lon_df.columns.astype(str)
        lat_df.index = lat_df.index.astype(str)
        lon_df.index = lon_df.index.astype(str)
        lat_df.to_parquet(lat_file)
        lon_df.to_parquet(lon_file)
        return lat_grid, lon_grid

    if not os.path.exists(fdir):
        os.makedirs(fdir)

    lat_file = os.path.join(fdir, f"gefs{deg_res}_latitudes.parquet")
    lon_file = os.path.join(fdir, f"gefs{deg_res}_longitudes.parquet")

    if os.path.exists(lat_file) and os.path.exists(lon_file):
        try:
            lats = pd.read_parquet(lat_file).values
            lons = pd.read_parquet(lon_file).values
        except AttributeError:
            # Historical files written with non-string column names can confuse fastparquet
            os.remove(lat_file)
            os.remove(lon_file)
            lats, lons = generate_and_store()
    else:
        lats, lons = generate_and_store()

    return {'latitudes': lats, 'longitudes': lons}
