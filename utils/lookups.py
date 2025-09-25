"""Lookup tables and dictionaries for geography, variables, etc
"""
# Clyfar version 0.9.0 (pre-release, no bugfixes in testing yet)
snow_stids = ['COOPJENU1', 'COOPFTDU1', 'COOPALMU1', 'COOPDINU1', 'COOPROSU1',
              'COOPVELU1', 'COOPDSNU1', 'COOPOURU1', 'COOPNELU1']
wind_stids = ['DURU1', 'A1622', 'SPMU1', 'QV4', 'WAXU1', 'E8302', 'KVEL',
                'QRS', 'MYT5']
solar_stids = ["A1622", "SPMU1", "SFLU1", "E3712", "UTSTV", "USWU1", "MCKU1"]
mslp_stids = ["KVEL",]
ozone_stids = ["QV4", "QRS", "UBCSP",]
temp_stids = ['A1622', 'UINU1','KVEL', 'USWU1', 'BLAU1', 'KU69', 'UBCSP']

# Elevation for masking NWP data as "low level"
lowhigh_elev_split = 1850

obs_vars = [
    "wind_speed",
    "wind_direction",
    "air_temp",
    "dew_point_temperature",
    "pressure",
    "snow_depth",
    "solar_radiation",
    "altimeter",
    "soil_temp",
    "sea_level_pressure",
    "snow_accum",
    "ceiling",
    "soil_temp_ir",
    "snow_smoothed",
    "snow_accum_manual",
    "snow_water_equiv",
    "net_radiation_sw",
    "sonic_air_temp",
    "sonic_vertical_vel",
    "vertical_heat_flux",
    "outgoing_radiation_sw",
    "PM_25_concentration",
    "ozone_concentration",
    "derived_aerosol_boundary_layer_depth",
    "NOx_concentration",
    "PM_10_concentration",
]

##############################################
# Things common to all versions of Clyfar

lat_lon = {
        "Vernal": (40.4555,-109.5287),
        "Duchesne":(40.1633,-110.4029),
        "Ouray":(40.0891,-109.6774),
        "Dragon":(39.78549,-109.07315),
        "Rock Creek Ranch":(39.53777,-110.03689),
        "Kings Peak":(40.7764,-110.3728),
}

elevations = {
        "Ouray":1425,
        "Vernal":1622,
        "Split Mtn":2294,
        "Kings Pk":4123,
}



# STATIONS USED FOR REPRESENTATIVE OBSERVATIONS - version 0.9.0


"""
Helper function that looks up synonyms for, say, a weather variable
like snow. This could be "sde", "snow", "snow_depth", "Snow Depth (m)".
This should be an unordered linked between adjacent terms.

The strings are:
* "array_name": The name of the array accessed via xarray
* "label": The pretty label for the variable in plots
* "mf_name": The name of the variable in Clyfar membership functions
* "gefs_query": The key used to access the variable in GEFS data
* "synoptic": The name of the variable in Synoptic Weather obs
"""
class Lookup:
    def __init__(self):
        """Find keys and values for loading GEFS (and some obs) data.

        Usage:
            from utils.lookups import Lookup

            # ...
            lookup = Lookup()
            result = lookup.find_vrbl_keys('sde')
            # ...

        Attributes:
            self.string_dict (dict): Dictionary of synonym keys for variables.
        """
        self.string_dict = {
            "snow": {'array_name': 'sde', 'label': 'Snow depth (cm)',
                     'mf_name': 'snow', 'gefs_query': ':SNOD:', 'synoptic': 'snow_depth'},
            "mslp": {'array_name': 'prmsl', 'label': 'Mean sea level pressure (hPa)',
                     'mf_name': 'mslp', 'gefs_query': ':PRMSL:', 'synoptic': 'sea_level_pressure'},
            "solar": {'array_name': 'sdswrf', 'label': 'Solar radiation (W/m^2)',
                      'mf_name': 'solar', 'gefs_query': ':DSWRF:', 'synoptic': 'solar_radiation'},
            "wind": {'array_name': 'si10', 'label': 'Wind speed (m/s)',
                     'mf_name': 'wind', 'gefs_query': "GRD:10 m above", 'synoptic': 'wind_speed'},
            "ozone": {'label': 'Ozone concentration (ppb)', 'mf_name': 'ozone',
                      'synoptic': 'ozone_concentration', },
            "temp": {'array_name': 't2m', 'label': 'Temperature (C)',
                        # 'mf_name': 'temp',
                        'gefs_query': "TMP:2 m above",
                        'synoptic': 'temperature'},
        }

    def find_vrbl_keys(self, value):
        """Find the dictionary of keys for a given variable.

        Args:
            value (str): The variable to look up.

        Returns:
            dict: The dictionary of keys for the variable.
        """
        for key, val in self.string_dict.items():
            if value in val.values():
                return self.string_dict[key]
        return None

    def get_key(self,vrbl, _type):
        return self.string_dict[vrbl][_type]
