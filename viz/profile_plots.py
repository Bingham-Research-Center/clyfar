"""Visualisations for vertical profiles of, e.g., temperature observed and/or modelled by NWP.

"""

import os

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


def compute_max_temp_profile(df, meta_df, target_date, timezone="US/Mountain"):
    """
    Compute the maximum temperature by station and day, and filter by a specific date.

    Args:
        df (pd.DataFrame): Original DataFrame with a datetime index and columns "stid" and "air_temp".
        meta_df (pd.DataFrame): Metadata DataFrame containing station information.
        target_date (str or pd.Timestamp): The target date to filter the results.
        timezone (str): The timezone to convert the DataFrame index to. Default is "US/Mountain".

    Returns:
        pd.DataFrame: DataFrame with maximum temperatures and elevations for the target date.
    """
    # Copy the dataframe for non-destructive playtime
    _df = df.copy(deep=True)[["stid", "air_temp"]]

    # Get dataframe into the specified timezone
    _df.index = _df.index.tz_convert(timezone)

    # Add a local_day column
    _df["local_day"] = _df.index.date

    # Ensure local_day is in datetime format
    _df["local_day"] = pd.to_datetime(_df["local_day"])

    # Group by 'stid' and 'local_day' to compute the maximum temperature
    max_temp = _df.groupby(["stid", "local_day"])["air_temp"].max().reset_index()
    max_temp = max_temp.rename(columns={"air_temp": "max_air_temp"})

    # Get elevations of the unique stations in max_temp in a dictionary
    elevations = {stid: meta_df[stid].loc["ELEV_DEM"] * 0.304 for stid in max_temp["stid"].unique()}

    # Filter to only those with the target date
    max_temp = max_temp[max_temp["local_day"] == pd.Timestamp(target_date)]

    # Add a column with the elevation of the station
    max_temp["elevation"] = max_temp["stid"].map(elevations)

    # Sort so elevation is ascending order.
    max_temp = max_temp.sort_values("elevation").dropna()

    return max_temp