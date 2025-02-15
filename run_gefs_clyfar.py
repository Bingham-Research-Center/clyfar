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
from typing import Dict, List, Tuple
import logging
import datetime

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt

from nwp.download_funcs import check_and_create_latlon_files
from fis.v1p0 import (
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
from viz.plotting import plot_meteogram
from fis.v1p0 import Clyfar
from viz.possibility_funcs import (plot_percentile_meteogram,
                                   plot_possibility_bar_timeseries,
                                   plot_ozone_heatmap, plot_dailymax_heatmap)

######### SETTINGS ##########
# At the top of the file, enforce spawn context
if mp.get_start_method() != 'spawn':
    try:
        mp.set_start_method('spawn', force=True)
    except RuntimeError:
        print("Warning: Could not set spawn context. Already initialized.")

L = Lookup()
clyfar = Clyfar()

# TODO - DYNAMIC PATHS
# clyfar_data_root = './data/clyfar_output'
# utils.try_create(clyfar_data_root)
# clyfar_fig_root = './figures/clyfar_output'
# utils.try_create(clyfar_fig_root)

# Configure logging with precise timestamp and process identification
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s.%(msecs)03d - %(processName)s - %(message)s',
                   datefmt='%Y-%m-%d %H:%M:%S')

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
            mask_temp = elev_df[res] < GEOGRAPHIC_CONSTANTS[
            # Arbitrary extra 500m buffer as we're smoothing and masking anyway
                        'elevation_threshold'] + 250

            # Temporary for now
            masks[res] = mask_temp

            # Apply the weighted average
            weighted_elev = weighted_average(elev_df[res], mask_temp)
            elev_df[res] = weighted_elev
            masks[res] = elev_df[res] < GEOGRAPHIC_CONSTANTS['elevation_threshold']

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
    avg_neighbors = np.divide(sum_neighbors,neighbor_counts)


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
        processor_map = self.get_processor_maps()

        with mp.Pool(processes=self.process_count) as pool:
            results = pool.map(process_member_variable, [(member, variable, processor_map) for member in member_names for variable in variables])

        nested_results = {}
        for variable, member, df in results:
            if variable not in nested_results:
                nested_results[variable] = {}
            nested_results[variable][member] = df

        return nested_results

#### END OF CLASS ####

# @configurable_timer(log_file="performance_log.txt")
def parallel_forecast_workflow(init_dt: datetime.datetime, masks: Dict, member_names: List[str], variables: List[str], ncpus: int = None, testing: bool = False) -> Dict[str, Dict[str, pd.DataFrame]]:
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
    for member, df in dfs.items():
        fpath = create_forecast_fname(variable, member, init_dt_dict['naive'])
        utils.try_create(os.path.dirname(fpath))
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
    # clyfar001 etc
    if gefs_member.startswith('p'):
        return f'clyfar{int(gefs_member[1:]):03d}'
    elif isinstance(gefs_member, int):
        # Assuming the number is correctly starting at 1!
        return f'clyfar{gefs_member:03d}'
    else:
        raise Exception

def run_singlemember_inference(init_dt: datetime.datetime, member, percentiles):
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
        # Put the dataframe for this member and variable into the dictionary
        all_vrbl_dfs[variable] = load_forecast_data(variable, init_dt,
                                    member_names = [member,])[member]

    # data_dict = reorganise_data(all_vrbl_dfs)

    # Get the datetime of all rows possible (solar not on first)
    indices = all_vrbl_dfs['snow'].index.copy()
    output_df = pd.DataFrame(index=indices)

    for nt, dt in enumerate(indices):
        if nt == 0:
            print("Solar radiation is unavailable for first time.")
            for pct in percentiles:
                output_df.loc[dt, f'ozone_{pct}pc'] = np.nan
            continue

        # Hacky with units - TODO - fix this with pint package
        snow_val = all_vrbl_dfs["snow"][snow_].loc[dt] * 1000  # For m to mm
        mslp_val = all_vrbl_dfs["mslp"][mslp_].loc[dt] * 100  # For hPa to Pa
        wind_val = all_vrbl_dfs["wind"][wind_].loc[dt] # already in m/s?
        solar_val = all_vrbl_dfs["solar"][solar_].loc[dt] # already w/m2 TODO Crap after 240h
        temp_val = all_vrbl_dfs["temp"][temp_].loc[dt] # already in C

        # Use the variables in the function call
        pc_dict, poss_df = clyfar.compute_ozone(
            # Don't need temp, that's for visualising only
            snow_val, mslp_val, wind_val, solar_val,
            percentiles=percentiles)

        for pct in percentiles:
            output_df.loc[dt, f'ozone_{pct}pc'] = pc_dict[pct]

        for cat in poss_df.index:
            output_df.loc[dt, cat] = poss_df.loc[cat].values

        # Also include the values above ending in _val
        output_df.loc[dt, 'snow'] = snow_val
        output_df.loc[dt, 'mslp'] = mslp_val
        output_df.loc[dt, 'wind'] = wind_val
        output_df.loc[dt, 'solar'] = solar_val
        output_df.loc[dt, 'temp'] = temp_val
        pass
    # Do we have columns for possibility, etc?
    # Whatever is needed for plotting data

    pass
    print("Clyfar inference complete for member",
                clyfar_member, "driven by GEFS member ", member)
    return output_df



############## CLYFAR FUNCS #####################
#################################################

def main(dt, clyfar_fig_root, clyfar_data_root,
         maxhr='all', ncpus='auto', nmembers='all', visualise=True,
         save=True, verbose=False, testing=False, no_clyfar=False,
         no_gefs=False):
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
    percentiles = [10, 50, 90]

    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    utils.print_system_info()

    member_names = [f'p{n:02d}' for n in range(1, nmembers + 1)]
    print(member_names, nmembers)

    if testing:
        member_names = member_names[:10]
        ncpus = 10
    else:
        ncpus = ncpus if ncpus != 'auto' else nmembers * 5  # Adjust for both members and variables

    latlons = {
        '0p25': check_and_create_latlon_files("0p25"),
        '0p5': check_and_create_latlon_files("0p5")
    }
    elev_df, masks = initialize_geography(latlons)

    init_dt_dict = utils.get_valid_forecast_init(force_init_dt=dt)

    variables = ['wind', 'solar', 'snow', 'mslp', 'temp']

    if not no_gefs:
        print("Downloading GEFS data for", init_dt_dict['naive'])
        results = parallel_forecast_workflow(
            init_dt_dict['naive'], masks, member_names, variables, ncpus=ncpus,
            testing=testing)

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
    if not no_clyfar:
        print("Running Clyfar for", init_dt_dict['naive'])

        ############################
        # TODO Create daily values
        ############################

        clyfar_df_dict = {}
        for nm, member in enumerate(member_names):
            clyfar_member = gefs_to_clyfar_membername(member)
            # TODO - no dicts; just save members in a folder for the run?
            clyfar_df_dict[clyfar_member] = run_singlemember_inference(
                init_dt_dict['naive'], member,
                percentiles)
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
                df.to_parquet(os.path.join(subdir,
                                f"{clyfar_member}_df.parquet"))
            print("Saved Clyfar dataframes to ", subdir)

        if visualise:
            do_optim_pessim = False
            do_heatmap = True
            do_dailymax_heatmap = False

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
                    fig, ax = plot_dailymax_heatmap(
                                    clyfar_df_dict[clyfar_member],
                                    )
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

    main(dt=args.inittime,
         clyfar_fig_root=args.fig_root, clyfar_data_root=args.data_root,
         ncpus=args.ncpus, nmembers=args.nmembers,
         visualise=True, save=True,
         verbose=args.verbose, testing=args.testing,
         no_clyfar=args.no_clyfar, no_gefs=args.no_gefs,
         )
