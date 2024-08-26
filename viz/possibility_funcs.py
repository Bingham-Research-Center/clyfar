"""Functions to visualise the possibility distribution predicted by the FIS in this version of Clyfar.
"""

import os

import numpy as np
import matplotlib as M
import matplotlib.pyplot as plt

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