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

    def generate_and_store():
        try_create(fdir)
        lats = latlons[deg_res]['latitudes']
        lons = latlons[deg_res]['longitudes']

        lats_flat = lats.flatten()
        lons_flat = lons.flatten()
        elev_df = elevation_from_latlon(lats_flat, lons_flat)
        elev_arr = elev_df['elevation_m'].values.reshape(lats.shape)

        elev_store = pd.DataFrame(elev_arr)
        elev_store.columns = elev_store.columns.astype(str)
        elev_store.index = elev_store.index.astype(str)
        elev_store.to_parquet(fpath)
        return elev_arr

    if os.path.exists(fpath):
        try:
            elev_arr = pd.read_parquet(fpath).to_numpy()
        except AttributeError:
            os.remove(fpath)
            elev_arr = generate_and_store()
    else:
        elev_arr = generate_and_store()

    return elev_arr
