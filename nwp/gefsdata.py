import datetime
import os
import multiprocessing as mp
import tempfile

import numpy as np
import pandas as pd
from cartopy import crs as ccrs
import xarray as xr
from herbie import Herbie
import fasteners

from nwp.datafile import DataFile
from utils.download_utils import retry_download_backoff

# At the top of the file, enforce spawn context
if mp.get_start_method() != 'spawn':
    try:
        mp.set_start_method('spawn', force=True)
    except RuntimeError:
        print("Warning: Could not set spawn context. Already initialized.")

class GEFSData(DataFile):
    LOCK_DIR = os.getenv("CLYFAR_TMPDIR")

    def __init__(self):
        """Download, process GEFS data.
        """
        super().__init__()

    @classmethod
    def generate_timeseries(cls, fxx, inittime, gefs_regex, ds_key, lat, lon,
                            product,member="c00", remove_grib=True):
        """Need more info on variable names etc

        product here is "0.25 deg" etc
        """
        timeseries = []
        validtimes = []
        for f in fxx:
            validtime = inittime + datetime.timedelta(hours=f)
            H = cls.setup_herbie(inittime, fxx=f, product=product, model="gefs",
                                 member=member)
            ds = cls.get_CONUS(gefs_regex, H, remove_grib=remove_grib)
            # TODO: move the cropping method to a more general script (e.g., geog_funcs)
            ds_crop = cls.crop_to_UB(ds)
            val = cls.get_closest_point(ds_crop, ds_key, lat, lon)
            validtimes.append(validtime)
            timeseries.append(val.values)
        ts_df = pd.DataFrame({ds_key:timeseries},index=validtimes)
        return ts_df

    @staticmethod
    def setup_herbie(inittime, fxx=0, product="nat", model="gefs",member='c00'):
        H = Herbie(
            inittime,
            model=model,
            product=product,
            fxx=fxx,
            member=member,
        )
        return H

    @staticmethod
    def __OLD_get_CONUS(qstr, herbie_inst, remove_grib=True):
        ds = herbie_inst.xarray(qstr, remove_grib=remove_grib)
        ds = ds.metpy.parse_cf()
        return ds

    @classmethod
    @retry_download_backoff(retries=3, backoff_in_seconds=1)
    def safe_get_CONUS(cls, qstr, herbie_inst, remove_grib=True):
        """
        Safely download and process GRIB file using fasteners.
        """
        # Create unique lock file path based on the GEFS data request
        lock_path = os.path.join(
            cls.LOCK_DIR,
            f"herbie_{herbie_inst.date:%Y%m%d_%H}_{herbie_inst.fxx:03d}_{herbie_inst.member}.lock"
        )

        lock = fasteners.InterProcessLock(lock_path)

        with lock:
            ds = herbie_inst.xarray(qstr, remove_grib=remove_grib)
            ds = ds.metpy.parse_cf()

        if os.path.exists(lock_path):
            os.remove(lock_path)

        return ds

    @staticmethod
    def get_CONUS(qstr, herbie_inst, remove_grib=True):
        """
        Maintain backward compatibility but use safe version
        """
        return GEFSData.safe_get_CONUS(qstr, herbie_inst, remove_grib)

    @staticmethod
    def get_closest_point(ds, vrbl, lat, lon):
        point_val = ds[vrbl].sel(latitude=lat, longitude=lon, method="nearest")
        return point_val

    @staticmethod
    def crop_to_UB(ds, ):
        sw_corner = (39.4, -110.9)
        ne_corner = (41.1, -108.5)
        lats = ds.latitude.values
        lons = ds.longitude.values

        if np.max(lons) > 180.0:
            lons -= 360.0

        # Note the reserved latitude order!
        ds_sub = ds.sel(latitude=slice(ne_corner[0], sw_corner[0]),
                        longitude=slice(sw_corner[1], ne_corner[1]))
        return ds_sub

    @classmethod
    def get_cropped_data(cls,inittime,fxx,q_str,product="nat", remove_grib=True,
                         member="c00"):
        """JRL: I'm not sure if this is needed. Speeds up cropped data generation?

        Args:
            inittime (datetime.datetime)
        """
        H = cls.setup_herbie(inittime, fxx=fxx, product=product, member=member)
        ds = cls.get_CONUS(q_str, H, remove_grib=remove_grib)
        ds_crop = cls.crop_to_UB(ds)
        return ds_crop

    @classmethod
    def get_profile_df(cls,ds_T,ds_Z,lat,lon,max_height=10E3):
        # Label altitudes
        # can get profile of other things than temp...

        # Pressure levels not identical for T and Z
        T_P = ds_T.isobaricInhPa.values
        Z_P = ds_Z.isobaricInhPa.values

        T_prof = cls.get_closest_point(ds_T, "t", lat, lon).values - 273.15  # Celsius
        df_T = pd.DataFrame({"temp":T_prof}, index=T_P)

        Z_prof = cls.get_closest_point(ds_Z, "gh", lat, lon).values # m
        df_Z = pd.DataFrame({"height":Z_prof}, index=Z_P)

        # Need to merge and have NaNs where missing
        df = pd.merge(df_T,df_Z,left_index=True, right_index=True, how="outer")

        # Now we find where Z_prof < max_height (m)
        return df[df["height"] < max_height]