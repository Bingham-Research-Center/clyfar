"""Functions related to computing the pseudo-lapse rate from temperature data (obs and forecast).
"""
import os

import numpy as np
import pandas as pd
from scipy import stats
import matplotlib.pyplot as plt

from obs.obsdata import ObsData
from viz import plotting
from viz.profile_plots import compute_max_temp_profile


def compute_pseudo_lapse_rate(filt_temp_df, elevations, x_range=(1000, 4000), do_filter=False, elev_bins=None,
                              num_std_dev=1.5, do_plot=True):
    """
    Compute the pseudo-lapse rate using least squares regression and plot the results.

    Args:
        filt_temp_df (pd.DataFrame): DataFrame with the filtered temperature data.
        elevations (dict): Dictionary of names and elevations for plotting vertical lines on the figure for reference.
        x_range (tuple): Tuple of the x-axis range for the plot. Default is (1000, 4000).
        do_filter (bool): Whether to filter the temperature data. Default is False.
        elev_bins (list): List of elevation bins for filtering. Default is None.
        num_std_dev (float): Number of standard deviations to use for filtering. Default is 1.5.

    Returns:
        float: The computed slope of the regression line (pseudo-lapse rate) in °C/km.
    """
    if do_filter:
        assert elev_bins is not None
        filt_temp_df = ObsData.filter_temperature_outliers(filt_temp_df, elev_bins, num_std_dev=num_std_dev)

    # Compute the least squares regression
    slope, intercept, r_value, p_value, std_err = stats.linregress(filt_temp_df["elevation"],
                                                                   filt_temp_df["max_air_temp"])

    # Print the slope in °C/km
    lapse_rate = slope * 1000
    print(f"Pseudo-lapse rate: {lapse_rate:.2f} °C/km")

    if do_plot:
        # Plot the profile
        fig, ax = plotting.plot_profile(filt_temp_df["max_air_temp"], filt_temp_df["elevation"], "obs",
                                        plot_levels=elevations)

        # Visualize the least squares regression as a line on the axes "ax"
        x = np.linspace(x_range[0], x_range[1], 100)
        y = slope * x + intercept
        ax.plot(y, x, color='black', linestyle='dashed')
        plt.show()

    return lapse_rate

def compute_plr_timeseries(temp_df, meta_df, elevations, start_year, end_year, elev_bins, num_std_dev=1,
                                start_month=12, end_month=3, start_day=1, end_day=15):
    """
    Compute the pseudo-lapse rate for each day within the specified date range.

    Args:
        temp_df (pd.DataFrame): DataFrame containing temperature data.
        meta_df (pd.DataFrame): DataFrame containing metadata.
        elevations (dict): Dictionary of names and elevations for plotting vertical lines on the figure for reference.
        start_year (int): The starting year of the range.
        end_year (int): The ending year of the range.
        elev_bins (list): List of elevation bins for filtering.
        num_std_dev (int): Number of standard deviations for filtering. Default is 1.
        start_month (int): The starting month of period. Default is 12. (Winter)
        end_month (int): The ending month of period. Default is 3. (Winter)
        start_day (int): The starting day of period. Default is 1.
        end_day (int): The ending day of period. Default is 15. (End of Ozone Alert)

    Returns:
        pd.DataFrame: DataFrame containing the lapse rate for each day.
    """
    lapse_rate_list = []

    start_date = f"{start_year:d}-{start_month:02d}-{start_day:02d}"
    end_date = f"{end_year:d}-{end_month:02d}-{end_day:02d}"

    for date in pd.date_range(start_date, end_date):
        max_temp = compute_max_temp_profile(temp_df, meta_df, date.strftime("%Y-%m-%d"))
        lapse_rate = compute_pseudo_lapse_rate(max_temp, elevations, do_filter=True, elev_bins=elev_bins,
                                                    num_std_dev=num_std_dev, do_plot=False)
        lapse_rate_list.append({"date": date, "lapse_rate": lapse_rate})

    lapse_rate_df = pd.DataFrame(lapse_rate_list)
    return lapse_rate_df