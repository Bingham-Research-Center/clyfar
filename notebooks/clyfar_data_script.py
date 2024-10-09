"""
Weather Data Retrieval Script

This script provides a command-line tool for retrieving weather data from the Synoptic API and Herbie.
Users can specify a date range, weather stations, and variables to retrieve, with options to save the results as JSON or HDF5 files.
It also supports downloading forecast data using Herbie for specific dates.

Usage

Run the script from the command line, providing necessary arguments for data retrieval:

Example:
python weather_data.py --start 04092023 --end 05092023 --stations Vernal,Dinosaur --variables air_temp,dew_point --save_to_json data.json

This command fetches weather data for the specified dates, stations, and variables, and saves the output in JSON format.

Command-Line Arguments

--start (str, required): Start date for data retrieval in the format DDMMYYYY (e.g., 04091991).

--end (str, optional): End date for data retrieval in the format DDMMYYYY (e.g., 05091991). If not provided, only the start date is used.

--stations (str, optional): Comma-separated list of station names (e.g., Vernal,Dinosaur NM). If not provided, defaults to a set of predefined stations.

--variables (str, optional): Comma-separated list of weather variables to retrieve (e.g., air_temp,dew_point). If not specified, all valid variables are used.

--save_to_json (str, optional): File path to save output data as a JSON file.

--save_to_hdf5 (str, optional): File path to save output data as an HDF5 file.

Features

Environment Variable Loading:

Loads API tokens and other environment variables using the dotenv package.

Synoptic API Integration:

Retrieves weather timeseries data for specified stations and variables.

Makes API calls using requests and formats the response as JSON.

Herbie Integration:

Uses Herbie to download weather forecast data for specific dates.

Flexible Date Parsing:

Accepts dates in DDMMYYYY format, converting them to an appropriate format for API requests.

Data Saving Options:

Can save retrieved data as JSON or HDF5 files for further analysis or storage.
"""

import os
import argparse
import requests
import json
import h5py
from herbie import Herbie
import subprocess
from pathlib import Path
import certifi
from pyproj._context import _set_context_ca_bundle_path
from pyproj._network import is_network_enabled, set_network_enabled
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()  # Added line


class WeatherData:
    SYNOPTIC_API_ROOT = "https://api.synopticdata.com/v2/"

    STATION_NAME_TO_ID = {
        "vernal": "QV4",
        "dinosaur": "A3822",
        "redwash": "A1633",
        "ouray": "A1622",
        "roosevelt": "QRS",
        "myton": "A1388",
        "whiterocks": "A1386"
    }

    def __init__(self, synoptic_api_token):
        self.synoptic_api_token = synoptic_api_token
        self.set_proj_network_settings()

    @staticmethod
    def set_proj_network_settings(ca_bundle_path: Path | str | bool | None = None) -> None:
        """
        Sets the path to the CA Bundle used by the `curl`
        built into PROJ when PROJ network is enabled.

        Parameters
        ----------
        ca_bundle_path: Path | str | bool | None, optional
            Default is None, which only uses the `certifi` package path as a fallback if
            the environment variables are not set. If a path is passed in, then
            that will be the path used. If it is set to True, then it will default
            to using the path provided, by the `certifi` package. If it is set to False
            or an empty string then it will default to the system settings or environment
            variables.
        """
        env_var_names = ("PROJ_CURL_CA_BUNDLE", "CURL_CA_BUNDLE", "SSL_CERT_FILE")
        if ca_bundle_path is False:
            ca_bundle_path = ""
        elif isinstance(ca_bundle_path, (str, Path)):
            ca_bundle_path = str(ca_bundle_path)
        elif (ca_bundle_path is True) or not any(
                env_var_name in os.environ for env_var_name in env_var_names
        ):
            ca_bundle_path = certifi.where()
        else:
            ca_bundle_path = ""

        _set_context_ca_bundle_path(ca_bundle_path)
        set_network_enabled(True)

    def get_synoptic_timeseries(self, station_ids, variables, start_date, end_date,
                                units="english", timezone="local", include_meta=True):
        vars_string = ','.join(variables)
        stid_string = ','.join(station_ids)

        params = {
            "token": self.synoptic_api_token,
            "stid": stid_string,
            "vars": vars_string,
            "start": start_date,
            "end": end_date,
            "units": units,
            "obtimezone": timezone,
            "include_station_meta": str(int(include_meta))
        }

        api_request_url = self.SYNOPTIC_API_ROOT + "stations/timeseries"
        response = requests.get(api_request_url, params=params)

        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Error {response.status_code}: {response.text}")

    def print_synoptic_air_temp(self, data):
        for station in data.get('STATION', []):
            stid = station.get('STID')
            name = station.get('NAME')
            observations = station.get('OBSERVATIONS', {})
            dates = observations.get('date_time', [])
            air_temps = observations.get('air_temp_set_1', [])

            print(f"Station: {stid} - {name}")
            for dt, temp in zip(dates, air_temps):
                print(f"  Date/Time: {dt}, Air Temperature: {temp} F")
            print()

    def get_herbie_data(self, date, model, product, fxx):
        H = Herbie(date, model=model, product=product, fxx=fxx)
        return H

    def download_herbie_data(self, H, search):
        subset = H.download(search=search)
        print(f"Downloaded Herbie data to: {subset}")
        return subset


def parse_date(date_str):
    # Parse date in the format DDMMYYYY
    if len(date_str) == 8:
        day = date_str[:2]
        month = date_str[2:4]
        year = date_str[4:]
        # Set default time to 1200 (noon), as it's generally a good time for weather data
        return f"{year}{month}{day}1200"
    else:
        raise ValueError("Date must be in the format DDMMYYYY")


def parse_station_names(station_names_str):
    station_names = station_names_str.split(',')
    station_ids = []
    for name in station_names:
        name_lower = name.strip().lower()
        if name_lower in WeatherData.STATION_NAME_TO_ID:
            station_ids.append(WeatherData.STATION_NAME_TO_ID[name_lower])
        else:
            raise ValueError(f"Station name '{name}' not recognized.")
    return station_ids


def main():
    parser = argparse.ArgumentParser(description="Fetch weather data using Synoptic API and Herbie.")
    parser.add_argument('--start', type=str, required=True, help='Start date for data retrieval (e.g., 04091991)')
    parser.add_argument('--end', type=str, help='End date for data retrieval (e.g., 20091991)')
    parser.add_argument('--stations', type=str, help='Comma-separated list of station names (e.g., Vernal,Dinosaur NM)')
    parser.add_argument('--variables', type=str, help='Comma-separated list of variables (e.g., air_temp,dew_point)')
    parser.add_argument('--save_to_json', type=str, help='File path to save output data as JSON')
    parser.add_argument('--save_to_hdf5', type=str, help='File path to save output data as HDF5')
    args = parser.parse_args()

    API_TOKEN = os.getenv('SYNOPTIC_API_TOKEN')
    if not API_TOKEN:
        raise ValueError("API token not found. Please ensure it's set in the .env file.")

    # Default hardcoded station IDs and variables
    station_ids = parse_station_names(args.stations) if args.stations else ["QV4", "A3822", "A1633", "A1622", "QRS",
                                                                            "A1388", "A1386"]
    valid_variables = [
        "air_temp", "dew_point", "relative_humidity", "pressure", "altimeter",
        "wet_bulb", "heat_index", "wind_chill", "wind_speed", "wind_direction",
        "wind_gust", "precip_accum", "precip_rate", "snow_depth",
        "solar_radiation", "visibility", "soil_temp", "soil_moisture"
    ]
    variables = args.variables.split(',') if args.variables else valid_variables
    variables = [var for var in variables if var in valid_variables]

    start_date = parse_date(args.start)
    end_date = parse_date(args.end) if args.end else start_date

    weather = WeatherData(API_TOKEN)

    # Synoptic API data
    synoptic_data = weather.get_synoptic_timeseries(station_ids, variables, start_date, end_date)
    weather.print_synoptic_air_temp(synoptic_data)

    # Generate a unique file name suffix based on the date range
    date_suffix = f"_{start_date}_{end_date}"

    # Save to JSON if requested
    if args.save_to_json:
        json_file_path = args.save_to_json.replace('.json', f"{date_suffix}.json")
        with open(json_file_path, 'w') as json_file:
            json.dump(synoptic_data, json_file, indent=4)
        print(f"Data saved to {json_file_path}")

    # Save to HDF5 if requested
    if args.save_to_hdf5:
        hdf5_file_path = args.save_to_hdf5.replace('.h5', f"{date_suffix}.h5")
        with h5py.File(hdf5_file_path, 'w') as hdf5_file:
            for station in synoptic_data.get('STATION', []):
                station_group = hdf5_file.create_group(station['STID'])
                for key, value in station.items():
                    if isinstance(value, list):
                        station_group.create_dataset(key, data=value)
                    else:
                        station_group.attrs[key] = value
        print(f"Data saved to {hdf5_file_path}")

    # Herbie data (if start and end date are the same)
    if start_date == end_date:
        herbie_obj = weather.get_herbie_data(start_date, model="hrrr", product="sfc", fxx=6)
        herbie_subset = weather.download_herbie_data(herbie_obj, search=":TMP:2 m")


if __name__ == "__main__":
    main()