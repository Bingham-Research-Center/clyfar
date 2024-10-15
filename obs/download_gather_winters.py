"""A script to download observations from Synoptic for each winter and save to disc.

These are the constants:
* The set of stations
* The set of variables


"""

import os
import datetime

import numpy as np

from obs.obsdata import ObsData

### CONSTANTS ###
fdir = "../data"
qc = "all"

start_month = 12
end_month = 3
start_day = 1
end_day = 15

# Do last ten years (ending 2023/2024)
# The year indicates the end of the winter (i.e. the February's year)
years = np.arange(2005,2025)
# years = [2016,]

obs_vars = ["wind_speed", "wind_direction",
            "air_temp", "dew_point_temperature",
            "pressure", "snow_depth", "solar_radiation",
            "altimeter", "soil_temp",
            "sea_level_pressure", "snow_accum",
            "ceiling", "soil_temp_ir",
            "snow_smoothed", "snow_accum_manual", "snow_water_equiv",
            "net_radiation_sw",
            "sonic_air_temp", "sonic_vertical_vel",
            "vertical_heat_flux", "outgoing_radiation_sw",
            "PM_25_concentration", "ozone_concentration",
            "derived_aerosol_boundary_layer_depth",
            "NOx_concentration", "PM_10_concentration",
            ]

### PROCEDURE ###
# For each winter, download obs + metadata, save to disc

for year in years:
    print(f"Downloading for winter {year-1}/{year}.")
    start_date = datetime.datetime(year-1,start_month,start_day)
    end_date = datetime.datetime(year,end_month,end_day)
    obs = ObsData(start_date,end_date, vrbls=obs_vars, qc=qc)
    pass
    obs.save_df(fdir, f"UB_obs_{int(year)}.parquet", drop_na=True)
    print("Saved to disc.")

    # What is the memory footprint of the obs.df and metadata df?
    print("Dataframe obs_df takes ",
          obs.df.memory_usage(index=True).sum()/1E6, "MB")
    print("The metadata Dataframe takes up ",
            obs.meta_df.memory_usage(index=True).sum()/1E6, "MB")
    fpath = os.path.join(fdir, f"UB_obs_{year}.parquet")
    print("On disk:", os.path.getsize(
                fpath)/1E6, "MB")

