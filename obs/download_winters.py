"""Download data from Synoptic Weather and saved to disc in parquet format (and the metadata in pickle).

You can run this standalone by editing the constants at the bottom of the script. Or import into another script."""

import os
import datetime
import numpy as np
import pytz

from obs.obsdata import ObsData

def download_winter_obs(start_year, end_year, start_month, end_month, start_day, end_day, obs_vars,
                                    fdir="../data", qc="all"):
    """
    Download observations from Synoptic for each winter and save to disk.

    Args:
        start_year (int): The starting year of the range.
        end_year (int): The ending year of the range.
        start_month (int): The starting month of period.
        end_month (int): The ending month of period.
        start_day (int): The starting day of period.
        end_day (int): The ending day of period.
        obs_vars (list): List of observed variables to download.
        fdir (str): Directory to save the downloaded files. Default is "../data".
        qc (str): Quality control parameter. Default is "all" to do all checks available server-side.

    Returns:
        None
    """
    years = np.arange(start_year + 1, end_year + 1, dtype=int)

    for year in years:
        print(f"Downloading for winter {year-1}/{year}.")
        start_date = datetime.datetime(year-1, start_month, start_day)
        end_date = datetime.datetime(year, end_month, end_day)
        obs = ObsData(start_date, end_date, vrbl=obs_vars, qc=qc)
        obs.save_df(fdir, f"UB_obs_{int(year)}.parquet", drop_na=True)
        print("Saved to disk.")
        # print("Dataframe obs_df takes ", obs.df.memory_usage(index=True).sum()/1E6, "MB")
    return

def start_end_dates(dt, hours, quant_min=5, ):
    """ Create a start and end datetime
    """
    # TODO - if we want most recent 00Z, for instance, this will fail?
    # Roll back to most recent minute that is a multiple of quant_min (or 0)
    end_dt = dt.replace(minute=(dt.minute // quant_min) * quant_min,
                            second=0, microsecond=0)

    start_dt = end_dt - datetime.timedelta(hours=hours)
    # TODO - test to see if timezone works for mountain time too by adding 5 hours?
    return start_dt, end_dt

def download_most_recent(vrbl, n_days, stids, timezone="UTC",
                            qc="all"):
    """
    Download the most recent data from Synoptic Weather.

    Args:
        obs_vars (list): List of observed variables to download, e.g.,
            ["wind_speed", "wind_direction", "air_temp",]
        n_days (int): The number of days to download.
        timezone (str): The timezone for datetimes. Default is 'utc'.

    """
    now_dt = datetime.datetime.now(tz=pytz.timezone(timezone))
    start_dt, end_dt = start_end_dates(now_dt, hours=24*n_days)
    obs = ObsData(start_dt, end_dt, vrbl, qc=qc, stids=stids)
    return obs


if __name__ == "__main__":
    # Constants
    fdir = "../data"
    qc = "all"
    start_month = 12
    end_month = 3
    start_day = 1
    end_day = 15
    start_year = 2005
    end_year = 2024
    obs_vars = ["wind_speed", "wind_direction", "air_temp", "dew_point_temperature", "pressure", "snow_depth", "solar_radiation", "altimeter", "soil_temp", "sea_level_pressure", "snow_accum", "ceiling", "soil_temp_ir", "snow_smoothed", "snow_accum_manual", "snow_water_equiv", "net_radiation_sw", "sonic_air_temp", "sonic_vertical_vel", "vertical_heat_flux", "outgoing_radiation_sw", "PM_25_concentration", "ozone_concentration", "derived_aerosol_boundary_layer_depth", "NOx_concentration", "PM_10_concentration"]

    # Run the download function with the constants
    download_winter_obs(start_year, end_year, start_month, end_month, start_day, end_day, obs_vars, fdir, qc)