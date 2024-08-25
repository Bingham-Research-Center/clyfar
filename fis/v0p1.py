"""Configuration for version 0.1 of the FIS (prototype).

This prototype uses four inputs and one output. The inputs are:

*

"""

import numpy as np

import skfuzzy as fuzz
from skfuzzy import control as ctrl

# Universes of discourses per variable, in metric units

# Snow in mm up to 750 mm (3 foot)
snow_uod = np.arange(0, 750, 5)

# mslp using our stations has a bias/error but whatever
# mslp_uod = np.arange(970, 1040, 1)
mslp_uod = np.arange(1000E2, 1070E2, 0.5E2)

wind_uod = np.arange(0, 20, 0.125)

solar_uod = np.arange(100, 1100, 10)

snow = ctrl.Antecedent(snow_uod, 'snow')
mslp = ctrl.Antecedent(mslp_uod, 'mslp')
wind = ctrl.Antecedent(wind_uod, 'wind')
solar = ctrl.Antecedent(solar_uod, 'solar')

# TODO: solar might combine stations via percentile of all per day, maybe per hour, THEN nzm

# Output variable
ozone = ctrl.Consequent(np.arange(20, 140, 1), 'ozone')