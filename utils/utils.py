"""General utility functions.
"""

import os
import datetime
import pickle
import time
import functools

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

def create_meteogram_fname(inittime, loc, vrbl, model, actually_heatmap=False):
    init_str = inittime.strftime("%Y%m%d-%H%M")
    plot_str = "heatmap" if actually_heatmap else "meteogram"
    fname = f"{plot_str}_{loc}_{vrbl}_{init_str}_{model}.png"
    return fname

def try_create(fpath):
    try:
        if not os.path.exists(fpath):
            os.makedirs(fpath, exist_ok=True)
            print("Creating directory", fpath)
    except OSError as e:
        print(f"Error creating directory {fpath}: {e}")
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

def datetime_of_previous_run(dt, do_utc=True, do_naive=True, do_local=True,
                                hours=6):
    # Going to assume we want all three variants of the datetime, haha
    new_dt_utc = dt - datetime.timedelta(hours=hours)
    init_dt_naive = new_dt_utc.replace(tzinfo=None)
    local_t0 = new_dt_utc.astimezone(pytz.timezone('US/Mountain'))
    return new_dt_utc, init_dt_naive, local_t0

def get_nice_tick_spacing(data_range, quantizations):
    """Calculate a nice tick spacing for a given data range.

    Example:

        ```python
        inch_spacing = get_nice_tick_spacing(inch_range, quantizations)
        # Calculate tick positions in inches
        inch_min = np.floor(y_min * conversion_factor / inch_spacing) * inch_spacing
        inch_max = np.ceil(y_max * conversion_factor / inch_spacing) * inch_spacing
        inch_ticks = np.arange(inch_min, inch_max + inch_spacing/2, inch_spacing)
        # Set the ticks on the secondary axis
        ax2.set_yticks(inch_ticks)
        ```

    Args:
        data_range (float): Range of data to be covered
        quantizations (list): List of allowed tick spacings

    Returns:
        float: Selected tick spacing
    """
    target_num_ticks = 5

    # Convert quantizations to sorted list
    spacings = sorted(quantizations)

    # Find the spacing that gives closest to target number of ticks
    best_spacing = spacings[0]
    best_diff = float('inf')

    for spacing in spacings:
        num_ticks = data_range / spacing
        diff = abs(num_ticks - target_num_ticks)
        if diff < best_diff:
            best_diff = diff
            best_spacing = spacing

    return best_spacing

def get_valid_forecast_init(current_dt=None, required_delay_hours=8,
                            force_init_dt=None):
    """Determines valid forecast initialization time accounting for data availability."""

    if force_init_dt:
        init_times = {
            # 'utc': force_init_dt.astimezone(pytz.utc),
            'utc': force_init_dt.replace(tzinfo=pytz.timezone('UTC')),
            'naive': force_init_dt.replace(tzinfo=None),
            'local': force_init_dt.astimezone(pytz.timezone('US/Mountain')),
            'skipped': []
        }
        return init_times

    # Use current UTC time if not specified to override it
    current_dt = current_dt or datetime.datetime.now(tz=pytz.utc)

    # Find most recent 6-hourly initialization time
    init_dt = current_dt.replace(
        hour=current_dt.hour - (current_dt.hour % 6),
        minute=0, second=0, microsecond=0
    ).replace(tzinfo=pytz.utc)

    # Calculate hours needed to wait for data availability
    hours_since_init = (current_dt - init_dt).total_seconds() / 3600
    periods_to_backtrack = max(1, int(np.ceil((required_delay_hours - hours_since_init) / 6)))

    # Store initialization history
    init_times = {
        'utc': init_dt - datetime.timedelta(hours=6 * periods_to_backtrack),
        'skipped': [init_dt - datetime.timedelta(hours=6 * i) for i in range(periods_to_backtrack)]
    }

    # Add timezone variants
    init_times['naive'] = init_times['utc'].replace(tzinfo=None)
    init_times['local'] = init_times['utc'].astimezone(pytz.timezone('US/Mountain'))

    return init_times

def print_forecast_init_times(init_times):
    """Prints the forecast initialization times with informative messages.

    Args:
        init_times (dict): Dictionary containing initialization times.
    """
    print("Current datetime in UTC:", datetime.datetime.now(tz=pytz.utc))
    for key, value in init_times.items():
        if key == 'utc':
            print(f"Forecast initialization time (UTC): {value}")
        elif key == 'naive':
            print(f"Forecast initialization time (naive, no timezone): {value}")
        elif key == 'local':
            print(f"Forecast initialization time (local, US/Mountain): {value}")
        elif key == 'skipped':
            print("Skipped initialization times (most recent runs):")
            for skipped_time in value:
                print(f"  - {skipped_time}")


def print_system_info():
    """Prints system information about available resources.

    Most useful for deciding how to optimize parallel processing.
    """
    import multiprocessing
    import psutil

    print("Number of CPUs:", multiprocessing.cpu_count())
    print("Number of GPUs:", len(os.environ.get('CUDA_VISIBLE_DEVICES', '').split(',')))
    print("Memory available:", psutil.virtual_memory().total / 1e9, "GB")
    print("Number of threads:", psutil.cpu_count(logical=False))
    # All add a line about system storage memory, in GB.
    # TODO - make this also tell us storage on a supercomputer/archive
    print("System storage memory:", psutil.disk_usage('/').total / 1e9, "GB")
    return

def configurable_timer(threshold_ms: float = None, log_file: str = None):
    """
    Configurable timer decorator with threshold alerts and logging capabilities.

    Example:
        @configurable_timer(threshold_ms=200, log_file="performance_log.txt")
        def func(...):

    Args:
        threshold_ms (float, optional): Alert threshold in milliseconds
        log_file (str, optional): Path to timing log file
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            result = func(*args, **kwargs)
            execution_time = (time.perf_counter() - start_time) * 1000

            if threshold_ms and execution_time > threshold_ms:
                print(f"Warning: {func.__name__} exceeded threshold "
                      f"({execution_time:.2f} ms > {threshold_ms} ms)")

            if log_file:
                with open(log_file, 'a') as f:
                    f.write(f"{func.__name__},{execution_time:.2f}\n")

            return result
        return wrapper
    return decorator

def json_from_poss_df(df):
    """Export possibility dataframes into json format for website.
    """
    return

def json_from_obs_df(df):
    """Export observation dataframes into json format for website.
    """
    return