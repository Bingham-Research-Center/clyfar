"""Functions related to computing the pseudo-lapse rate from temperature data (obs and forecast).
"""
import os

import numpy as np
import pandas as pd
from scipy import stats
import matplotlib.pyplot as plt

from obs.obsdata import ObsData
from viz import plotting

def compute_pseudo_lapse_rate(filt_temp_df, elevations, x_range=(1000, 4000), do_filter=False, elev_bins=None,
                              num_std_dev=1.5, do_plot=True):
    """
    Compute the pseudo-lapse rate using least squares regression and plot the results.

    Args:
        filt_temp_df (pd.DataFrame): DataFrame with the filtered temperature data.
        elevations (dict): Dictionary of station names and their elevations.
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
