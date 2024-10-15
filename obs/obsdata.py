import datetime
import itertools
import os

import metpy.calc
from metpy.units import units
import numpy as np
import pandas as pd

import synoptic.services as ss

import utils.utils as utils
# from utils.lookups import obs_vars

class ObsData:
    def __init__(self,start_date,end_date,recent=12*60*60, radius_mi=45, radius_ctr="UCL21",
                    vrbls=None, qc=None):
        """Download, process, and archive observation data.
        """
        self.start_date = start_date
        self.end_date = end_date
        self.recent = recent
        self.qc = qc

        # format example: radius="UCL21,50"
        radius_str = f"{radius_ctr},{radius_mi}"
        self.radius_str = radius_str

        self.vrbls = self.return_variable_list(vrbls)
        self.meta_df = self.create_metadata_df()
        self.stids = [str(s) for s in self.meta_df.columns]

        self.df = self.create_df()

    def create_metadata_df(self):
        # TODO - check this finds all stations within certain time, not just recent
        df_meta = ss.stations_metadata(radius=self.radius_str) #, recent=self.recent)
        return df_meta

    def get_elevations(self):
        elevs = []
        for stid in self.stids:
            elevs.append(self.meta_df[stid].loc["ELEVATION"]*0.304)
        return elevs

    def create_df(self):
        """Create a dataframe of observation data for the period/area of interest.

        TODO:
        * Decide what to do about "_set_" variables

        Returns:
            pd.DataFrame: dataframe of observation data

        """
        # Make dataframe of data for this period
        df_list = []

        for stid in self.stids:
            print("Loading data for station", stid)
            try:
                _df = ss.stations_timeseries(stid=stid, start=self.start_date, end=self.end_date, vars=self.vrbls,
                                                verbose=False,
                                             qc_checks='all',
                                             # qc_checks='synopticlabs',
                                             # qc_remove_data="on",
                                             )
            except AssertionError:
                # raise
                print("Skipping", stid)
                # continue

            # Assign this metadata to the variables df for ease of access
            # TODO - maybe remove?
            # stid_lat = self.meta_df[stid].loc["latitude"]  # .values.squeeze()
            # stid_lon = self.meta_df[stid].loc["longitude"]  # .values.squeeze()
            # elev = self.meta_df[stid].loc["ELEVATION"] * 0.304  # .values.squeeze()*0.304

            ############# Uncomment below for density calculation: ##########
            # if ("pressure" in _df.columns) and ("air_temp" in _df.columns) and ("dew_point_temperature" in _df.columns):
            #     rho = get_density(_df["pressure"],_df["air_temp"]+273.15,_df["dew_point_temperature"]+273.15)
            #     _df = _df.assign(air_density=rho.values)
            _df =  _df.assign(stid=stid)
            #, elevation=elev, latitude=stid_lat, longitude=stid_lon)

            # Check certain data for QC
            # _df = self.check_constant_temps(_df)

            pd.to_datetime(_df.index.strftime('%Y-%m-%dT%H:%M:%SZ'))
            df_list.append(_df)

        df = pd.concat(df_list, axis=0, ignore_index=False)

        # Reduce memory use
        col64 = [df.columns[i] for i in range(len(list(df.columns))) if (df.dtypes.iloc[i] == np.float64)]
        change_dict = {c: np.float32 for c in col64}

        # Adding ozone concentration because it's randomly an object
        # change_dict["ozone_concentration"] = np.float32

        # Making stid string type
        change_dict["stid"] = str

        df = df.astype(change_dict)

        # Convert invalid or empty strings to NaN
        if "ozone_concentration" in df.columns:
            df['ozone_concentration'] = pd.to_numeric(df['ozone_concentration'], errors='coerce')
        return df

    @classmethod
    def filter_temperature_outliers(cls, df, elev_bins, num_std_dev=2):
        filtered_dfs = []

        for min_elev, max_elev in itertools.zip_longest(elev_bins[:-1], elev_bins[1:]):
            # Select the subset of the DataFrame within the elevation bin
            pass
            sub_df = df[(df["elevation"] > min_elev) & (df["elevation"] <= max_elev)]

            # Calculate mean and standard deviation of air_temp in this bin
            mean_temp = sub_df["drybulb"].mean()
            std_dev_temp = sub_df["drybulb"].std()

            # Define the acceptable range for air_temp
            lower_bound = mean_temp - num_std_dev * std_dev_temp
            upper_bound = mean_temp + num_std_dev * std_dev_temp

            # Filter out rows where air_temp is outside the acceptable range
            filtered_sub_df = sub_df[(sub_df["drybulb"] > lower_bound) & (sub_df["drybulb"] < upper_bound)]

            # Append the filtered sub-dataframe to the list
            filtered_dfs.append(filtered_sub_df)

        # Concatenate all the filtered sub-dataframes
        filtered_df = pd.concat(filtered_dfs)
        pass
        return filtered_df

    @staticmethod
    def return_variable_list(vrbls_user):
        # Variables we care about in operations
        # TODO: put in lookup file under utils module eventually
        if vrbls_user is not None:
            obs_vars = vrbls_user
        else:
            obs_vars = ["wind_speed", "wind_direction",
                        "air_temp", "dew_point_temperature",
                        "pressure", "snow_depth", "solar_radiation",
                        "altimeter", "soil_temp",
                        "sea_level_pressure", "snow_accum",
                        "ceiling", "soil_temp_ir",
                        "snow_smoothed", "snow_accum_manual", "snow_water_equiv",
                        "net_radiation_sw",
                        "sonic_air_temp", "sonic_vertical_vel",
                        "vertical_heat_flux", "outgoing_radiation_sw",
                        "PM_25_concentration", "ozone_concentration",
                        "derived_aerosol_boundary_layer_depth",
                        "NOx_concentration", "PM_10_concentration",
                    ]
        return obs_vars

    @staticmethod
    def get_latest_hour():
        current_time = datetime.datetime.utcnow()
        # If past 20 min, use latest hour
        if current_time.minute > 20:
            latest_hr_dt = current_time.replace(minute=0, second=0, microsecond=0)
        # Else go back 1 hour + minutes
        else:
            latest_hr_dt = current_time.replace(minute=0, second=0, microsecond=0) - datetime.timedelta(hours=1)
        return latest_hr_dt

    def get_profile_df(self, dt:pd.Timestamp, temp_type="drybulb",tolerance=5):
        profile_data = []
        df = self.df

        for stid in self.stids:
            elev = self.meta_df[stid].loc["ELEVATION"]*0.304
            # print(stid)
            # Time window is just for memory efficiency - tolerance is set later
            sub_df = df[
                (df['stid'] == stid) &
                (df.index <= dt + pd.Timedelta(minutes=tolerance)) &
                (df.index >= dt - pd.Timedelta(minutes=tolerance))
                ]

            # print(sub_df["air_temp"])

            # i = sub_df.index.get_indexer([prof_dt,],method='nearest')
            # print(i)
            if len(sub_df) == 0:
                print("no measurement in this range.")
                continue

            pass

            # temp = sub_df["air_temp"].iloc[i]
            temp = utils.get_closest_non_nan(sub_df, "air_temp", dt, pd.Timedelta(f'{tolerance} minutes'))
            # print(temp)

            elev = utils.get_closest_non_nan(sub_df, "elevation", dt, pd.Timedelta(f'{tolerance}minutes'))
            # print(elev)

            if temp_type == "drybulb":
                if (not np.isnan(temp)) and (not np.isnan(elev)):
                    profile_data.append([elev, temp])

            elif temp_type == "theta":
                raise Exception
                # p = sub_df["pressure"].iloc[i]
                p = utils.get_closest_non_nan(sub_df, "pressure", dt, pd.Timedelta('30 minutes'))

                # Can we estimate p from elev?

                if (not np.isnan(temp)) and (not np.isnan(p)):
                    theta = metpy.calc.potential_temperature(p * units("pascal"), temp * units("celsius")).magnitude
                    # print(theta)

                    # print(elev)

                    profile_data.append([elev, theta])
                    # print("Added theta", theta, "at", elev, )
                # print("Skipping due to missing in something:", temp, p)
        t_df = pd.DataFrame(profile_data, columns=["elevation", temp_type])
        elev_bins = [1000,1500,2000,2500,3000,3500,4000]
        t_df = self.filter_temperature_outliers(t_df,elev_bins)
        return t_df

    @classmethod
    def combine_dataframes(cls, df_old, df_new):
        # Make index (datetime) a column (date_time)
        df_old = df_old.reset_index()
        df_new = df_new.reset_index()

        # Combine the dataframes
        combined_df = pd.concat([df_old, df_new])

        # Identify columns that don't have NaNs and aren't dicts for duplicate checking
        hashable_cols = [col for col in combined_df.columns
                         if not combined_df[col].isna().any()
                         and not isinstance(combined_df[col].iloc[0], dict)]

        # Drop duplicates considering only hashable columns
        combined_df = combined_df.drop_duplicates(subset=hashable_cols)

        # Set the 'datetime' column back as the index
        combined_df.set_index('date_time', inplace=True)

        return combined_df

    @classmethod
    def create_meta_filename(cls, fname):
        """Create a metadata filename by adding '_meta' before the extension."""
        fname_base, fname_ext = os.path.splitext(fname)
        # Use pickle, not parquet, for metadata due to object dtypes
        fname_ext = ".pkl"
        return f"{fname_base}_meta{fname_ext}"

    def save_df(self, fdir="../data", fname="obs_test1.parquet",
                    drop_na=False):
        """Save obs data and its metadata to a file for storage on disc.

        The obs data uses parquet but metadata uses pickle due to its dtypes being object.

        Args:
            fdir (str): directory to save the two files (.parquet file)
            fname (str): filename of main (observation) dataframe to save the file

        Returns:
            None
        """
        utils.try_create(fdir)

        # Save the obs dataframe to parquet
        fpath = os.path.join(fdir, fname)

        if drop_na:
            self.df.dropna(how='all').to_parquet(fpath, engine="pyarrow")
        else:
            self.df.to_parquet(fpath, engine="pyarrow")

        # Save the metadata dataframe to pickle
        fname_meta = self.create_meta_filename(fname)
        fpath_meta = os.path.join(fdir, fname_meta)
        utils.save_to_pickle(self.meta_df, fpath_meta)

        return

    @staticmethod
    def load_dfs(fdir="../data", fname="obs_test1.parquet"):
        """Load obs data and its metadata from a parquet file on disc.

        Args:
            fdir (str): directory from which to load the two files
            fname (str): filename of main (observation) dataframe

        Returns:
            tuple: (df, meta_df) where df are obs and meta_df is the metadata
        """
        fname_meta = ObsData.create_meta_filename(fname)
        df = pd.read_parquet(os.path.join(fdir, fname), engine="pyarrow")
        meta_df = utils.load_from_pickle(os.path.join(fdir, fname_meta))
        return df, meta_df