"""
Version 1.0.0 of Clyfar configuration file.

This class encapsulates the configuration for the Clyfar fuzzy inference system.
It organizes configuration details, membership functions, and rules, and provides
methods to access configurations and compute outputs.

TODO:
How much of the configuration goes in the init to attach as attributes versus
defined in the top scope of the file?
"""

import os
from collections.abc import Sequence
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from skfuzzy import control as ctrl

from utils.lookups import Lookup
from fis.fis import FIS

# Geographic and computational constants
snow_stids = ['COOPJENU1', 'COOPFTDU1', 'COOPALMU1', 'COOPDINU1', 'COOPROSU1',
              'COOPVELU1', 'COOPDSNU1', 'COOPOURU1', 'COOPNELU1']
wind_stids = ['DURU1', 'A1622', 'SPMU1', 'QV4', 'WAXU1', 'E8302', 'KVEL', 'QRS', 'MYT5']
solar_stids = ["A1622", "SPMU1", "SFLU1", "E3712", "UTSTV", "USWU1", "MCKU1"]
mslp_stids = ["KVEL",]
ozone_stids = ["QV4", "QRS"]

GEOGRAPHIC_CONSTANTS = {
    'extent': [-110.9, -108.2, 41.3, 39.2],
    'ouray': {'lat': 40.0891, 'lon': -109.6774},
    'elevation_threshold': 2000,
}

# Forecast configuration
FORECAST_CONFIG = {
    'delta_h': 3,  # Time step in forecast series
    'solar_delta_h': 3,  # Higher temporal resolution for solar radiation
    'max_h': {"0p25": 240, "0p5": 384},
    'products': {
        'solar': "atmos.25", 'snow': "atmos.25",
        'mslp': "atmos.25", 'wind': "atmos.25"
    },
    'products_backup': {
        'solar': "atmos.5", 'snow': "atmos.5",
        'mslp': "atmos.5", 'wind': "atmos.5"
    }
}

# Variable metadata
VARIABLE_METADATA = {
    'labels': {
        'solar': 'Solar radiation (W/m^2)',
        'snow': 'Snow depth (cm)',
        'mslp': 'Mean sea level pressure (hPa)',
        'wind': 'Wind speed (m/s)',
        'ozone': 'Ozone concentration (ppb)'
    },
    'station_ids': {
        "snow": snow_stids, "wind": wind_stids,
        "solar": solar_stids, "mslp": mslp_stids,
        "ozone": ozone_stids
    },
    'variable_names': {
        'solar': 'solar_radiation',
        'snow': 'snow_depth',
        'wind': 'wind_speed',
        'mslp': 'sea_level_pressure',
        'ozone': 'ozone_concentration'
    }
}

ozone_cats = {
    "background": "#6CA0DC",
    "moderate": "#FFD700",
    "elevated": "#FF8C00",
    "extreme": "#FF6F61"
}

wind_cats = {
    "calm": "#6CA0DC",
    "breezy": "#FFD700"
}

snow_cats = {
    "negligible": "#6CA0DC",
    "sufficient": "#FFD700"
}

mslp_cats = {
    "low": "#6CA0DC",
    "moderate": "#FFD700",
    "high": "#FF6F61"
}

solar_cats = {
    "low": "#6CA0DC",
    "moderate": "#FFD700",
    "high": "#FF6F61"
}

# Looking into "factory classes"...

class Clyfar(FIS):
    def __init__(self):
        """ Version 1.0.0 of the Clyfar configuration file.

        First creates generic FIS object via inheritance, then adds specific
        configuration details for this version.
        """
        super().__init__()

        # Define category color mappings
        # TODO - move these colour dictionaries, not needed here?
        # Or maybe we customise these depending on variables in version?


        # Define Universes of Discourse (UOD)
        self.snow_uod = np.arange(0, 251, 2)        # Snow in mm up to 250mm
        self.mslp_uod = np.arange(99500, 105010, 50)  # MSLP in Pa
        self.wind_uod = np.arange(0, 15.1, 0.25)    # Wind in m/s
        self.solar_uod = np.arange(100, 805, 5)     # Solar in W/m²
        self.ozone_uod = np.arange(20, 141, 1)      # Ozone in ppb

        # Also hold in self.universes in format {variable: uod}
        self.universes = {
            "snow": self.snow_uod,
            "mslp": self.mslp_uod,
            "wind": self.wind_uod,
            "solar": self.solar_uod,
            "ozone": self.ozone_uod
        }

        # Initialize Antecedents and Consequents
        self.snow = ctrl.Antecedent(self.snow_uod, 'snow')
        self.mslp = ctrl.Antecedent(self.mslp_uod, 'mslp')
        self.wind = ctrl.Antecedent(self.wind_uod, 'wind')
        self.solar = ctrl.Antecedent(self.solar_uod, 'solar')
        self.ozone = ctrl.Consequent(self.ozone_uod, 'ozone')

        # Dictionaries for easy access
        self.input_dict = {
            "snow": self.snow,
            "mslp": self.mslp,
            "wind": self.wind,
            "solar": self.solar
        }
        self.output_dict = {
            "ozone": self.ozone
        }

        self.input_vars = list(self.input_dict.keys())
        self.output_vars = list(self.output_dict.keys())

        # Define Membership Functions and attach to self.inputs
        self.mfs = self._define_membership_functions()

        # Define Rules - (can overwrite the superclass placeholder)
        self.rules = self._define_rules() # dict!

        self.control_system, self.simulation = self.create_control_simulation()

        self.df = self.create_empty_df()

    def create_empty_df(self):
        """The five columns of each variable, with rows as timestamps.

        """
        df = pd.DataFrame(columns=self.input_vars)
        # df = pd.DataFrame(columns=[self.input_vars + self.output_vars])
        return df

    def compute_ozone(self, snow_val, mslp_val, wind_val, solar_val,
                            percentiles: Sequence[int|float]) -> dict:
        """
        Computes the ozone level based on input parameters.

        TODO units may need fixing!

        Args:
            snow_val (float): Snow value in cm.
            mslp_val (float): Mean sea level pressure in hPa.
            wind_val (float): Wind speed in m/s.
            solar_val (float): Solar insolation in W/m^2
            percentiles (list): List of percentiles (float/int) to compute.

        Returns:
            float: Computed ozone level.
        """
        self.simulation.input['snow'] = snow_val
        self.simulation.input['mslp'] = mslp_val
        self.simulation.input['wind'] = wind_val
        self.simulation.input['solar'] = solar_val

        # Perform the fuzzy inference
        self.simulation.compute()

        poss_df = self.create_possibility_df(
            self.simulation, self.ozone,
            ozone_cats.keys(), normalize=False)


        y_agg = self.compute_aggregated_distr(poss_df, self.ozone)
        pc_dict = self.defuzzify_percentiles(self.ozone.universe, y_agg,
                                             percentiles=percentiles)
        pass
        # Need to find indices for this time
        # Does it make the columns automatically?
        # Put inferred values into the dataframe
        # self.df.at[0, 'ozone_10pc'] = pc_dict[10]
        # self.df.at[0, 'ozone_50pc'] = pc_dict[50]
        # self.df.at[0, 'ozone_90pc'] = pc_dict[90]

        return pc_dict

    def _define_membership_functions(self):
        """Defines all membership functions for the fuzzy variables.
        """
        # Snow Membership Functions
        self.snow['negligible'] = self.create_piecewise_linear_sigmoid(
                    self.snow_uod, 1, 60, 90, 0)
        self.snow['sufficient'] = self.create_piecewise_linear_sigmoid(
                    self.snow_uod, 0, 60, 90, 1)

        # Wind Membership Functions
        self.wind['calm'] = self.create_piecewise_linear_sigmoid(
                    self.wind_uod, 1, 1.5, 3.5, 0)
        self.wind['breezy'] = self.create_piecewise_linear_sigmoid(
                    self.wind_uod, 0, 1.5, 3.5, 1)

        # MSLP Membership Functions
        self.mslp['low'] = self.create_piecewise_linear_sigmoid(
                    self.mslp_uod, 1, 101000, 101500, 0)
        self.mslp['moderate'] = self.create_trapz(
                    self.mslp_uod, 101000, 101500, 103000, 103500)
        self.mslp['high'] = self.create_piecewise_linear_sigmoid(
                    self.mslp_uod, 0, 102500, 103500, 1)

        # Solar Membership Functions
        self.solar['low'] = self.create_piecewise_linear_sigmoid(
                    self.solar_uod, 1, 200, 300, 0)
        self.solar['moderate'] = self.create_trapz(
                    self.solar_uod, 200, 300, 500, 700)
        self.solar['high'] = self.create_piecewise_linear_sigmoid(
                    self.solar_uod, 0, 500, 700, 1)

        # Ozone Membership Functions
        self.ozone['background'] = self.create_trapz(
                    self.ozone_uod, 25, 40, 50, 60)
        self.ozone['moderate'] = self.create_trapz(
                    self.ozone_uod, 40, 50, 60, 70)
        self.ozone['elevated'] = self.create_trapz(
                    self.ozone_uod, 50, 60, 75, 90)
        self.ozone['extreme'] = self.create_trapz(
                    self.ozone_uod, 0, 75, 90, 125)

        # Put these in a dictionary as another way to access.
        mfs = {
            "snow": {
                "negligible": self.snow['negligible'].mf,
                "sufficient": self.snow['sufficient'].mf
            },
            "wind": {
                "calm": self.wind['calm'].mf,
                "breezy": self.wind['breezy'].mf
            },
            "mslp": {
                "low": self.mslp['low'].mf,
                "moderate": self.mslp['moderate'].mf,
                "high": self.mslp['high'].mf
            },
            "solar": {
                "low": self.solar['low'].mf,
                "moderate": self.solar['moderate'].mf,
                "high": self.solar['high'].mf
            },
            "ozone": {
                "background": self.ozone['background'].mf,
                "moderate": self.ozone['moderate'].mf,
                "elevated": self.ozone['elevated'].mf,
                "extreme": self.ozone['extreme'].mf
            }}

        return mfs

    def _define_rules(self):
        """Defines all the fuzzy rules."""
        rules = []

        # Rule 1: Ozone cannot build
        rule1 = ctrl.Rule(
            (self.snow['negligible'] | self.mslp['low'] | self.wind['breezy']),
            self.ozone['background']
        )
        rules.append(rule1)

        # Rule 2: Sufficient snow, high pressure, calm wind, high solar -> extreme ozone
        rule2 = ctrl.Rule(
            self.snow['sufficient'] & self.mslp['high'] & self.wind['calm'] & self.solar['high'],
            self.ozone['extreme']
        )
        rules.append(rule2)

        # Rule 3: Sufficient snow, high pressure, calm wind, moderate solar -> elevated ozone
        rule3 = ctrl.Rule(
            self.snow['sufficient'] & self.mslp['high'] & self.wind['calm'] & self.solar['moderate'],
            self.ozone['elevated']
        )
        rules.append(rule3)

        # Rule 4: Sufficient snow, high pressure, calm wind, low solar -> moderate ozone
        rule4 = ctrl.Rule(
            self.snow['sufficient'] & self.mslp['high'] & self.wind['calm'] & self.solar['low'],
            self.ozone['moderate']
        )
        rules.append(rule4)

        # Additional Rules for Early-Season Inversion and Cusp Cases
        # Rule 5: Sufficient snow, moderate pressure, calm wind, high solar -> elevated ozone
        rule5 = ctrl.Rule(
            self.snow['sufficient'] & self.mslp['moderate'] & self.wind['calm'] & self.solar['high'],
            self.ozone['elevated']
        )
        rules.append(rule5)

        # Rule 6: Sufficient snow, moderate pressure, calm wind, moderate solar -> moderate ozone
        rule6 = ctrl.Rule(
            self.snow['sufficient'] & self.mslp['moderate'] & self.wind['calm'] & self.solar['moderate'],
            self.ozone['moderate']
        )
        rules.append(rule6)

        # Uncomment and define additional rules as needed
        # rule7 = ctrl.Rule(
        #     self.snow['sufficient'] & self.mslp['moderate'] & self.wind['calm'] & self.solar['low'],
        #     self.ozone['background']
        # )
        # rules.append(rule7)

        return rules

    def visualize_membership_functions(self):
        """Quicklook plots of membership functions for all fuzzy variables.

        Use the viz.plotting module for better plots... TODO!
        """

        for antecedent in [self.snow, self.mslp, self.wind, self.solar]:
            antecedent.view()
            plt.show()

        self.ozone.view()
        plt.show()

# Example Usage
# if __name__ == "__main__":
    # config = ClyfarConfig()

    # Access category colors
    # ozone_categories = config.get_categories("ozone")
    # print("Ozone Categories:", ozone_categories)

    # Compute ozone level
    # ozone_level = config.compute_ozone(snow_val=50, mslp_val=102000, wind_val=2, solar_val=600)
    # print(f"Computed Ozone Level: {ozone_level} ppb")

    # Visualize membership functions
    # config.visualize_membership_functions()

    # Config.df should show dataframe