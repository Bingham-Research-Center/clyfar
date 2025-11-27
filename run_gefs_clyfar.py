"""
Comprehensive Parallel Processing Implementation for Ensemble Weather Forecasts

This module implements a parallel processing framework for meteorological ensemble forecasts,
incorporating multiple atmospheric variables with specific processing methodologies for each.
The implementation optimizes computational efficiency while maintaining data integrity and
theoretical consistency in the treatment of ensemble members.

Key methodological considerations:
- Systematic parallel processing of ensemble members
- Variable-specific processing protocols
- Synchronized I/O operations
- Memory-efficient data structure management
- Inter-process communication architecture

JRL: Disclosure. This is one script that Claude 3.5 LLM did heavy-lifting for.
TODO - "temp" to become numerous further variables in branch testing v1.1+
"""
import argparse
import multiprocessing as mp

from scipy import ndimage

# mp.set_start_method('spawn', force=True)
print("Current start method:", mp.get_start_method())
import os
from typing import Dict, List, Tuple, Optional
import logging
import datetime
import platform
import sys

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt

from nwp.download_funcs import check_and_create_latlon_files
from fis.v0p9 import (
    VARIABLE_METADATA, FORECAST_CONFIG,
    GEOGRAPHIC_CONSTANTS,
)
from preprocessing.representative_nwp_values import (
    do_nwpval_wind, create_forecast_dataframe, do_nwpval_solar,
    do_nwpval_snow, do_nwpval_mslp, do_nwpval_temp,
)
from utils import utils
from utils.geog_funcs import get_elevations_for_resolutions
from utils.lookups import Lookup
from utils.utils import configurable_timer
from utils.runlog import write_run_summary
from viz.plotting import plot_meteogram
from fis.v0p9 import Clyfar
from viz.possibility_funcs import (plot_percentile_meteogram,
                                   plot_possibility_bar_timeseries,
                                   plot_ozone_heatmap, plot_dailymax_heatmap)

######### SETTINGS ##########
# Uintah Basin (Vernal, UT) local timezone
LOCAL_TIMEZONE = "America/Denver"

# At the top of the file, enforce spawn context
if mp.get_start_method() != 'spawn':
    try:
        mp.set_start_method('spawn', force=True)
    except RuntimeError:
        print("Warning: Could not set spawn context. Already initialized.")

L = Lookup()
clyfar = Clyfar()

DEFAULT_GEFS_MEMBER_COUNT = 30

# TODO - DYNAMIC PATHS
# clyfar_data_root = './data/clyfar_output'
# utils.try_create(clyfar_data_root)
# clyfar_fig_root = './figures/clyfar_output'
# utils.try_create(clyfar_fig_root)

# Configure logging with precise timestamp and process identification
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s.%(msecs)03d - %(processName)s - %(message)s',
                   datefmt='%Y-%m-%d %H:%M:%S')

logger = logging.getLogger(__name__)

######### FUNCS ##########
def initialize_geography(latlons, use_raw_elevations=False):
    """Initialize geographic masks and elevation data."""
    elev_df = {}
    masks = {}

    # Split between low & high elevation is "elevation_threshold"
    # Use a 2-D filter to take a weighted average of the neighbouring cells
    for res in ['0p25', '0p5']:
        elev_df[res] = get_elevations_for_resolutions(latlons, res, fdir='data')
        if use_raw_elevations:
            masks[res] = elev_df[res] < GEOGRAPHIC_CONSTANTS['elevation_threshold']
        else:
            mask_temp = elev_df[res] < (
                GEOGRAPHIC_CONSTANTS['elevation_threshold'] + 250
            )
            # For the v0.9.5 freeze, keep the buffered mask without smoothing so
            # behaviour matches the historical runs; we'll revisit post-freeze.
            masks[res] = mask_temp

    return elev_df, masks

def weighted_average(elevation, mask):
    """
    Compute the weighted average of each cell with its neighbors.

    Parameters:
    - elevation: 2D NumPy array of elevation values.
    - mask: 2D NumPy boolean array where True indicates a low terrain cell.

    Returns:
    - 2D NumPy array of weighted averages.
    """
    # Define the convolution kernel for 8-connected neighbors
    kernel = np.array([[1, 1, 1],
                       [1, 0, 1],
                       [1, 1, 1]])

    # Compute the number of valid neighbors for each cell
    neighbor_counts = ndimage.convolve(mask.astype(float), kernel,
                                       mode='constant', cval=0.0)

    # Avoid division by zero; set to 1 where neighbour_counts is 0 to prevent NaNs
    # JRL - is this needed?
    safe_neighbor_counts = np.where(neighbor_counts == 0, 1, neighbor_counts)

    # Compute the sum of neighbor elevation values
    # First, mask the elevation to consider only valid neighbors

    masked_elevation = np.where(mask, elevation, 0)
    sum_neighbors = ndimage.convolve(masked_elevation, kernel, mode='constant', cval=0.0)

    # Compute the average of the surrounding cells
    # with np.errstate(invalid='ignore'):
    avg_neighbors = np.divide(sum_neighbors, safe_neighbor_counts)


    # Compute the final weighted average
    weighted_avg = (2 * elevation + avg_neighbors) / 3

    # Handle cells with no valid neighbors: retain the original elevation
    weighted_avg = np.where(neighbor_counts == 0, elevation, weighted_avg)

    return weighted_avg


def get_optimal_process_count(ncpus=None) -> int:
    """
    Determine optimal process count based on system resources.

    Args:
        ncpus: Number of CPUs to use. If None, use all available CPUs minus 1.

    Returns:
        int: Optimal number of processes
    """
    if ncpus is None:
        ncpus = max(1, mp.cpu_count() - 1)
    else:
        # Ensure we don't exceed available CPUs
        ncpus = min(ncpus, mp.cpu_count())
    return ncpus

def process_member_variable(args):
    member, variable, processor_map = args
    return variable, member, processor_map[variable](member)[1]

class ParallelEnsembleProcessor:
    """
    Manages parallel processing of ensemble forecasts with synchronized I/O operations.
    Implements specific processing methodologies for each meteorological variable.
    """

    def __init__(self, init_dt: datetime.datetime, masks: Dict,
                 process_count: int = None, testing=False):
        """
        Initialize parallel processing environment with specified parameters.

        Args:
        init_dt: Initialization datetime for the forecast
            masks: Geographic masks for data filtering
            process_count: Number of parallel processes (defaults to optimal count)
        """
        self.testing = testing
        self.init_dt = init_dt
        self.masks = masks
        self.process_count = (process_count if process_count is not None
                            else get_optimal_process_count())
        self.logger = logging.getLogger(__name__)
        self.lookup = Lookup()
        self.processor_map = self.get_processor_maps()

    def _process_ensemble_member_wind(self, member: str) -> Tuple[str, pd.DataFrame]:
        """Process wind forecasts with quantile-based methodology."""
        self.logger.info(f"Processing wind forecast for member {member}")

        dh = 6 if self.testing else FORECAST_CONFIG['delta_h']
        wind_ts = do_nwpval_wind(
                    init_dt_naive=self.init_dt,
                    start_h = 0,
                    max_h = FORECAST_CONFIG['max_h']['0p5'],
                    masks = self.masks,
                    delta_h = dh,
                    member = member,
            )
        df = create_forecast_dataframe(
            wind_ts,
            self.lookup.string_dict['wind']["array_name"]
        )
        return member, df

    def _process_ensemble_member_temp(self,
                            member: str) -> Tuple[str, pd.DataFrame]:
        self.logger.info(f"Processing temp forecast for member {member}")

        dh = 6 if self.testing else FORECAST_CONFIG['delta_h']
        temp_ts = do_nwpval_temp(
            init_dt_naive=self.init_dt,
            start_h = 0,
            max_h = FORECAST_CONFIG['max_h']['0p5'],
            masks = self.masks,
            delta_h = dh,
            member = member,
        )
        df = create_forecast_dataframe(
            temp_ts,
            self.lookup.string_dict['temp']["array_name"]
        )
        return member, df

    def _process_ensemble_member_solar(self, member: str) -> Tuple[str, pd.DataFrame]:
        """Process solar radiation with high temporal resolution requirements."""
        self.logger.info(f"Processing solar forecast for member {member}")

        solar_dh = 6 if self.testing else FORECAST_CONFIG['solar_delta_h']
        solar_ts = do_nwpval_solar(
            init_dt_naive=self.init_dt,
            start_h= 0 + solar_dh,
            max_h = FORECAST_CONFIG['max_h']['0p5'],
            masks = self.masks,
            delta_h= solar_dh,
            member = member,
        )
        df = create_forecast_dataframe(
            solar_ts,
            self.lookup.string_dict['solar']["array_name"],
            init_time=self.init_dt
        )
        return member, df

    def _process_ensemble_member_snow(self, member: str) -> Tuple[str, pd.DataFrame]:
        """Process snow depth with elevation-based filtering."""
        self.logger.info(f"Processing snow forecast for member {member}")

        dh = 6 if self.testing else FORECAST_CONFIG['delta_h']
        snow_ts = do_nwpval_snow(
                    init_dt_naive=self.init_dt,
                    start_h = 0,
                    max_h = FORECAST_CONFIG['max_h']['0p5'],
                    masks = self.masks,
                    delta_h = dh,
                    member = member,
                    do_early = True,
                    do_late = True,
            # self.init_dt, 0, FORECAST_CONFIG['max_h']['0p25'], self.masks,
            # FORECAST_CONFIG['delta_h'],
            # quantile=0.9, member=member
        )
        df = create_forecast_dataframe(
            snow_ts,
            self.lookup.string_dict['snow']["array_name"]
        )
        return member, df

    def _process_ensemble_member_mslp(self, member: str) -> Tuple[str, pd.DataFrame]:
        """Process mean sea level pressure with geographic point-based methodology."""
        self.logger.info(f"Processing MSLP forecast for member {member}")

        dh = 6 if self.testing else FORECAST_CONFIG['delta_h']
        mslp_ts = do_nwpval_mslp(
            init_dt_naive=self.init_dt,
            lat=GEOGRAPHIC_CONSTANTS['ouray']['lat'],
            lon=GEOGRAPHIC_CONSTANTS['ouray']['lon'],
            member=member,
            delta_h= dh,
        )
        df = create_forecast_dataframe(
            mslp_ts,
            self.lookup.string_dict['mslp']["array_name"]
        )
        return member, df

    def get_processor_maps(self) -> Dict[str, callable]:
        processor_map = {
            'wind': self._process_ensemble_member_wind,
            'solar': self._process_ensemble_member_solar,
            'snow': self._process_ensemble_member_snow,
            'mslp': self._process_ensemble_member_mslp,
            'temp': self._process_ensemble_member_temp,
        }
        return processor_map

    def process_variable_member_parallel(self, member_names: List[str], variables: List[str]) -> Dict[str, Dict[str, pd.DataFrame]]:
        """
        Execute parallel processing for specified meteorological variables and ensemble members.

        Args:
        member_names: List of ensemble member identifiers
        variables: List of target meteorological variables

        Returns:
        Nested dictionary mapping variables and member identifiers to processed DataFrames
        """
        processor_map = self.processor_map

        with mp.get_context('spawn').Pool(processes=self.process_count) as pool:
            results = pool.map(
                process_member_variable,
                [(member, variable, processor_map) for member in member_names for variable in variables],
            )

        nested_results = {}
        for variable, member, df in results:
            if variable not in nested_results:
                nested_results[variable] = {}
            nested_results[variable][member] = df

        return nested_results

#### END OF CLASS ####

@configurable_timer(log_file="performance_log.txt")
def parallel_forecast_workflow(init_dt: datetime.datetime, masks: Dict, member_names: List[str], variables: List[str], ncpus: int = None, testing: bool = False, serial: bool = False) -> Dict[str, Dict[str, pd.DataFrame]]:
    """
    Execute comprehensive parallel forecast workflow for all variables and members.

    Args:
    init_dt: Forecast initialization datetime
    masks: Geographic masks for data filtering
    member_names: List of ensemble member identifiers
    variables: List of target meteorological variables

    Returns:
    Nested dictionary of processed forecasts by variable and member
    """
    processor = ParallelEnsembleProcessor(init_dt, masks, process_count=ncpus, testing=testing)
    if serial:
        out: Dict[str, Dict[str, pd.DataFrame]] = {var: {} for var in variables}
        for member in member_names:
            for variable in variables:
                _, df = processor.processor_map[variable](member)
                out[variable][member] = df
        return out
    results = processor.process_variable_member_parallel(member_names, variables)
    return results

# Root directory for image output
def make_dated_rootdir(rootdir: str, init_dt_dict: dict):
    # add the timestamp in a YYYYMMDD_HHZ format for the folder
    return os.path.join(
                    rootdir, init_dt_dict['naive'].strftime('%Y%m%d_%HZ'))

def create_forecast_fname(variable: str, member: str,
                            init_dt_dict: datetime.datetime) -> str:
    """Create the file path for saving forecast data."""
    dataroot = "./data"
    utils.try_create(dataroot)
    timestr = init_dt_dict.strftime('%Y%m%d_%H%MZ')
    fpath = os.path.join(dataroot, timestr, f"{timestr}_{variable}_{member}_df.parquet")
    return fpath

def save_forecast_data(dfs: Dict[str, pd.DataFrame], variable: str, init_dt_dict: dict):
    """Save forecast data to disk."""
    lookup = Lookup()
    mslp_col = lookup.string_dict['mslp']["array_name"]
    for member, df in dfs.items():
        fpath = create_forecast_fname(variable, member, init_dt_dict['naive'])
        utils.try_create(os.path.dirname(fpath))
        if variable == "mslp":
            series = df[mslp_col]
            if series.isna().all():
                # TODO: Fix in Herbie refactor (see TODO-HERBIE-REFACTOR.md)
                logger.warning(
                    "MSLP dataframe for %s contains only NaNs; writing anyway. "
                    "Forecast will use fallback MSLP values.", member
                )
            else:
                logger.info(
                    "MSLP stats for %s: min=%.1f hPa median=%.1f hPa p90=%.1f hPa",
                    member,
                    float(series.min()),
                    float(series.median()),
                    float(series.quantile(0.9)),
                )
        df.to_parquet(fpath)
    return

def load_forecast_data(variable: str, init_dt: datetime.datetime, member_names: list):
    """Load forecast data from disk."""
    dfs = {}
    for member in member_names:
        fpath = create_forecast_fname(variable, member, init_dt)
        dfs[member] = pd.read_parquet(fpath)
    return dfs

def visualize_results(results: Dict[str, Dict[str, pd.DataFrame]],
                      clyfar_fig_root, init_dt_dict: dict):
    """
    Generate visualization suite for processed forecast results.

    TODO: maybe, ultimately move more of this to the plotting modules?

    Args:
        results: Nested dictionary of processed forecasts
    """
    for variable, dfs in results.items():
        title = (f"{VARIABLE_METADATA['labels'][variable]} forecast: "
                f"GEFS members initialised at "
                f"{init_dt_dict['naive'].strftime('%Y-%m-%d %H%M')} UTC ("
                f"using {len(dfs.keys())} members)"
                )
        fig, ax = plot_meteogram(
            dfs,
            Lookup().get_key(variable, "array_name"),
            title=title,
            plot_ensemble_mean=True,
        )

        fig.show()

        # Save the figure
        # Create a filename suitable for variable, GEFS at init time.
        fname = utils.create_meteogram_fname(init_dt_dict['naive'],
                                    "UB-repr", variable, "GEFS")

        dated_rootdir = make_dated_rootdir(clyfar_fig_root, init_dt_dict)
        utils.try_create(dated_rootdir)

        fig.savefig(fpath := os.path.join(dated_rootdir, fname))
        print("Saved figure to", fpath)
        plt.close(fig)
    return

#################################################
############## CLYFAR FUNCS #####################

# TODO - redo the data loading to be more intelligent than this
def reorganise_data(forecast_data: dict):
    """Reorganise forecast data into a dictionary of dataframes.

    Args:
        forecast_data (dict): Dictionary of forecast data. The format
            is forecast_data['variable']['member']['array_name'] like
            forecast_data['snow']['p01']['sde'].

    Returns:
        dict: Dictionary of dataframes. The format is
            data_dict['member']['variable'] which gives a dataframe
            of the data for that member and variable.
    """
    data_dict = {}
    for variable, member_data in forecast_data.items():
        for member, df in member_data.items():
            for array_name, series in df.items():
                if member not in data_dict:
                    data_dict[member] = {}
                if variable not in data_dict[member]:
                    data_dict[member][variable] = pd.DataFrame(index=series.index)
                data_dict[member][variable][array_name] = series
    return data_dict

############## CLYFAR FUNCS #####################

def gefs_to_clyfar_membername(gefs_member: str) -> str:
    """Convert GEFS member name to Clyfar member name.

    c00 -> clyfar000 (control)
    p01 -> clyfar001
    p30 -> clyfar030
    """
    if gefs_member == 'c00':
        return 'clyfar000'
    elif gefs_member.startswith('p'):
        return f'clyfar{int(gefs_member[1:]):03d}'
    elif isinstance(gefs_member, int):
        return f'clyfar{gefs_member:03d}'
    else:
        raise ValueError(f"Unknown GEFS member format: {gefs_member}")

def run_singlemember_inference(init_dt: datetime.datetime, member, percentiles,
                               forecast_cache: Optional[Dict[str, Dict[str, pd.DataFrame]]]=None,
                               diagnostics: Optional[List[Dict]] = None):
    """Run Clyfar driven by a single member of GEFS.

    init_dt should be naive.
    """
    # Clyfar member name
    clyfar_member = gefs_to_clyfar_membername(member)

    # Some shortcuts
    snow_ = L.string_dict['snow']['array_name']
    mslp_ = L.string_dict['mslp']['array_name']
    wind_ = L.string_dict['wind']['array_name']
    solar_ = L.string_dict['solar']['array_name']
    temp_ = L.string_dict['temp']['array_name']

    all_vrbl_dfs = {}
    all_vrbls = ['snow', 'mslp', 'solar', 'wind', 'temp']
    for variable in all_vrbls:
        # Prefer freshly processed data when available to avoid disk I/O
        if forecast_cache and variable in forecast_cache:
            member_df = forecast_cache[variable].get(member)
            if member_df is not None:
                all_vrbl_dfs[variable] = member_df.copy()
                continue

        all_vrbl_dfs[variable] = load_forecast_data(
            variable, init_dt, member_names=[member,])[member]

    # data_dict = reorganise_data(all_vrbl_dfs)

    # Get the datetime of all rows possible (solar not on first)
    indices = all_vrbl_dfs['snow'].index.copy()
    output_df = pd.DataFrame(index=indices)

    poss_records: List[Dict[str, float]] = []

    for nt, dt in enumerate(indices):
        if nt == 0:
            print("Solar radiation is unavailable for first time.")
            for pct in percentiles:
                output_df.loc[dt, f'ozone_{pct}pc'] = np.nan
            continue

        snow_val = all_vrbl_dfs["snow"][snow_].loc[dt]  # mm
        # MSLP may have coarser time resolution - use nearest available value
        mslp_series = all_vrbl_dfs["mslp"][mslp_]
        mslp_val = mslp_series.iloc[mslp_series.index.get_indexer([dt], method='nearest')[0]]  # hPa
        wind_val = all_vrbl_dfs["wind"][wind_].loc[dt] # already in m/s?
        solar_val = all_vrbl_dfs["solar"][solar_].loc[dt] # already w/m2 TODO Crap after 240h
        temp_val = all_vrbl_dfs["temp"][temp_].loc[dt] # already in C

        # UOD guard: warn/clip when inputs fall outside FIS domains
        val_map = {
            'snow': snow_val,
            'mslp': mslp_val,
            'wind': wind_val,
            'solar': solar_val,
        }
        clipped_flags = {}
        for v, val in val_map.items():
            u = clyfar.universes.get(v)
            if u is None:
                continue
            umin, umax = float(u.min()), float(u.max())
            if not np.isfinite(val):
                continue
            if val < umin or val > umax:
                logger.warning(f"UOD clip: {v}={val:.3f} outside [{umin:.3f},{umax:.3f}] at {dt}")
                val = float(np.clip(val, umin, umax))
                clipped_flags[v] = True
            else:
                clipped_flags[v] = False
            val_map[v] = val

        snow_val = val_map['snow']
        mslp_val = val_map['mslp']
        wind_val = val_map['wind']
        solar_val = val_map['solar']

        # Use the variables in the function call
        pc_dict, poss_df = clyfar.compute_ozone(
            # Don't need temp, that's for visualising only
            snow_val, mslp_val, wind_val, solar_val,
            percentiles=percentiles)

        for pct in percentiles:
            output_df.loc[dt, f'ozone_{pct}pc'] = pc_dict[pct]

        for cat in poss_df.index:
            output_df.loc[dt, cat] = poss_df.loc[cat].values

        poss_records.append(poss_df['possibility'].to_dict())

        # Also include the values above ending in _val
        output_df.loc[dt, 'snow'] = snow_val
        output_df.loc[dt, 'mslp'] = mslp_val
        output_df.loc[dt, 'wind'] = wind_val
        output_df.loc[dt, 'solar'] = solar_val
        output_df.loc[dt, 'temp'] = temp_val
        for v, was_clipped in clipped_flags.items():
            output_df.loc[dt, f'{v}_clipped'] = was_clipped
        pass
    # Do we have columns for possibility, etc?
    # Whatever is needed for plotting data

    pass
    print("Clyfar inference complete for member",
                clyfar_member, "driven by GEFS member ", member)

    if diagnostics is not None:
        diag_entry: Dict[str, float] = {'member': clyfar_member}
        input_cols = ['snow', 'mslp', 'wind', 'solar', 'temp']
        for col in input_cols:
            series = output_df[col].dropna()
            if series.empty:
                continue
            diag_entry[f'{col}_p10'] = float(series.quantile(0.1))
            diag_entry[f'{col}_p50'] = float(series.quantile(0.5))
            diag_entry[f'{col}_p90'] = float(series.quantile(0.9))

        poss_matrix = pd.DataFrame(poss_records)
        if not poss_matrix.empty:
            for cat in poss_matrix.columns:
                diag_entry[f'poss_mean_{cat}'] = float(poss_matrix[cat].mean())
                diag_entry[f'poss_active_{cat}'] = float((poss_matrix[cat] > 0).mean())

        diagnostics.append(diag_entry)

    return output_df



############## CLYFAR FUNCS #####################
#################################################

def main(dt, clyfar_fig_root, clyfar_data_root,
         maxhr='all', ncpus='auto', nmembers=None, visualise=True,
         save=True, verbose=False, testing=False, no_clyfar=False,
         no_gefs=False, log_fis=False):
    """Execute parallel operational forecast workflow.

    Note:
        * The testing parameter takes precedence if True over ncpus and nmembers.

    Args:
        dt (datetime.datetime): Initialization datetime for the forecast.
        maxhr (int): Maximum hours to run the models. 'all' for all.
            Currently not implemented, using all hours.
        ncpus (int): Number of CPUs to use. If 'auto', match nmembers.
        nmembers (int): Number of ensemble members to use. "all" for all.
        visualise (bool): Whether to generate visualizations. Default is True.
        save (bool): Whether to save the results. Default is True.
        verbose (bool): Whether to enable verbose logging. Default is False.
        testing (bool): Whether to enable testing mode. Default is False.
        do_clyfar (bool): Whether to run Clyfar. Default is True.
        do_gefs (bool): Whether to download GEFS data. Default is False.
    """
    # Find most recent run time - would have to wait for runs to come through
    # run = pd.Timestamp("now", tz="utc").floor('1h').replace(tzinfo=None)
    # Can also wait, maybe for 20 min intervals.
    # H = HerbieWait(run=run, model="rap", product="awp130pgrb",
    #                 wait_for="10s", check_interval="1s", fxx=0)

    percentiles = [10, 50, 90]

    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    utils.print_system_info()

    member_count = (DEFAULT_GEFS_MEMBER_COUNT if nmembers in (None, 'all')
                    else int(nmembers))
    if member_count < 1:
        raise ValueError("nmembers must be at least 1")
    if member_count > 31:
        raise ValueError("GEFS has max 31 members (c00 + p01-p30)")

    # GEFS members: c00 (control) + p01-p30 (perturbations)
    if member_count == 31:
        member_names = ['c00'] + [f'p{n:02d}' for n in range(1, 31)]
    else:
        # For smaller runs, use perturbation members only
        member_names = [f'p{n:02d}' for n in range(1, member_count + 1)]
    print(f"Using {len(member_names)} members: {member_names}")

    if testing:
        member_names = member_names[:10]
        member_count = len(member_names)
        ncpus = 10
    else:
        if ncpus in (None, 'auto'):
            ncpus = member_count * 5  # Adjust for both members and variables
        else:
            ncpus = int(ncpus)

    latlons = {
        '0p25': check_and_create_latlon_files("0p25"),
        '0p5': check_and_create_latlon_files("0p5")
    }
    try:
        from nwp.gefsdata import GEFSData
        GEFSData.LATLONS = latlons
    except ImportError:
        pass
    elev_df, masks = initialize_geography(latlons)

    init_dt_dict = utils.get_valid_forecast_init(force_init_dt=dt)

    variables = ['wind', 'solar', 'snow', 'mslp', 'temp']

    results = None

    if not no_gefs:
        print("Downloading GEFS data for", init_dt_dict['naive'])
        workflow_fn = (parallel_forecast_workflow
                        if verbose else parallel_forecast_workflow.__wrapped__)
        results = workflow_fn(
            init_dt_dict['naive'], masks, member_names, variables, ncpus=ncpus,
            testing=testing, serial=args.serial_debug)

        print(f"{init_dt_dict['naive']=}, {masks=}, {member_names=}, "
              f"{ncpus=}, {testing=}")

        if save:
            print("Saving GEFS data for", init_dt_dict['naive'])
            for variable, dfs in results.items():
                save_forecast_data(dfs, variable, init_dt_dict)

        if visualise:
            print("Visualizing GEFS data for", init_dt_dict['naive'])
            # Generate visualization suite
            visualize_results(results, clyfar_fig_root, init_dt_dict)

    # Run Clyfar here - GEFS time series already exists if everything went well
    # Go member by member to compute Clyfar
    fis_diagnostics: Optional[List[Dict]] = [] if log_fis else None

    if not no_clyfar:
        print("Running Clyfar for", init_dt_dict['naive'])

        ############################
        # TODO Create daily values
        ############################

        clyfar_df_dict = {}
        dailymax_df_dict = {}
        for nm, member in enumerate(member_names):
            clyfar_member = gefs_to_clyfar_membername(member)
            # TODO - no dicts; just save members in a folder for the run?
            member_df = run_singlemember_inference(
                init_dt_dict['naive'], member,
                percentiles, forecast_cache=results,
                diagnostics=fis_diagnostics)
            clyfar_df_dict[clyfar_member] = member_df
            dailymax_df_dict[clyfar_member] = utils.compute_local_daily_max(
                member_df, target_tz=LOCAL_TIMEZONE)
            pass

        print("Clyfar inference complete for", init_dt_dict['naive'])

        # TODO - save datatables so those can be used to export json files
        # Each member needs possibility of each category for each time (row)
        # then with third dimension of ensemble members.

        if save:
            # subfolder for this run
            # Root gets us to subdir with date
            # subdir = os.path.join(clyfar_data_root,
                                  # init_dt_dict['naive'].strftime('%Y%m%d%H'),
                                  # )
            subdir = clyfar_data_root
            utils.try_create(subdir)
            for clyfar_member, df in clyfar_df_dict.items():
                df.to_parquet(os.path.join(
                    subdir, f"{clyfar_member}_df.parquet"))
            dailymax_dir = os.path.join(subdir, "dailymax")
            utils.try_create(dailymax_dir)
            for clyfar_member, df in dailymax_df_dict.items():
                df.to_parquet(os.path.join(
                    dailymax_dir, f"{clyfar_member}_dailymax.parquet"))
            print("Saved Clyfar dataframes to ", subdir)
            print("Saved daily-max ozone tables to ", dailymax_dir)

        if log_fis and fis_diagnostics:
            diag_df = pd.DataFrame(fis_diagnostics)
            diag_means = diag_df.mean(numeric_only=True)
            logger.info("FIS diagnostics mean values per member:\n%s",
                        diag_means.to_string())

        if visualise:
            do_optim_pessim = False
            do_heatmap = True
            do_dailymax_heatmap = True

            # TODO - create folders by run date and GEFS v Clyfar output

            print("Visualizing Clyfar data for", init_dt_dict['naive'])
            if do_optim_pessim:
                for clyfar_member in clyfar_df_dict.keys():
                    fig, ax = plot_percentile_meteogram(
                                    clyfar_df_dict[clyfar_member],
                                    )
                    fname = utils.create_meteogram_fname(init_dt_dict['naive'],
                                        "UB-pc", "ozone", clyfar_member)
                    subdir = os.path.join(clyfar_fig_root, "optim_pessim")
                    utils.try_create(subdir)
                    fig.savefig(os.path.join(subdir,fname))
                    plt.show()
                    plt.close(fig)
                    print("Saved optimist/pessimist plots to ", subdir)

            if do_heatmap:
                for clyfar_member in clyfar_df_dict.keys():
                    fig, ax = plot_ozone_heatmap(
                                    clyfar_df_dict[clyfar_member],
                                    )
                    fname = utils.create_meteogram_fname(init_dt_dict['naive'],
                                    "UB-poss", "ozone",
                                    clyfar_member, actually_heatmap=True,)
                    subdir = os.path.join(clyfar_fig_root, "heatmap")
                    utils.try_create(subdir)
                    fig.savefig(os.path.join(subdir,fname))
                    plt.show()
                    plt.close(fig)
                    print("Saved 3-h heatmaps of O3 categories to ", subdir)

            if do_dailymax_heatmap:
                for clyfar_member in clyfar_df_dict.keys():
                    daily_df = dailymax_df_dict.get(clyfar_member)
                    if daily_df is None or daily_df.empty:
                        logger.warning("Skipping daily-max heatmap for %s "
                                       "due to empty aggregation",
                                       clyfar_member)
                        continue
                    fig, ax = plot_dailymax_heatmap(daily_df)
                    fname = utils.create_meteogram_fname(init_dt_dict['naive'],
                                         "UB-dailymax", "ozone",
                                         clyfar_member, actually_heatmap=True,)
                    subdir = os.path.join(clyfar_fig_root, "heatmap")
                    utils.try_create(subdir)
                    fig.savefig(os.path.join(subdir,fname))
                    plt.show()
                    plt.close(fig)
                    print("Saved daily-max heatmaps of O3 categories to ", subdir)

    # TODO - the heatmaps could be normalised by baserate...

    pass
    print("Forecast workflow complete for", init_dt_dict['naive'])
    return

if __name__ == "__main__":
    # Ensure Matplotlib caches land in a writable path to avoid warnings
    if "MPLCONFIGDIR" not in os.environ:
        default_mplconfig = os.path.join(os.getcwd(), ".mplconfig")
        os.makedirs(default_mplconfig, exist_ok=True)
        os.environ["MPLCONFIGDIR"] = default_mplconfig

    # TODO - add data & figure paths (set by environment variables at runtime)
    parser = argparse.ArgumentParser(
            description="Run the parallel operational forecast workflow.")
    parser.add_argument(
        '-i', '--inittime', required=True,
        type=lambda s: datetime.datetime.strptime(s,
        '%Y%m%d%H'), help='Initialization time in YYYYMMDDHH format')
    parser.add_argument(
        '-n', '--ncpus', required=True, type=int,
        help='Number of CPUs to use')
    parser.add_argument(
        '-m', '--nmembers', required=True, type=int,
        help='Number of ensemble members to use')
    parser.add_argument(
        '-d', '--data-root', required=True, type=str,
        help='Root directory for data output')
    parser.add_argument(
        '-f', '--fig-root', required=True, type=str,
        help='Root directory for figure output')
    # parser.add_argument(
    #     '-x', '--maxhr', type=int,
    #     help='Maximum hours to run the models')
    parser.add_argument(
        '-v', '--verbose', action='store_true',
        help='Enable verbose logging')
    parser.add_argument(
        '-t', '--testing', action='store_true',
        help='Enable testing mode')
    parser.add_argument(
        '-nc', '--no-clyfar', action='store_true',
        help='Disable Clyfar processing')
    parser.add_argument(
        '-ng', '--no-gefs', action='store_true',
        help='Disable GEFS processing')
    parser.add_argument(
        '--log-fis', action='store_true',
        help='Log fuzzy-system diagnostics for calibration')
    parser.add_argument(
        '--serial-debug', action='store_true',
        help='Process members sequentially (no multiprocessing) for debugging')

    args = parser.parse_args()
    # Leave maxhr for now - not implemented

    print("Parsed Arguments:")
    print(f"Initialization Time: {args.inittime}")
    print(f"Number of CPUs: {args.ncpus}")
    print(f"Number of Members: {args.nmembers}")
    print(f"Verbose: {args.verbose}")
    print(f"Testing: {args.testing}")
    print(f"Do Clyfar: {not args.no_clyfar}")
    print(f"Do GEFS: {not args.no_gefs}")
    print("Saving data to root directory:", args.data_root)
    print("Saving figures to root:", args.fig_root)

    run_label = args.inittime.strftime('%Y%m%d_%H%MZ')
    run_suffix = "smoke" if args.testing else "run"
    run_id = f"{run_label}_{run_suffix}"
    summary_root = (os.path.join(args.data_root, "baseline_0_9")
                    if args.testing else args.data_root)
    started_utc = datetime.datetime.utcnow()
    run_failed = False
    try:
        main(dt=args.inittime,
             clyfar_fig_root=args.fig_root, clyfar_data_root=args.data_root,
             ncpus=args.ncpus, nmembers=args.nmembers,
             visualise=True, save=True,
             verbose=args.verbose, testing=args.testing,
             no_clyfar=args.no_clyfar, no_gefs=args.no_gefs,
             log_fis=args.log_fis,
             )
    except Exception:
        run_failed = True
        raise
    finally:
        if not run_failed:
            finished_utc = datetime.datetime.utcnow()
            cli_args = {
                "inittime": args.inittime.strftime("%Y%m%d%H"),
                "ncpus": args.ncpus,
                "nmembers": args.nmembers,
                "data_root": args.data_root,
                "fig_root": args.fig_root,
                "testing": args.testing,
                "no_clyfar": args.no_clyfar,
                "no_gefs": args.no_gefs,
                "log_fis": args.log_fis,
            }
            artifacts = {
                "forecast_data_dir": os.path.join(args.data_root, run_label),
                "figures_dir": os.path.join(
                    args.fig_root, args.inittime.strftime("%Y%m%d_%HZ")),
                "log_file": None,
                "performance_log": os.path.abspath("performance_log.txt"),
            }
            if args.testing:
                smoke_log = os.path.join(
                    args.data_root, "baseline_0_9", "logs",
                    f"smoke_{args.inittime.strftime('%Y%m%d%H')}.log")
                if os.path.exists(smoke_log):
                    artifacts["log_file"] = smoke_log
            env_info = {
                "python": platform.python_version(),
                "platform": platform.platform(),
                "conda_prefix": os.environ.get("CONDA_PREFIX"),
            }
            summary = {
                "run_id": run_id,
                "run_type": "smoke" if args.testing else "operational",
                "cli": {"argv": sys.argv, "args": cli_args},
                "timing": {
                    "started_utc": started_utc.isoformat() + "Z",
                    "finished_utc": finished_utc.isoformat() + "Z",
                    "duration_seconds": (finished_utc - started_utc).total_seconds(),
                },
                "artifacts": artifacts,
                "environment": env_info,
                "notes": "Baseline smoke run" if args.testing else "",
            }
            runlog_path = write_run_summary(summary_root, run_id, summary)
            print(f"Run metadata written to {runlog_path}")
