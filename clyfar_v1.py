"""Run Clyfar version 1 using GEFS NWP data as input.

The configuration for Clyfar's v1 FIS is in __v1p0.py. This script pieces
together the FIS components. The FIS class instance has methods for
generating and plotting output (forecasts of different types) from Clyfar.

TODO:
* A argparse interface for creating images or website resources
* Time zones are messed up
* Reduction to single numbers per day
* Insolation needs fixing after 240h
* Check percentile computation is interpolated or nearest neighbor

John Lawson, December 2024, Bingham Research Center & Utah State Univ.
"""
import os
import datetime

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt

from fis.v1p0 import Clyfar
from utils import utils
from utils.lookups import Lookup

# Some settings here
L = Lookup()
percentiles = [10, 50, 90]
n_members = 30
member_names = [f"p{i:02d}" for i in range(1, n_members+1)]

# For testing:
member_names = member_names[:10]

# Load the configuration for Clyfar version 1
clyfar = Clyfar()

clyfar_data_root = './data/clyfar_output'
clyfar_fig_root = './figures/clyfar_output'

dt = datetime.datetime(2024, 12, 16, 12, 0, 0)

# Load forecast data
def load_forecast_data(variable: str, init_dt: datetime.datetime, member_names: list):
    """Load forecast data from disk."""
    dataroot = "./data"
    timestr = init_dt.strftime('%Y%m%d_%H%MZ')
    dfs = {}
    for member in member_names:
        fpath = os.path.join(dataroot, timestr, f"{timestr}_{variable}_{member}_df.parquet")
        if os.path.exists(fpath):
            dfs[member] = pd.read_parquet(fpath)
        else:
            print(f"Warning: File {fpath} does not exist.")
    return dfs

all_dfs = {}
for variable in ['snow', 'mslp', 'solar', 'wind']:
    all_dfs[variable] = load_forecast_data(variable,
                            dt,
                            # datetime.datetime(2024,12,10,12,0,0),
                            member_names = member_names,
                            )

pass

# forecast_data is structured as thus:
# forecast_data['snow']['p01']['sde'] is a pandas series of snow depth
# TODO - a function that reorganises this into a dictionary of dataframes
# something more like data_dict['p01']['snow'] gives a value of a Pandas
# Series of snow depth and then we can concatenate later to a dataframe.
# We also need datetimes kept aside as indices for the output dataframe.

# TODO - redo this function to instead have
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

data_dict = reorganise_data(all_dfs)

# Run inference with forecast data as inputs
def run_inference(forecast_data: dict, percentiles, bogus_add=None):
    """Run inference with forecast data as inputs.

    This should be for just one member.
    """

    snow_name = L.string_dict['snow']['array_name']
    mslp_name = L.string_dict['mslp']['array_name']
    wind_name = L.string_dict['wind']['array_name']
    solar_name = L.string_dict['solar']['array_name']

    output_df = pd.DataFrame(index=forecast_data[
                            member_names[0]]['snow'].index.copy())

    # Make a dictionary that has this blank template for each member
    output_df_dict = {member: output_df.copy(
                            deep=True) for member in member_names}

    if bogus_add is None:
        bogus_add = {'snow': 0, 'mslp': 0, 'wind': 0,
                        'solar': 0}

    # TODO - do daily values so each day has one clyfar possibility forecast
    # TODO - for solar, take fraction of max for the day after 240h and adjust
    # Always group by local midnight to midnight for each day
    # Main run: a 7am Clyfar run using 0600 UTC GEFS data (7 or 8 hours lag)

    for member, df_dict in forecast_data.items():
        pass
        for nt, dt in enumerate(df_dict['snow'].index):
            # Don't use iloc as some variables have different rows present
            if nt == 0:
                print("Solar radiation is unavailable for first time.")
                for pct in percentiles:
                    output_df_dict[member].loc[dt, f'ozone_{pct}pc'] = np.nan
                continue
                # print(f"Variables at this point are: {member=}, {df=}, "
                #       f"{nt=}, {dt=}")
            # Hacky with units - TODO - fix this with pint package
            # bogus add is a dictionary of values to add to the forecast
            snow_val = bogus_add['snow'] + df_dict["snow"][snow_name].loc[dt] * 10  # For cm
            mslp_val = bogus_add['mslp'] + df_dict["mslp"][mslp_name].loc[dt] * 100  # For Pa
            wind_val = bogus_add['wind'] + df_dict["wind"][wind_name].loc[dt]
            solar_val =bogus_add['solar'] + df_dict["solar"][solar_name].loc[dt]

            # Use the variables in the function call
            pc_dict, _ = clyfar.compute_ozone(
                snow_val,
                mslp_val,
                wind_val,
                solar_val,
                percentiles=percentiles,
            )
            for pct in percentiles:
                output_df_dict[member].loc[dt, f'ozone_{pct}pc'] = pc_dict[pct]
            # Also include the values above ending in _val
            output_df_dict[member].loc[dt, 'snow'] = snow_val
            output_df_dict[member].loc[dt, 'mslp'] = mslp_val
            output_df_dict[member].loc[dt, 'wind'] = wind_val
            output_df_dict[member].loc[dt, 'solar'] = solar_val
    return output_df_dict

# Way to force inference to add these values to see difference to forecast
# bogus_add = {'snow': 80, 'mslp': 0, 'wind': -1, 'solar': 50}
bogus_add = None
clyfar_df = run_inference(data_dict, percentiles, bogus_add=bogus_add)
pass

data_fname = f"clyfar_{dt.strftime('%Y%m%d_%H%M')}Z.parquet"
data_fpath = os.path.join(clyfar_data_root, data_fname)
utils.try_create(os.path.dirname(data_fpath))
clyfar_df.to_parquet(data_fpath)

##### VIZ #####


# TODO - hour 240 buggered by solar? Is it every 3h then every 6 for plot?

# Improved figure to see the 50th percentile of ozone for each member
fig, ax = plt.subplots(figsize=(12, 6))  # Longer width than height

# Define a color map for better distinction between lines
colors = plt.cm.viridis(np.linspace(0, 1, len(clyfar_df)))

for color, (member, df) in zip(colors, clyfar_df.items()):
    ax.plot(df.index, df['ozone_50pc'], color=color, alpha=0.7, lw=1.5)

# Set labels for the axes
ax.set_xlabel('Datetime')
ax.set_ylabel('Ozone (ppb)')

# Format the x-axis to show simple datetime tick labels
ax.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%Y-%m-%d'))
fig.autofmt_xdate()

# Remove the legend for clarity
# ax.legend()

fname = f"clyfar-50pc_{dt.strftime('%Y%m%d_%H%M')}Z.png"
fig.savefig(os.path.join(clyfar_fig_root, fname))


# TODO - save figure so it can be archived and called by website



plt.show()


# We then have output for each GEFS ensemble member
# Show output time series forecasts of ozone percentiles over the 16 days

# Visualise different aspects of Clyfar (inputs, aggregation, memberships)
