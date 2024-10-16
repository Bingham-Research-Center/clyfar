"""General utility functions.
"""

import os
import datetime
import pickle

import pandas as pd
import numpy as np
import pytz

def save_to_pickle(obj, fpath):
    with open(fpath, 'wb') as f:
        pickle.dump(obj, f)

def load_from_pickle(fpath):
    with open(fpath, 'rb') as f:
        obj = pickle.load(f)
    return obj

def get_closest_non_nan(df, column, target_time, tolerance):
    if df[column].isna().all():
        return np.nan

    # Get closest time index
    closest_time = df.index.get_indexer([target_time], method='nearest')[0]

    # Calculate time difference
    time_diff = abs(df.index[closest_time] - target_time)

    # Check if the closest time is within tolerance and non-NaN
    if time_diff <= tolerance and not pd.isna(df.at[df.index[closest_time], column]):
        return df.at[df.index[closest_time], column]

    # Calculate the average time difference between points if freq is not available
    if not hasattr(df.index, 'freq') or df.index.freq is None:
        avg_time_diff = (df.index[1] - df.index[0]).total_seconds()
    else:
        avg_time_diff = df.index.freq.delta.total_seconds()

    # Search for the closest non-NaN value within tolerance
    max_shifts = int(tolerance.total_seconds() // avg_time_diff + 1)
    for i in range(1, max_shifts):
        for time_shift in [-i, i]:
            new_time = df.index[closest_time] + pd.Timedelta(seconds=time_shift * avg_time_diff)
            if new_time in df.index:
                if abs(new_time - target_time) <= tolerance and not pd.isna(df.at[new_time, column]):
                    return df.at[new_time, column]

    return np.nan  # Return np.nan if no value found within tolerance

def herbie_from_datetime(dt:datetime.datetime):
    """Convert datetime to herbie timestamp
    (Might be same as pandas and this is redundant?)
    """
    hbts = dt.strftime(f"%Y-%m-%d %H:%M")
    return hbts

def pd_from_datetime(dt:datetime.datetime):
    """Convert datetime to pandas timestamp
    """
    pdts = pd.Timestamp(dt)#, tz="UTC")
    return pdts

def create_image_fname(dt, inittime, plot_type, model,
                        subtitle=None):
    date_str = dt.strftime("%Y%m%d-%H%M")

    if model == "obs":
        init_str = ""
    else:
        init_str = inittime.strftime("%Y%m%d-%H%M") + "_"

    fname = f"{init_str}{date_str}_{plot_type}_{model}.png"
    return fname

def create_meteogram_fname(inittime, loc, vrbl, model):
    init_str = inittime.strftime("%Y%m%d-%H%M")
    fname = f"meteogram_{loc}_{vrbl}_{init_str}_{model}.png"
    return fname

def try_create(fpath):
    if not os.path.exists(fpath):
        os.mkdir(fpath)
        print("Creating directory", fpath)
    return

def create_nwp_title(description, model, init_time, valid_time):
    forecast_hour = int((valid_time - init_time).total_seconds() / 3600)
    title = (f"{description}\nModel: {model}, Init: {init_time.strftime('%Y-%m-%d %H:%M')}, "
                f"Valid: {valid_time.strftime('%Y-%m-%d %H:%M')} (T+{forecast_hour}h)")
    return title

def create_obs_title(description, valid_time,subtitle):
    if subtitle is None:
        subtitle = ""
    else:
        subtitle = f"\n{subtitle}"
    title = f"{description}\nObserved data, valid: {valid_time.strftime('%Y-%m-%d %H:%M')}{subtitle}"
    return title

def create_meteogram_title(description, init_time, model, location):
    title = f"{description}\n{location}, initialised from {model}: {init_time.strftime('%Y-%m-%d %H:%M')}"
    return title

def reverse_lookup(dictionary, target_value):
    for key, value in dictionary.items():
        if value == target_value:
            return key
    return None  # or raise an exception if you prefer

def convert_to_naive_utc(dt):
    """Convert an offset-aware datetime to offset-naive in UTC.
    """
    # Convert to UTC and remove tzinfo
    return dt.astimezone(pytz.utc).replace(tzinfo=None)

def select_nearest_neighbours(source_df, target_df, max_diff='30min'):
    # Might be duplicate of nearest_non_nan above

    # target_df.index is a DatetimeIndex
    target_datetimes = target_df.index

    # Initialize a list to store the nearest neighbours
    nearest_indices = []

    for target in target_datetimes:
        # Wrap the target in a list and find the index of the nearest neighbour in source_df
        nearest_idx_array = source_df.index.get_indexer([target], method='nearest')
        nearest_idx = nearest_idx_array[0]  # Get the first (and only) element
        nearest_datetime = source_df.index[nearest_idx]

        # Check the time difference
        time_diff = abs(nearest_datetime - target)
        if time_diff > pd.Timedelta(max_diff):
            raise ValueError(f"Time difference exceeded: {time_diff} between {nearest_datetime} and {target}")

        nearest_indices.append(nearest_idx)

    # Select the corresponding rows from the source DataFrame
    selected_rows = source_df.iloc[nearest_indices]
    return selected_rows

def find_common_stids(vrbl_stids, years, num_years):
    """
    Find the station IDs that have reported for the last `num_years` consistently.

    TODO: make more general than just stid (e.g., for any column)

    Args:
        vrbl_stids (dict): Dictionary of station IDs per year.
        years (list): List of years.
        num_years (int): Number of years to check for consistency.

    Returns:
        set: Set of common station IDs.
    """
    stids = [set(vrbl_stids[year]) for year in years[-num_years:]]
    return set.intersection(*stids)