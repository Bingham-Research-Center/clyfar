"""Lookup tables and dictionaries for geography, variables, etc
"""


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



# STATIONS USED FOR REPRESENTATIVE OBSERVATIONS - version 1.0.0


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
                      'synoptic': 'ozone_concentration', }
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