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

import multiprocessing as mp
from multiprocessing import Pool
import os
from typing import Dict, List, Tuple
import logging
import datetime
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
from utils.geog_funcs import save_elevations_for_resolutions
from utils.lookups import Lookup
from utils.utils import configurable_timer
from viz.plotting import plot_meteogram

# Configure logging with precise timestamp and process identification
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s.%(msecs)03d - %(processName)s - %(message)s',
                   datefmt='%Y-%m-%d %H:%M:%S')

def initialize_geography(latlons):
    """Initialize geographic masks and elevation data."""
    elev_df = {}
    masks = {}

    for res in ['0p25', '0p5']:
        elev_df[res] = save_elevations_for_resolutions(latlons, res, fdir='data')
        masks[res] = elev_df[res] < GEOGRAPHIC_CONSTANTS['elevation_threshold']

    return elev_df, masks

def get_optimal_process_count() -> int:
    """
    Determine optimal process count based on system resources.

    Returns:
    int: Optimal number of processes, reserving one core for system operations
    """
    # Just for the laptop so we don't overload it
    # TODO - argparse to set CPUs
    # ncpus = max(1, mp.cpu_count() - 2)
    ncpus = 30
    return ncpus

class ParallelEnsembleProcessor:
    """
    Manages parallel processing of ensemble forecasts with synchronized I/O operations.
    Implements specific processing methodologies for each meteorological variable.
    """

    def __init__(self, init_dt: datetime.datetime, masks: Dict,
                 process_count: int = None):
        """
        Initialize parallel processing environment with specified parameters.

        Args:
        init_dt: Initialization datetime for the forecast
            masks: Geographic masks for data filtering
            process_count: Number of parallel processes (defaults to optimal count)
        """
        self.init_dt = init_dt
        self.masks = masks
        self.process_count = (process_count if process_count is not None
                            else get_optimal_process_count())
        self.logger = logging.getLogger(__name__)
        self.lookup = Lookup()

    def _process_ensemble_member_wind(self, member: str) -> Tuple[str, pd.DataFrame]:
        """Process wind forecasts with quantile-based methodology."""
        self.logger.info(f"Processing wind forecast for member {member}")
        wind_ts = do_nwpval_wind(
                    init_dt_naive=self.init_dt,
                    start_h = 0,
                    max_h = FORECAST_CONFIG['max_h']['0p5'],
                    masks = self.masks,
                    delta_h = FORECAST_CONFIG['delta_h'],
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
        solar_ts = do_nwpval_solar(
            init_dt_naive=self.init_dt,
            start_h=3,
            max_h = 384,
            masks = self.masks,
            delta_h=FORECAST_CONFIG['solar_delta_h'],
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
        snow_ts = do_nwpval_snow(
                    init_dt_naive=self.init_dt,
                    start_h = 0,
                    max_h = FORECAST_CONFIG['max_h']['0p5'],
                    masks = self.masks,
                    delta_h = FORECAST_CONFIG['delta_h'],
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
        mslp_ts = do_nwpval_mslp(
            init_dt_naive=self.init_dt,
            lat=GEOGRAPHIC_CONSTANTS['ouray']['lat'],
            lon=GEOGRAPHIC_CONSTANTS['ouray']['lon'],
            member=member,
            delta_h=FORECAST_CONFIG['delta_h']
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

        with Pool(processes=self.process_count) as pool:
            results = pool.map(processor_map[variable], member_names)

        return dict(results)

#### END OF CLASS ####

@configurable_timer(log_file="performance_log.txt")
def parallel_forecast_workflow(init_dt: datetime.datetime,
                     masks: Dict,
                     member_names: List[str]) -> Dict[str, Dict[str, pd.DataFrame]]:
    """
    Execute comprehensive parallel forecast workflow for all variables.

    Args:
    init_dt: Forecast initialization datetime
    masks: Geographic masks for data filtering
        member_names: List of ensemble member identifiers

    Returns:
    Nested dictionary of processed forecasts by variable and member
    """
    processor = ParallelEnsembleProcessor(init_dt, masks)
    results = {}

    for variable in ['wind', 'solar', 'snow', 'mslp']:
        results[variable] = processor.process_variable_parallel(
            member_names, variable
        )

    return results

# Root directory for image output
def make_dated_rootdir(rootdir: str, init_dt: dict):
    # add the timestamp in a YYYYMMDD_HHZ format for the folder
    return os.path.join(
                    rootdir, init_dt['naive'].strftime('%Y%m%d_%HZ'))

def save_forecast_data(dfs: Dict[str, pd.DataFrame], variable: str,
                            init_dt: dict):
    """Save forecast data to disk."""
    dataroot = "./data"
    timestr = init_dt['naive'].strftime('%Y%m%d_%H%MZ')
    # vrbl = VARIABLE_METADATA['labels'][variable]
    for member, df in dfs.items():
        fpath = os.path.join(dataroot, timestr,
                        f"{timestr}_{variable}_{member}_df.parquet")
        utils.try_create(os.path.dirname(fpath))
        df.to_parquet(fpath)
    return

def visualize_results(results: Dict[str, Dict[str, pd.DataFrame]],
                        init_dt: dict):
    """
    Generate visualization suite for processed forecast results.

    Args:
        results: Nested dictionary of processed forecasts
    """
    for variable, dfs in results.items():
        title = (f"{VARIABLE_METADATA['labels'][variable]} forecast: "
                f"GEFS members initialised at "
                # f"{list(dfs.values())[0].index[0].strftime(
                #                      '%Y-%m-%d %H%M')} UTC"
                f"{init_dt['naive'].strftime('%Y-%m-%d %H%M')} UTC ("
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
        fname = utils.create_meteogram_fname(init_dt['naive'],
                                    "ouray", variable, "GEFS")

        rootdir = "./figures_parallel"
        dated_rootdir = make_dated_rootdir(rootdir, init_dt)
        utils.try_create(dated_rootdir)

        fig.savefig(fpath := os.path.join(dated_rootdir, fname))
        print("Saved figure to", fpath)
        plt.close(fig)
    return

def main(visualise=True, save=True):
    """Execute parallel operational forecast workflow.

    TODO:
    * Solar goes 6-h after fxx=240 so we could do a persistent forecast
        (one conclusion for write-up/analysis is finding a new way to do this)
    * ...
    """
    # Print how many CPUs, GPUs, memory, and threads we have for resources
    utils.print_system_info()

    # Initialize ensemble members
    member_names = [f'p{n:02d}' for n in range(1, 31)]

    # for testing
    # member_names = member_names[:10]

    # Initialize geographic parameters
    latlons = {
        '0p25': check_and_create_latlon_files("0p25"),
        '0p5': check_and_create_latlon_files("0p5")
    }
    elev_df, masks = initialize_geography(latlons)

    # Get initialization time
    init_dt = utils.get_valid_forecast_init(
        # force_init_dt=datetime.datetime(2024, 12, 16, 6, 0, 0)
        force_init_dt=datetime.datetime(2024, 12, 15, 18, 0, 0)
    )

    # Execute parallel workflow
    results = parallel_forecast_workflow(
        init_dt['naive'],
        masks,
        member_names
    )

    if visualise:
        # Generate visualization suite
        visualize_results(results, init_dt)

    if save:
        # Save to disc
        for variable, dfs in results.items():
            if variable == "solar":
                pass
            save_forecast_data(dfs, variable, init_dt)

    return

if __name__ == "__main__":
    main(visualise=True, save=True)
