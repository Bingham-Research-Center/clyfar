"""Functions to visualise the possibility distribution predicted by the FIS in this version of Clyfar.
"""

import os

import numpy as np
import matplotlib as M
import matplotlib.pyplot as plt

def plot_possibility_heatmap(possibility_df):
    pass

def plot_possibility_timeseries(df, fig=None, ax=None):
    """The rows/index is timestamp, and columns are the categories.
    """
    if fig is None:
        fig, ax = plt.subplots(figsize=(10, 5))
    # For each row, we want bars of different colours as x-axis locations
    # for each category, with the height of the bar being the possibility
    raise NotImplementedError
    return

def plot_possibility_bars(possibility_df):
    """Plot the possibility distribution as a bar chart.

    The dataframe should have column names as the category (e.g., 'elevated') and the row has value $[0--1]$.

    Args:
        possibility_df (pd.DataFrame): The possibility distribution as a DataFrame.

    """
    fig, ax = plt.subplots()
    ax.bar(possibility_df.columns, possibility_df.values[0])
    ax.set_ylabel('Possibility')
    ax.set_xlabel('Category')

    return fig, ax

def plot_percentile_meteogram(df, fig=None, ax=None,
                                transition_hour=240):
    if fig is None:
        fig,ax = plt.subplots(figsize=(10, 5))

    # Define the maroon/purple color for the example lines
    fave_color = '#4B0082'

    pc_colors = {
        # 10th percentile, low estimate of ozone, "green"
        10: '#00FF7F',
        # 50th percentile, middle estimate of ozone, "orange"
        50: '#FFA07A',
        # 90th percentile, high estimate of ozone, "red"
        90: '#FF6347',
    }

    # Plot best-, average-, and worst-case scenarios (10th, 50th, 90th percentiles)
    # Use plot colours defined in pc_colors
    ax.plot(df.index, df['ozone_10pc'], label="Optimistic (10th pc)",
            color=pc_colors[10], lw=1)
    ax.plot(df.index, df['ozone_50pc'], label="Neutral (50th pc)",
            color=pc_colors[50], lw=1)
    ax.plot(df.index, df['ozone_90pc'], label="Pessimistic (90th pc)",
            color=pc_colors[90], lw=1)

    # Shade between the 10th and 90th with a very faint fave_color
    ax.fill_between(df.index, df['ozone_10pc'], df['ozone_90pc'],
                    color=fave_color, alpha=0.2)

    # Label this is Clyfar ozone hindcasts for 2021/2022, perfect inputs (obs)
    # x-axis is date, y-axis is ozone concentration (ppb)
    ax.set_xlabel("Date", fontsize=12)
    ax.set_ylabel("Ozone Concentration (ppb)", fontsize=12)
    ax.set_title(f"Clyfar Ozone Predictions", fontsize=14)
    ax.set_ylim(20, 140)

    # Mark horizontal line at 70 ppb as grey dashed line in background (low z order)
    ax.axhline(y=70, color='grey', linestyle='--', alpha=0.6, zorder=0)

    # What x-axis value corresponds to transition_hour?
    # if isinstance(transition_hour,int):
    #     forecast_transition = df.index[transition_hour]

    # day10_note = "    10 days: coarser resolution hereon.   "
    # ax.text(forecast_transition[0], 0.035, day10_note,
    #     transform=ax.get_xaxis_transform(), ha='left', va='top',
    #     fontsize=8, color='darkgray')# pad=1)

    ax.legend()
    plt.show()
    return fig,ax
