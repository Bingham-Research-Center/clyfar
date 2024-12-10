"""Configuration for version 0.1 of the FIS (prototype).

This prototype uses four inputs and one output. The inputs are:

*

"""

import numpy as np

import skfuzzy as fuzz
from skfuzzy import control as ctrl

from fis.fis import FIS

### General settings ###



### UNIVERSES OF DISCOURSE ###

# mm
snow_uod = np.arange(0, 750, 5)

# Pascals
mslp_uod = np.arange(1000E2, 1070E2, 0.5E2)

# m/s
wind_uod = np.arange(0, 20, 0.125)

# W/m^2
solar_uod = np.arange(100, 1100, 10)

# ppb
ozone_uod = np.arange(20, 140, 1)

### INPUTS AND OUTPUTS ###
snow = ctrl.Antecedent(snow_uod, 'snow')
mslp = ctrl.Antecedent(mslp_uod, 'mslp')
wind = ctrl.Antecedent(wind_uod, 'wind')
solar = ctrl.Antecedent(solar_uod, 'solar')

ozone = ctrl.Consequent(ozone_uod, 'ozone')

### MEMBERSHIP FUNCTIONS ###
snow['negligible'] = fuzz.sigmf(snow.universe, 70, -0.07)
snow['sufficient'] = fuzz.sigmf(snow.universe, 100, 0.07)

mslp['low'] = fuzz.sigmf(mslp.universe, 1013E2, -0.005)
mslp['average'] = fuzz.gaussmf(mslp.universe, 1029E2, 8E2)
mslp['high'] = fuzz.sigmf(mslp.universe, 1045E2, 0.005)

wind['calm'] = fuzz.sigmf(wind.universe, 2.5, -3.0)
wind['breezy'] = fuzz.sigmf(wind.universe, 2.5, 3.0)

solar['midwinter'] = fuzz.sigmf(solar.universe, 300, -0.03)
solar['winter'] = fuzz.gaussmf(solar.universe, 450, 100)
solar['spring'] = fuzz.gaussmf(solar.universe, 650, 100)
solar['summer'] = fuzz.sigmf(solar.universe, 750, 0.03)

curve_centres = {'background':40, 'moderate':52, 'elevated':67, 'extreme':95}
sigma_vals = {'background':6, 'moderate':5.5, 'elevated':6, 'extreme':10}

ozone['background'] = fuzz.gaussmf(ozone.universe, curve_centres['background'], sigma_vals['background'])
ozone['moderate'] = fuzz.gaussmf(ozone.universe, curve_centres['moderate'], sigma_vals['moderate'])
ozone['elevated'] = fuzz.gaussmf(ozone.universe, curve_centres['elevated'], sigma_vals['elevated'])
ozone['extreme'] = fuzz.gaussmf(ozone.universe, curve_centres['extreme'], sigma_vals['extreme'])

### RULES ###

# Rule 1: Catching cases where ozone cannot build
rule1 = ctrl.Rule((snow['negligible'] | mslp['low'] | wind['breezy']), ozone['background'])

# Rules 2--4: snow sufficient, pressure high, wind calm - now depends on solar insolation
rule2 = ctrl.Rule(snow['sufficient'] & mslp['high'] & wind['calm'] & solar['spring'], ozone['extreme'])
rule3 = ctrl.Rule(snow['sufficient'] & mslp['high'] & wind['calm'] & solar['winter'], ozone['elevated']) # sun weak, but conditions good
rule4 = ctrl.Rule(snow['sufficient'] & mslp['high'] & wind['calm'] & (solar['midwinter'] | solar['summer']), ozone['moderate']) # sun weak/strong, but other conditions good

# Cusp cases (Rules 5 & 6)
rule5 = ctrl.Rule(snow['sufficient'] & mslp['average'] & wind['calm'] & (solar['spring'] | solar['winter']), ozone['elevated']) # maybe moderate
rule6 = ctrl.Rule(snow['sufficient'] & mslp['average'] & wind['calm'] & (solar['midwinter'] | solar['summer']), ozone['moderate']) # maybe background

# if __name__ == '__main__':
# def return_fis():

## Create control system and simulation
ozone_ctrl = ctrl.ControlSystem([rule1, rule2, rule3, rule4, rule5, rule6])
ozone_sim = FIS(ozone_ctrl, ozone)
# return ozone_ctrl, ozone_sim
