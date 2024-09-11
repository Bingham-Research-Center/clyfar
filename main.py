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

if test_gefs_meteogram:
    lon, lat = (360 - 109.6774, 40.0891)

    init_dt = datetime.datetime(2023,12,5,18,0,0)
    ts = GEFSData.generate_timeseries(list(range(0,240,12)), init_dt, ":SNOD:", "sde", lat, lon,
                                        product="atmos.25",member='mean')
    fig, ax = plotting.plot_meteogram(ts, "sde", title=None, save=None,second_df=None, second_col=None)
    fig.show()

pass