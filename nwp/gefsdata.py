import datetime
import os
import multiprocessing as mp
import tempfile
import logging

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
    _LATLON_CACHE = {}
    LOCK_DIR = os.getenv("CLYFAR_TMPDIR") or tempfile.gettempdir()

    def __init__(self, clear_cache=False):
        """Download, process GEFS data.
        """
        super().__init__()
        self.clear_cache = clear_cache

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
        os.makedirs(cls.LOCK_DIR, exist_ok=True)
        lock_path = os.path.join(
            cls.LOCK_DIR,
            f"herbie_{herbie_inst.date:%Y%m%d_%H}_{herbie_inst.fxx:03d}_{herbie_inst.member}.lock"
        )

        lock = fasteners.InterProcessLock(lock_path)

        with lock:
            if getattr(cls, "clear_cache", False):
                for path in (herbie_inst.idx, herbie_inst.grib):
                    if isinstance(path, str) and path and path.startswith("/"):
                        try:
                            os.remove(path)
                        except FileNotFoundError:
                            pass
            attempts = 2
            last_exc = None
            for attempt in range(attempts):
                try:
                    ds = herbie_inst.xarray(qstr, remove_grib=remove_grib)
                    break
                except Exception as exc:
                    last_exc = exc
                    if attempt < attempts - 1:
                        for path in (herbie_inst.idx, herbie_inst.grib):
                            if isinstance(path, str) and path and os.path.exists(path):
                                try:
                                    os.remove(path)
                                except FileNotFoundError:
                                    pass
                        continue
                    logger = logging.getLogger(__name__)
                    logger.warning("Herbie download failed for %s f%03d (%s); returning NaNs",
                                   herbie_inst.date, herbie_inst.fxx, exc)
                    import xarray as xr
                    import numpy as np
                    lat = lon = None
                    grid = getattr(herbie_inst, "grid", None)
                    if grid is not None:
                        lat = grid.lat
                        lon = grid.lon
                    if lat is None or lon is None:
                        product = getattr(herbie_inst, "product", "")
                        if product.endswith(".25") or ".25" in product:
                            res_key = "0p25"
                        elif product.endswith(".5") or ".5" in product:
                            res_key = "0p5"
                        else:
                            res_key = "0p25"
                        lat, lon = cls._load_latlon_arrays(res_key)
                    if lat is None or lon is None:
                        raise RuntimeError("No latitude/longitude grid available for fallback download") from exc
                    data_var = (qstr.strip(':') or 'var').lower()
                    data = np.full((1, lat.shape[0], lon.shape[0]), np.nan)
                    valid_time = getattr(herbie_inst, "valid_date", None)
                    if valid_time is None:
                        valid_time = getattr(herbie_inst, "date", None)
                    ds = xr.Dataset(
                        data_vars={data_var: (('time', 'latitude', 'longitude'), data)},
                        coords={
                            'time': ('time', [valid_time] if valid_time is not None else [0]),
                            'latitude': ('latitude', lat),
                            'longitude': ('longitude', lon),
                        },
                    )
            ds = ds.metpy.parse_cf()

        # if os.path.exists(lock_path):
        #     os.remove(lock_path)

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
        if "latitude" not in ds or "longitude" not in ds:
            raise KeyError("Dataset missing latitude/longitude for cropping")

        lons = ds.longitude
        if float(lons.max()) > 180.0:
            shifted = (((lons + 180.0) % 360.0) - 180.0)
            ds = ds.assign_coords(longitude=shifted)
            ds = ds.sortby('longitude')

        # Note the reversed latitude order!
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
    def _load_latlon_arrays(cls, res_key: str):
        cache = cls._LATLON_CACHE.setdefault(res_key, {})
        lat1d = cache.get('lat')
        lon1d = cache.get('lon')
        if lat1d is None or lon1d is None:
            suffix = "0p25" if res_key == "0p25" else "0p5"
            base_dir = os.path.join("data", "geog")
            lat_file = os.path.join(base_dir, f"gefs{suffix}_latitudes.parquet")
            lon_file = os.path.join(base_dir, f"gefs{suffix}_longitudes.parquet")
            try:
                lat_grid = pd.read_parquet(lat_file).values
                lon_grid = pd.read_parquet(lon_file).values
                lat1d = lat_grid[:, 0]
                lon1d = lon_grid[0, :]
            except FileNotFoundError:
                lat1d = lon1d = None
            cache['lat'] = lat1d
            cache['lon'] = lon1d
        return cache.get('lat'), cache.get('lon')

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
