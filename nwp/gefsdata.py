import datetime
import os
import subprocess
import numpy as np
import pandas as pd
from cartopy import crs as ccrs
import xarray as xr
from herbie import Herbie
from nwp.datafile import DataFile


class GEFSData(DataFile):
    def __init__(self):
        """Download, process GEFS data."""
        pass

    @classmethod
    def generate_timeseries(cls, fxx, inittime, gefs_regex, ds_key, lat, lon,
                            product="atmos.25", member="p01", remove_grib=True):
        """Generate a time series from GEFS data."""
        timeseries = []
        validtimes = []
        for f in fxx:
            validtime = inittime + datetime.timedelta(hours=f)
            try:
                # Ensure the file is downloaded
                file_path = cls.ensure_grib2_file(inittime, product, member, f, gefs_regex)
                if file_path:
                    # Open the dataset
                    ds = xr.open_dataset(file_path)  # Using netcdf now
                    ds = ds.metpy.parse_cf()
                    ds_crop = cls.crop_to_UB(ds)
                    val = cls.get_closest_point(ds_crop, ds_key, lat, lon)
                    validtimes.append(validtime)
                    timeseries.append(val.values)
                else:
                    print(f"Failed to download file for forecast hour {f}.")
            except FileNotFoundError as e:
                print(f"File not found for forecast hour {f}: {e}")
            except Exception as e:
                print(f"An error occurred for forecast hour {f}: {e}")
        ts_df = pd.DataFrame({ds_key: timeseries}, index=validtimes)
        return ts_df

    @staticmethod
    def setup_herbie(inittime, fxx=12, product="atmos.25", model="gefs", member="p01"):
        """Initialize Herbie with specified parameters."""
        H = Herbie(
            inittime,
            model=model,
            product=product,
            fxx=fxx,
            member=member,
        )
        print(f"Initialized Herbie with model={model}, product={product}, fxx={fxx}, member={member}")
        return H

    @staticmethod
    def get_CONUS(qstr, herbie_inst, remove_grib=True):
        """Fetch CONUS region data using Herbie."""
        try:
            ds = herbie_inst.xarray(qstr, remove_grib=remove_grib)
            ds = ds.metpy.parse_cf()
            print(f"Dataset variables: {list(ds.data_vars)}")
            print(f"Dataset coordinates: {list(ds.coords)}")
            return ds
        except FileNotFoundError as e:
            print(f"CONUS data not found: {e}")
            raise
        except Exception as e:
            print(f"Failed to fetch CONUS data: {e}")
            raise

    @staticmethod
    def get_closest_point(ds, vrbl, lat, lon):
        """Retrieve the value closest to the specified latitude and longitude."""
        try:
            point_val = ds[vrbl].sel(latitude=lat, longitude=lon, method="nearest")
            return point_val
        except KeyError as e:
            print(f"Variable '{vrbl}' not found in dataset: {e}")
            raise
        except Exception as e:
            print(f"Failed to select closest point: {e}")
            raise

    @staticmethod
    def crop_to_UB(ds):
        """Crop the dataset to the Upper Basin region."""
        try:
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
        except Exception as e:
            print(f"Failed to crop dataset: {e}")
            raise

    @classmethod
    def get_cropped_data(cls, inittime, fxx, q_str, product="nat", remove_grib=True):
        """Fetch and crop GEFS data."""
        try:
            H = cls.setup_herbie(inittime, fxx=fxx, product=product)
            ds = cls.get_CONUS(q_str, H, remove_grib=remove_grib)
            ds_crop = cls.crop_to_UB(ds)
            return ds_crop
        except Exception as e:
            print(f"Failed to get cropped data: {e}")
            raise

    @classmethod
    def get_profile_df(cls, ds_T, ds_Z, lat, lon, max_height=10E3):
        """Generate a profile dataframe from temperature and geopotential height datasets."""
        try:
            # Label altitudes
            T_P = ds_T.isobaricInhPa.values
            Z_P = ds_Z.isobaricInhPa.values

            T_prof = cls.get_closest_point(ds_T, "t", lat, lon).values - 273.15  # Celsius
            df_T = pd.DataFrame({"temp": T_prof}, index=T_P)

            Z_prof = cls.get_closest_point(ds_Z, "gh", lat, lon).values  # m
            df_Z = pd.DataFrame({"height": Z_prof}, index=Z_P)

            # Merge and handle NaNs
            df = pd.merge(df_T, df_Z, left_index=True, right_index=True, how="outer")

            # Filter based on max_height
            return df[df["height"] < max_height]
        except KeyError as e:
            print(f"Missing variable in dataset: {e}")
            raise
        except Exception as e:
            print(f"Failed to generate profile dataframe: {e}")
            raise

    @classmethod
    def ensure_grib2_file(cls, inittime, product, member, fxx, variable, save_dir='/Users/a02428741/data/gefs/'):
        """
        Ensure that the GRIB2 file is downloaded. If not, download using Herbie's Python API.
        Returns the file path if exists, else None.
        """
        date_str = inittime.strftime('%Y%m%d')
        hour_str = inittime.strftime('%H')
        # Fixed filename format to use correct GEFS naming
        file_name = f"subset_{hash(variable) & 0xFFFFFF:06x}_{member}.t{hour_str}z.pgrb2s.{product}.f{fxx:03d}.nc"
        file_path = os.path.join(save_dir, date_str, file_name)

        if not os.path.exists(file_path):
            print(f"File {file_path} not found. Attempting to download with Herbie's Python API.")
            # Initialize Herbie
            H = cls.setup_herbie(inittime, fxx=fxx, product=product, member=member)
            # Attempt to download the GRIB2 file
            try:
                qstr = variable
                ds = H.xarray(qstr, remove_grib=True)

                # Save directly to the correct location
                os.makedirs(os.path.join(save_dir, date_str), exist_ok=True)
                ds.to_netcdf(file_path)
                print(f"Saved file to {file_path}.")
                return file_path

            except Exception as e:
                print(f"Failed to download file with Herbie: {e}")
                return None
        else:
            print(f"File {file_path} already exists.")
            return file_path