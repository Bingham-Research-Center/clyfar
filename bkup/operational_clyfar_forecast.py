"""
Operational Forecast Implementation using Clyfar

JRL: IMPORTANT. This script will be deprecated in favour of  parallel-forecast
script and the jupyter notebook for the same name of this script.
Then we will move constants etc into utils etc.

This module implements operational forecasting methodology using the Clyfar framework.
It processes ensemble meteorological data to generate probabilistic ozone forecasts.

Key components:
- Data acquisition and preprocessing for multiple meteorological variables
- Ensemble member processing for uncertainty quantification
- Geographic subsetting and elevation-based filtering
- Representative value computation for initialization
"""

import datetime
import os

import pandas as pd
import pytz
import numpy as np
import matplotlib.pyplot as plt
import xarray as xr

from utils.geog_funcs import elevation_from_latlon, get_elevations_for_resolutions
from utils.lookups import (
    elevations, snow_stids, wind_stids, solar_stids,
    mslp_stids, ozone_stids, Lookup
)
from nwp.gefsdata import GEFSData
import utils.utils as utils
from utils.utils import datetime_of_previous_run
from nwp.download_funcs import load_variable, check_and_create_latlon_files
from obs.download_winters import download_most_recent
from preprocessing.representative_nwp_values import (
    create_forecast_dataframe,
    get_latlon_timeseries_df,
    get_grid_timeseries,
    do_nwpval_snow, do_nwpval_mslp, do_nwpval_wind, do_nwpval_solar,
)
from preprocessing.representative_obs import get_representative_obs
from viz.plotting import plot_meteogram

# Geographic and computational constants
GEOGRAPHIC_CONSTANTS = {
    'extent': [-110.9, -108.2, 41.3, 39.2],
    'ouray': {'lat': 40.0891, 'lon': -109.6774},
    'elevation_threshold': 2000,
}

# Forecast configuration
FORECAST_CONFIG = {
    'delta_h': 3,  # Time step in forecast series
    'solar_delta_h': 3,  # Higher temporal resolution for solar radiation
    'max_h': {"0p25": 240, "0p5": 384},
    'products': {
        'solar': "atmos.25", 'snow': "atmos.25",
        'mslp': "atmos.25", 'wind': "atmos.25"
    },
    'products_backup': {
        'solar': "atmos.5", 'snow': "atmos.5",
        'mslp': "atmos.5", 'wind': "atmos.5"
    }
}

# Variable metadata
VARIABLE_METADATA = {
    'labels': {
        'solar': 'Solar radiation (W/m^2)',
        'snow': 'Snow depth (cm)',
        'mslp': 'Mean sea level pressure (hPa)',
        'wind': 'Wind speed (m/s)',
        'ozone': 'Ozone concentration (ppb)'
    },
    'station_ids': {
        "snow": snow_stids, "wind": wind_stids,
        "solar": solar_stids, "mslp": mslp_stids,
        "ozone": ozone_stids
    },
    'variable_names': {
        'solar': 'solar_radiation',
        'snow': 'snow_depth',
        'wind': 'wind_speed',
        'mslp': 'sea_level_pressure',
        'ozone': 'ozone_concentration'
    }
}

def initialize_geography(latlons):
    """Initialize geographic masks and elevation data."""
    elev_df = {}
    masks = {}

    for res in ['0p25', '0p5']:
        elev_df[res] = get_elevations_for_resolutions(latlons, res, fdir='data')
        masks[res] = elev_df[res] < GEOGRAPHIC_CONSTANTS['elevation_threshold']

    return elev_df, masks

def get_representative_values(variables, lookback_days=7):
    """Compute representative observation values for initialization."""
    repr_vals = {}
    for var in variables:
        val = get_representative_obs(var, lookback_days,
                                     VARIABLE_METADATA['station_ids'][var])
        if var == 'mslp':
            val = val / 100  # Convert to hPa
        # elif var == 'snow': ---?
        repr_vals[var] = val
    return repr_vals

def process_wind_forecast(init_dt, masks, member_names, delta_h=12):
    """Process wind speed forecasts for all ensemble members."""
    dfs_wind = {}
    L = Lookup()

    for member in member_names:
        print(f"Processing wind member {member}")
        wind_ts = do_nwpval_wind(init_dt, masks, delta_h, quantile=0.9,
                                 member=member)
        dfs_wind[member] = create_forecast_dataframe(
            wind_ts,
            L.string_dict['wind']["array_name"]
        )
    return dfs_wind

def process_snow_forecast(init_dt, masks, member_names, delta_h=12):
    """Process snow depth forecasts for all ensemble members.

    Does this return metres or cm? We want cm for plots.
    """
    dfs_snow = {}
    L = Lookup()

    for member in member_names:
        print(f"Processing snow member {member}")
        snow_ts = do_nwpval_snow(init_dt, masks, delta_h, quantile=0.9,
                                 member=member)
        dfs_snow[member] = create_forecast_dataframe(
            snow_ts,
            L.string_dict['snow']["array_name"]
        )
    return dfs_snow

def process_solar_forecast(init_dt, masks, member_names, delta_h=3):
    """Process solar radiation forecasts for all ensemble members."""
    dfs_solar = {}
    L = Lookup()

    for member in member_names:
        print(f"Processing solar member {member}")
        solar_ts = do_nwpval_solar(init_dt, masks, delta_h=delta_h,
                                   quantile=0.9, member=member)
        dfs_solar[member] = create_forecast_dataframe(
            solar_ts,
            L.string_dict['solar']["array_name"],
            init_time=init_dt
        )
    return dfs_solar

def process_mslp_forecast(init_dt, member_names, delta_h=12):
    """Process mean sea level pressure forecasts for all ensemble members."""
    dfs_mslp = {}
    L = Lookup()

    for member in member_names:
        print(f"Processing MSLP member {member}")
        mslp_ts = do_nwpval_mslp(
            init_dt,
            lat=GEOGRAPHIC_CONSTANTS['ouray']['lat'],
            lon=GEOGRAPHIC_CONSTANTS['ouray']['lon'],
            member=member,
            delta_h=delta_h
        )
        dfs_mslp[member] = create_forecast_dataframe(
            mslp_ts,
            L.string_dict['mslp']["array_name"]
        )
    return dfs_mslp

def main():
    """Execute operational forecast workflow."""
    # Initialize ensemble members
    member_names = ['c00'] + [f'p{n:02d}' for n in range(1, 31)]
    member_names = member_names[1:3]  # Subset for testing

    # Root directory for image output
    rootdir = "./figures"
    utils.try_create(rootdir)

    # Initialize geography
    latlons = {
        '0p25': check_and_create_latlon_files("0p25"),
        '0p5': check_and_create_latlon_files("0p5")
    }
    elev_df, masks = initialize_geography(latlons)

    # Get initialization time
    init_dt = utils.get_valid_forecast_init(
        force_init_dt=datetime.datetime(2024, 12, 3, 6, 0, 0)
    )
    utils.print_forecast_init_times(init_dt)

    # Get representative values for initialization
    # TODO sync time 0 for snow depth etc
    repr_vals = get_representative_values(
        ['solar', 'mslp', 'snow', 'wind', 'ozone']
    )

    # Process forecasts
    dfs_wind = process_wind_forecast(init_dt['naive'], masks, member_names)
    dfs_snow = process_snow_forecast(init_dt['naive'], masks, member_names)
    dfs_solar = process_solar_forecast(
        init_dt['naive'], masks, member_names,
        delta_h=FORECAST_CONFIG['solar_delta_h']
    )
    dfs_mslp = process_mslp_forecast(init_dt['naive'], member_names)

    # Generate plots
    for var, dfs in [('wind', dfs_wind), ('snow', dfs_snow),
                     ('solar', dfs_solar), ('mslp', dfs_mslp)]:
        title = (f"{VARIABLE_METADATA['labels'][var]} forecast: "
                 f"GEFS members initialised at "
                 f"{dfs[member_names[0]].index[0].strftime('%Y-%m-%d %H%M')} UTC")
        fig, ax = plot_meteogram(dfs, Lookup().get_key(var, "array_name"),
                       title=title, plot_ensemble_mean=True)
        fig.show()

        # Save the figure
        # Create a filename suitable for variable, GEFS at init time.
        fname = utils.create_meteogram_fname(init_dt['naive'], "ouray", var, "GEFS")
        fig.savefig(fpath := os.path.join(rootdir, fname))
        print("Saved figure to", fpath)


if __name__ == "__main__":
    main()