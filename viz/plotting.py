"""Plotting weather maps, meteograms, and other visualizations."""

import os
import datetime
import pytz

import matplotlib as M
import matplotlib.pyplot as plt
import numpy as np

def plot_meteogram(df, plot_col, title=None, save=None,second_df=None, second_col=None):
    """Plot a meteogram of the dataframe of data.

    Args:
        df (pd.DataFrame): DataFrame of data to plot.
        plot_col (str): Column in df to plot.
        title (str, optional): Title of the plot. Defaults to None.
        save (str, optional): Path to save the plot. Defaults to None.
        second_df (pd.DataFrame, optional): Second DataFrame of data to plot. Defaults to None.
        second_col (str, optional): Column in second_df to plot. Defaults to None.

    Returns:
        fig, ax: Matplotlib figure and axis objects.
    """

    fig, ax = plt.subplots(1, figsize=(12, 8), dpi=200)

    # Plotting the data
    ax.plot(df.index, df[plot_col])

    if second_df is not None:
        assert second_col is not None
        ax.plot(second_df.index, second_df[second_col])

    # Setting the title
    if title:
        ax.set_title(title, fontsize=16, fontweight='bold')

    # Formatting the UTC time on the x-axis
    ax.xaxis.set_major_formatter(M.dates.DateFormatter('%Y-%m-%d %H:%M', tz=pytz.utc))
    plt.xticks(rotation=45)

    fig.tight_layout()

    # Refresh the figure to ensure the labels are updated
    fig.canvas.draw()

    # Optional: Adding local time labels in red below UTC labels
    local_tz = pytz.timezone('America/Denver')  # Adjust for your timezone
    for tick in ax.get_xticklabels():
        # Ensure the tick label is not empty
        if tick.get_text():
            utc_time = datetime.datetime.strptime(tick.get_text(), '%Y-%m-%d %H:%M')
            local_time = utc_time.replace(tzinfo=pytz.utc).astimezone(local_tz)
            ax.text(tick.get_position()[0], tick.get_position()[1] - 0.05,
                    local_time.strftime('%-I:%M %p'), color='red',
                    ha='right', transform=ax.get_xaxis_transform())

    # Saving the figure
    if save is not None:
        fig.savefig(save)

    return fig, ax