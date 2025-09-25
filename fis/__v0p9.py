"""Version 0.9.0 of Clyfar configuration file.

This will be imported by the FIS class to create the control system.
"""
import os

import numpy as np
from skfuzzy import control as ctrl

from utils.lookups import (
        Lookup, snow_stids, wind_stids, solar_stids,
        mslp_stids, ozone_stids,
)

from fis.fis import FIS

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

# Snow in mm up to 250mm (0.82 ft; 9.84 in) and anything more is clipped to the max
snow_uod = np.arange(0, 251, 2)

# This is just valid for KVEL
mslp_uod = np.arange(995E2, 1050.1E2, 0.5E2)

# Wind has sigmoid. m/s
wind_uod = np.arange(0, 15.1, 0.25)

# Solar
# solar_uod = np.arange(100, 1105, 5)
solar_uod = np.arange(100, 805, 5)

# Ozone - the output
ozone_uod = np.arange(20, 141, 1)

snow = ctrl.Antecedent(snow_uod, 'snow')
mslp = ctrl.Antecedent(mslp_uod, 'mslp')
wind = ctrl.Antecedent(wind_uod, 'wind')
solar = ctrl.Antecedent(solar_uod, 'solar')
input_dict = {"snow": snow, "mslp": mslp, "wind": wind, "solar": solar}

ozone = ctrl.Consequent(ozone_uod, 'ozone')
output_dict = {"ozone": ozone}

clyfar = FIS(input_dict, output_dict)

### MEMBERSHIP FUNCTIONS ###
snow['negligible'] = clyfar.create_piecewise_linear_sigmoid(
                            snow_uod, 1, 60, 90, 0)
snow['sufficient'] = clyfar.create_piecewise_linear_sigmoid(
                            snow_uod, 0, 60, 90, 1)

# TODO - plot these to check all is well 
wind['calm'] = clyfar.create_piecewise_linear_sigmoid(
                wind_uod, 1, 1.5, 3.5, 0)
wind['breezy'] = clyfar.create_piecewise_linear_sigmoid(
                wind_uod, 0, 1.5, 3.5, 1)

mslp['low'] = clyfar.create_piecewise_linear_sigmoid(
                mslp_uod, 1, 1010E2, 1015E2, 0)
mslp['moderate'] = clyfar.create_trapz(mslp_uod, 1010E2, 1015E2,
                                       1030E2, 1035E2, )
mslp['high'] = clyfar.create_piecewise_linear_sigmoid(
                mslp_uod, 0, 1025E2, 1035E2, 1)

solar['low'] = clyfar.create_piecewise_linear_sigmoid(
                solar_uod, 1, 200, 300, 0)
solar['moderate'] = clyfar.create_trapz(
                solar_uod, 200, 300, 500, 700)
solar['high'] = clyfar.create_piecewise_linear_sigmoid(
                solar_uod, 0, 500, 700, 1)

ozone['background'] = clyfar.create_trapz(ozone_uod, 25,
                                          40, 50, 60)
ozone['moderate'] = clyfar.create_trapz(ozone_uod, 40, 50, 60, 70)
ozone['elevated'] = clyfar.create_trapz(ozone_uod, 50, 60, 75, 90)
ozone['extreme'] = clyfar.create_trapz(ozone_uod,
                                       0, 75, 90, 125)

### RULESET ####
# Rule 1: Catching cases where ozone cannot build
rule1 = ctrl.Rule((snow['negligible'] | mslp['low'] | wind['breezy']), ozone['background'])

# Rules: snow sufficient, pressure high, wind calm - now depends on solar insolation
rule2 = ctrl.Rule(snow['sufficient'] & mslp['high'] & wind['calm'] & solar['high'], ozone['extreme'])
rule3 = ctrl.Rule(snow['sufficient'] & mslp['high'] & wind['calm'] & solar['moderate'], ozone['elevated']) # sun ok, but conditions good
rule4 = ctrl.Rule(snow['sufficient'] & mslp['high'] & wind['calm'] & solar['low'], ozone['moderate']) # sun weak, but other conditions good

# Another rule needed for early-season inversion with lack of storm/interruption so it builds - 2013/2014
# Memory of days into inversion or previous day etc. Build up to "steady state". Seth has draft of paper. Days into inversion?
# Correlate with NOx?!
# What if output was inversion strength?
# This then feeds into a model using "how strong", "how long", etc to predict ozone build-up

# Could consider a rule with a single use of a new variable that "tips the balance" in a cusp or extreme case
# Maybe soil temp/summer average, percent of max insolation, previous O3/NOx etc

# Cusp cases
rule5 = ctrl.Rule(snow['sufficient'] & mslp['moderate'] & wind['calm'] & solar['high'], ozone['elevated'])
rule6 = ctrl.Rule(snow['sufficient'] & mslp['moderate'] & wind['calm'] & solar['moderate'], ozone['moderate'])
# rule7 = ctrl.Rule(snow['sufficient'] & mslp['moderate'] & wind['calm'] & solar['low'], ozone['background']) # Feels like low-to-moderate!
# TODO - look at a lower trapz for cusp-ish wind and elevated ozone?
