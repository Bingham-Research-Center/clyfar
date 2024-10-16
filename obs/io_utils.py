"""Utility functions for reading and writing files with observation data etc.
"""

import os

import pandas as pd

from obs.obsdata import ObsData

def load_data_for_years(data_path, years, vrbl):
    """
    Load data for each year and count the number of unique stations that report at least one non-NaN for the given variable.

    Args:
        data_path (str): Path to the data files.
        years (list): List of years to load data for.
        vrbl (str): Variable name to check for non-NaN values.

    Returns:
        pd.DataFrame: DataFrame with counts of unique stations per year and their IDs.
    """
    year_counts = {}
    vrbl_stids = {}

    for year in years:
        df, meta_df = ObsData.load_dfs(data_path, f"UB_obs_{year}.parquet")

        try:
            small_df = df[[vrbl, "stid"]]
            year_counts[year] = small_df[small_df[vrbl].notnull()]["stid"].nunique()
            vrbl_stids[year] = small_df[small_df[vrbl].notnull()]["stid"].unique()
        except KeyError:
            print(f"Data for {year} not found")
            year_counts[year] = 0
            vrbl_stids[year] = []
            continue

    year_counts_df = pd.DataFrame.from_dict(year_counts, orient='index', columns=["stids"])
    stid_string_col = [",".join(vrbl_stids[year]) if len(vrbl_stids[year]) else "" for year in years]
    year_counts_df["stid_string"] = stid_string_col

    return year_counts_df