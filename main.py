"""main script for the project

Will eventually need one script using only obs to create a model.

TODO - create the best possible model and save as pickle; load at forecast time and use preprocessed NWP data.
"""
import os
import importlib
import datetime

import numpy as np

from nwp.gefsdata import GEFSData
from viz import plotting

test_fis = False
test_gefs_meteogram = False
test_gefs_map_plot = True

if test_fis:
    # Create Clyfar v0.1
    version = '0.1'
    v_str = version.replace('.', 'p')
    version_fpath = f'fis.v{v_str}'

    # Import FIS from v_py function return_fis
    module = importlib.import_module(version_fpath)

    # Get FIS instance
    # This is the control system more hidden from user
    ozone_ctrl = module.ozone_ctrl
    # This is out FIS class that wraps the control system
    ozone_sim = module.ozone_sim
    ozone = module.ozone

    # Get inputs
    inputs = {
        'snow': 100,
        'mslp': 1040E2,
        'wind': 1.5,
        'solar': 500
    }

    print(ozone_sim.generate_crisp_inference(inputs))
    print(ozone_sim.create_possibility_array())

# General settings for following GEFS/plotting tests

lon, lat = (360 - 109.6774, 40.0891) # Where is this?
init_dt = datetime.datetime(2023,12,5,18,0,0)

if test_gefs_meteogram:
    ts = GEFSData.generate_timeseries(list(range(0,240,12)), init_dt, ":SNOD:", "sde", lat, lon,
                                        product="atmos.25",member='mean',
                                        # To save time in testing we can save the grib files
                                        remove_grib=False)
    fig, ax = plotting.plot_meteogram(ts, "sde", title=None, save=None,second_df=None, second_col=None)
    fig.show()

if test_gefs_map_plot:
    # TODO: adjust visualisation settings and try different ones in this section (e.g., colour map, contour levels)

    ds_snow = GEFSData.get_cropped_data(init_dt, fxx=12, q_str=":SNOD:", product="atmos.5")
    fig, ax = plotting.surface_plot(ds_snow, "sde", fchr=0, label="SNOD", save=None,
                                        # vlim=(1, None), levels=clvs, plot_type="contourf",
                                        my_extent=[-110.9, -108.3, 41.15, 39.55]
                                        )
    fig.show()

    # Try another with 0.25 degree data
    ds_snow_0p25 = GEFSData.get_cropped_data(init_dt, fxx=12, q_str=":SNOD:", product="atmos.25")
    fig, ax = plotting.surface_plot(ds_snow_0p25, "sde", fchr=0, label="SNOD", save=None,
                                        my_extent=[-110.9, -108.3, 41.15, 39.55]
                                        )
    fig.show()
pass