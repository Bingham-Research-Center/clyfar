import os

import numpy as np
import requests
import urllib.parse
import pandas as pd

from utils.utils import try_create


def elevation_from_latlon(lats, lons):
    """Look up elevation of lat/lon"""
    # From https://gis.stackexchange.com/questions/338392/getting... help discussion
    url = r'https://epqs.nationalmap.gov/v1/json?'
    df = pd.DataFrame({
        'lats': lats,
        'lons': lons,
    })

    elevations = []
    for lat, lon in zip(lats,lons):

        # define rest query params
        params = {
            'output': 'json',
            'x': lon,
            'y': lat,
            'units': 'Meters'
        }

        # format query string and return query value
        result = requests.get((url + urllib.parse.urlencode(params)))
        elevations.append(np.float32(result.json()['value']))

    df['elevation_m'] = elevations
    return df

def get_elevations_for_resolutions(latlons, deg_res, fdir='./data/geog'):
    """
    Compute elevations for given lat/lon pairs and save to specified location.

    Args:
        latlons (dict): Dictionary with latitudes and longitudes arrays.
        deg_res (str): Degree resolution (e.g., '0p25', '0p5').
        fdir (str): Directory to save the elevation files (default is 'data').
    """
    fpath = os.path.join(fdir, f"elev_{deg_res}.parquet")
    if os.path.exists(fpath):
        elev_df = pd.read_parquet(fpath)
    else:
        try_create(fdir)
        lats = latlons[deg_res]['latitudes']
        lons = latlons[deg_res]['longitudes']

        # Flatten the lat/lon arrays
        lats_flat = lats.flatten()
        lons_flat = lons.flatten()

        # Get elevations
        elev_df = elevation_from_latlon(lats_flat, lons_flat)

        # Reshape the elevation data back to the original shape
        elev_df = elev_df['elevation_m'].values.reshape(lats.shape)

        # Save the reshaped elevation data
        pd.DataFrame(elev_df).to_parquet(fpath)

    return elev_df