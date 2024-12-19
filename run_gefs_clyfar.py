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
"""
import argparse
import multiprocessing as mp
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
    do_nwpval_snow, do_nwpval_mslp,
)
from utils import utils
from utils.geog_funcs import get_elevations_for_resolutions
from utils.lookups import Lookup
from utils.utils import configurable_timer
from viz.plotting import plot_meteogram
from fis.v1p0 import Clyfar
from viz.possibility_funcs import (plot_percentile_meteogram,
    plot_possibility_bar_timeseries, plot_ozone_heatmap)

######### SETTINGS ##########

L = Lookup()
clyfar = Clyfar()
clyfar_data_root = './data/clyfar_output'
utils.try_create(clyfar_data_root)
clyfar_fig_root = './figures/clyfar_output'
utils.try_create(clyfar_fig_root)

# Configure logging with precise timestamp and process identification
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s.%(msecs)03d - %(processName)s - %(message)s',
                   datefmt='%Y-%m-%d %H:%M:%S')

######### FUNCS ##########
def initialize_geography(latlons):
    """Initialize geographic masks and elevation data."""
    elev_df = {}
    masks = {}

    for res in ['0p25', '0p5']:
        elev_df[res] = get_elevations_for_resolutions(latlons, res)
        masks[res] = elev_df[res] < GEOGRAPHIC_CONSTANTS['elevation_threshold']

    return elev_df, masks

def get_optimal_process_count(ncpus=None) -> int:
    """
    Determine optimal process count based on system resources.

    Args:
        ncpus: Number of CPUs to use. If None, use all available CPUs minus 1.

    Returns:
    int: Optimal number of processes, reserving one core for system operations
    """
    # Just for the laptop so we don't overload it
    # TODO - argparse to set CPUs
    ncpus = max(1, mp.cpu_count() - 1)
    # For testing:
    # ncpus = 30
    ncpus = 10
    return ncpus

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

    def _process_ensemble_member_solar(self, member: str) -> Tuple[str, pd.DataFrame]:
        """Process solar radiation with high temporal resolution requirements."""
        self.logger.info(f"Processing solar forecast for member {member}")

        solar_dh = 6 if self.testing else FORECAST_CONFIG['solar_delta_h']
        solar_ts = do_nwpval_solar(
            init_dt_naive=self.init_dt,
            start_h=3,
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

    def process_variable_parallel(self,
                                member_names: List[str],
                                variable: str) -> Dict[str, pd.DataFrame]:
        """
        Execute parallel processing for specified meteorological variable.

        Args:
        member_names: List of ensemble member identifiers
        variable: Target meteorological variable

        Returns:
        Dictionary mapping member identifiers to processed DataFrames
        """
        processor_map = {
            'wind': self._process_ensemble_member_wind,
            'solar': self._process_ensemble_member_solar,
            'snow': self._process_ensemble_member_snow,
            'mslp': self._process_ensemble_member_mslp
        }

        if variable not in processor_map:
            raise ValueError(f"Unsupported variable: {variable}")

        # ctx = mp.get_context('spawn')
        # pool = ctx.Pool(processes=4)

        # with ctx.Pool(processes=self.process_count) as pool:
        with mp.Pool(processes=self.process_count) as pool:
            results = pool.map(processor_map[variable], member_names)

        return dict(results)

#### END OF CLASS ####

# @configurable_timer(log_file="performance_log.txt")
def parallel_forecast_workflow(init_dt: datetime.datetime,
                        masks: Dict,
                        member_names: List[str],
                        ncpus: int = None,
                        testing: bool = False,
                        ) -> Dict[str, Dict[str, pd.DataFrame]]:
    """
    Execute comprehensive parallel forecast workflow for all variables.

    Args:
    init_dt: Forecast initialization datetime
    masks: Geographic masks for data filtering
        member_names: List of ensemble member identifiers

    Returns:
    Nested dictionary of processed forecasts by variable and member
    """
    processor = ParallelEnsembleProcessor(init_dt, masks, process_count=ncpus,
                                            testing=testing)
    results = {}

    for variable in ['wind', 'solar', 'snow', 'mslp']:
        results[variable] = processor.process_variable_parallel(
            member_names, variable
        )

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
                      init_dt_dict: dict):
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

        rootdir = "./figures_parallel"
        dated_rootdir = make_dated_rootdir(rootdir, init_dt_dict)
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

    all_vrbl_dfs = {}
    for variable in ['snow', 'mslp', 'solar', 'wind']:
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

        # just for testing:
        # snow_val += 50.0
        # mslp_val += 4*100
        # wind_val /= 1.5
        # solar_val += 100

        # Use the variables in the function call
        pc_dict, poss_df = clyfar.compute_ozone(
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
        pass
    # Do we have columns for possibility, etc?
    # Whatever is needed for plotting data

    pass
    print("Clyfar inference complete for member",
                clyfar_member, "driven by GEFS member ", member)
    return output_df



############## CLYFAR FUNCS #####################
#################################################

def main(dt, maxhr='all', ncpus='auto', nmembers='all', visualise=True,
            save=True, verbose=False, testing=False, do_clyfar=True,
            # TODO change this to be true by default when workflow is developed
            # Too annoying with too little return to check in the parallel
            # processing whether the file exists or not, so manually toggle
            # that section.
            do_gefs=True):
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
    #T ODO - can skip GEFS download and run Clyfar on GEFS time series if
    # it was already saved to disc
    percentiles = [10, 50, 90]

    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Print how many CPUs, GPUs, memory, and threads we have for resources
    utils.print_system_info()

    # Initialize ensemble members and CPUs for parallelisation
    member_names = [f'p{n:02d}' for n in range(1, nmembers + 1)]
    if testing:
        member_names = member_names[:10]
        ncpus = 10
    else:
        ncpus = ncpus if ncpus != 'auto' else nmembers

    # Initialize geographic parameters
    latlons = {
        '0p25': check_and_create_latlon_files("0p25"),
        '0p5': check_and_create_latlon_files("0p5")
    }
    elev_df, masks = initialize_geography(latlons)

    # Get initialization time
    init_dt_dict = utils.get_valid_forecast_init(force_init_dt=dt)

    if do_gefs:
        print("Downloading GEFS data for", init_dt_dict['naive'])
        # Execute parallel workflow
        results = parallel_forecast_workflow(
                        init_dt_dict['naive'], masks, member_names, ncpus=ncpus,
                        testing=testing)
        print(results)

        if save:
            print("Saving GEFS data for", init_dt_dict['naive'])
            for variable, dfs in results.items():
                save_forecast_data(dfs, variable, init_dt_dict)

        if visualise:
            print("Visualizing GEFS data for", init_dt_dict['naive'])
            # Generate visualization suite
            visualize_results(results, init_dt_dict)



    # Run Clyfar here - GEFS time series already exists if everything went well
    # Go member by member to compute Clyfar
    if do_clyfar:
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

            # data_fname = f"clyfar-{1+nm:03d}_{dt.strftime('%Y%m%d_%H%M')}Z.parquet"
            # data_fpath = os.path.join(clyfar_data_root, data_fname)
            # utils.try_create(os.path.dirname(data_fpath))
            # clyfar_df.to_parquet(data_fpath)

        print("Clyfar inference complete for", init_dt_dict['naive'])

        if visualise:
            print("Visualizing Clyfar data for", init_dt_dict['naive'])
            for clyfar_member in clyfar_df_dict.keys():
                fig, ax = plot_percentile_meteogram(
                                clyfar_df_dict[clyfar_member],
                                )
                fname = utils.create_meteogram_fname(init_dt_dict['naive'],
                                    "UB-pc", "ozone", clyfar_member)
                fig.savefig(os.path.join(clyfar_fig_root,fname))


            # for clyfar_member in clyfar_df_dict.keys():
            #     fig, ax = plot_possibility_bar_timeseries(
            #                     clyfar_df_dict[clyfar_member],
            #                     )

            for clyfar_member in clyfar_df_dict.keys():
                fig, ax = plot_ozone_heatmap(
                                clyfar_df_dict[clyfar_member],
                                )
                fname = utils.create_meteogram_fname(init_dt_dict['naive'],
                                            "UB-heatmap", "ozone", clyfar_member)
                fig.savefig(os.path.join(clyfar_fig_root,fname))

            # TODO - the heatmaps could be normalised by baserate...
            # Could also hatch necessity etc
            pass


    pass
    print("Forecast workflow complete for", init_dt_dict['naive'])
    return

if __name__ == "__main__":
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
        '--no-clyfar', action='store_true',
        help='Disable Clyfar processing')
    parser.add_argument(
        '--no-gefs', action='store_true',
        help='Disable GEFS processing')

    args = parser.parse_args()
    # Leave maxhr for now - not implemented
    main(dt=args.inittime, ncpus=args.ncpus, nmembers=args.nmembers,
         visualise=True, save=True,
         verbose=args.verbose, testing=args.testing,
         # do_clyfar=not args.no_clyfar, do_gefs=not args.no_gefs
         do_clyfar=True, do_gefs=True,
         )
