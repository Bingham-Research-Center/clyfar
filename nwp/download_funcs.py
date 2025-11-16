"""Helper functions to do mass downloading of NWP weather data.
"""
import datetime
import logging
import os


import numpy as np
import pandas as pd
import xarray as xr

from nwp.gefsdata import GEFSData
from utils.lookups import Lookup

def load_variable(init_dt, start_h, max_h, delta_h, q_str, product,
                  member='c00', remove_grib=False,):
    """
    Legacy wrapper retained for backward compatibility.

    Prefer :func:`herbie_load_variable`, which normalizes coordinates and logs diagnostics.
    """
    logger = logging.getLogger(__name__)
    logger.warning(
        "load_variable() is deprecated; use herbie_load_variable() instead."
    )
    return herbie_load_variable(
        init_dt=init_dt,
        start_h=start_h,
        max_h=max_h,
        delta_h=delta_h,
        vrbl=q_str,
        product=product,
        member=member,
        remove_grib=remove_grib,
    )


def herbie_load_variable(
    init_dt,
    start_h,
    max_h,
    delta_h,
    vrbl,
    product,
    member="c00",
    remove_grib=True,
):
    """
    Download GEFS data via Herbie.xarray with normalized metadata.

    Args mirror load_variable but accept either a Lookup synonym or raw GEFS query.
    """
    logger = logging.getLogger(__name__)
    lookup = Lookup()
    var_info = lookup.find_vrbl_keys(vrbl) or {}
    gefs_query = var_info.get("gefs_query", vrbl)
    array_name = var_info.get("array_name")
    if product == "atmos.5":
        delta_h = max(delta_h, 6)
    hours = np.arange(start_h, max_h + 1, delta_h, dtype=int)

    slices = []
    for fxx in hours:
        if fxx < start_h:
            continue
        resol = "atmos.5" if fxx > 240 else product
        logger.info(
            "Herbie fetch %s f%03d member=%s product=%s",
            gefs_query,
            fxx,
            member,
            resol,
        )
        try:
            ds = _herbie_fetch_slice(
                init_dt=init_dt,
                fxx=fxx,
                product=resol,
                member=member,
                query=gefs_query,
                remove_grib=remove_grib,
            )
        except Exception as exc:
            logger.error(
                "Herbie fetch failed for %s f%03d (%s); skipping slice",
                gefs_query,
                fxx,
                exc,
            )
            continue

        if array_name and array_name in ds:
            ds = ds[[array_name]]
        ds = _normalize_dataset_coords(ds, init_dt, fxx)
        slices.append(ds)

    if not slices:
        logger.warning(
            "Herbie loader returned no slices for %s; falling back to legacy GEFSData path.",
            gefs_query,
        )
        return _legacy_gefs_concat(
            init_dt=init_dt,
            start_h=start_h,
            max_h=max_h,
            delta_h=delta_h,
            q_str=gefs_query,
            product=product,
            member=member,
            remove_grib=remove_grib,
        )

    combined = xr.concat(slices, dim="time", combine_attrs="drop")
    return combined


def _herbie_fetch_slice(init_dt, fxx, product, member, query, remove_grib):
    """Call Herbie.xarray with consistent backend configuration."""
    H = GEFSData.setup_herbie(
        init_dt,
        fxx=fxx,
        product=product,
        member=member,
    )
    index_name = f"{H.model}_{H.member}_{product.replace('.', '')}_{init_dt:%Y%m%d%H}_f{fxx:03d}.idx"
    backend_kwargs = {
        "indexpath": str(GEFSData._CFGRIB_INDEX_DIR / index_name),
        "errors": "ignore",
    }
    try:
        ds = H.xarray(
            query,
            remove_grib=remove_grib,
            backend_kwargs=backend_kwargs,
        )
    except Exception:
        logger = logging.getLogger(__name__)
        logger.warning(
            "Herbie.xarray failed for %s f%03d; falling back to GEFSData.get_cropped_data",
            query,
            fxx,
        )
        ds = GEFSData.get_cropped_data(
            init_dt,
            fxx=fxx,
            q_str=query,
            product=product,
            member=member,
            remove_grib=remove_grib,
        )
    return ds


def _normalize_dataset_coords(ds, init_dt, fxx):
    """
    Drop transient coordinates and ensure we have a single time slice.
    """
    keep_coords = {"time", "latitude", "longitude"}
    drop_names = [
        name for name in ds.coords if name not in keep_coords
    ]
    if drop_names:
        ds = ds.drop_vars(drop_names, errors="ignore")
    valid_time = np.array([np.datetime64(init_dt + datetime.timedelta(hours=int(fxx)))])
    if "time" in ds.coords:
        ds = ds.drop_vars("time", errors="ignore")
    ds = ds.expand_dims("time")
    ds = ds.assign_coords(time=("time", valid_time))
    return ds


def _legacy_gefs_concat(
    init_dt,
    start_h,
    max_h,
    delta_h,
    q_str,
    product,
    member,
    remove_grib,
):
    """Fallback to legacy GEFSData.get_cropped_data loop."""
    data_slices = []
    if product == "atmos.5":
        delta_h = max(delta_h, 6)
    fchrs = np.arange(start_h, max_h + 1, delta_h, dtype=int)
    for f in fchrs:
        if f < start_h:
            continue
        resol = "atmos.5" if f > 240 else product
        ds_ts = GEFSData.get_cropped_data(
            init_dt,
            fxx=int(f),
            q_str=q_str,
            product=resol,
            remove_grib=remove_grib,
            member=member,
        )
        ds_ts = _normalize_dataset_coords(ds_ts, init_dt, f)
        data_slices.append(ds_ts)
    if not data_slices:
        raise RuntimeError(f"No GEFS slices available for {q_str} (legacy path)")
    return xr.concat(data_slices, dim="time", combine_attrs="drop")

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
