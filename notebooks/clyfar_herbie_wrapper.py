import argparse
from herbie import Herbie
from datetime import datetime
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from skfuzzy import control as ctrl
import skfuzzy as fuzz

# Class to simplify working with Herbie data
class HerbieWrapper:
    def __init__(self, date, model='hrrr', product='sfc', fxx=0):
        self.herbie = Herbie(date, model=model, product=product, fxx=fxx)

    def __getattr__(self, attr):
        return getattr(self.herbie, attr)

    def download_and_read(self, variable):
        try:
            self.herbie.download(variable)
            return self.herbie.xarray(variable)
        except Exception as e:
            print(f"Error downloading or reading {variable}: {e}")
            return None

    def plot_variable(self, variable):
        # Plot the data if it's valid
        data = self.download_and_read(variable)
        if data is not None and 'lon' in data.dims and 'lat' in data.dims:
            plt.figure(figsize=(10, 6))
            plt.contourf(data.lon, data.lat, data.values, cmap='viridis')
            plt.colorbar(label=f'{variable}')
            plt.title(f'{variable} on {self.herbie.date}')
            plt.xlabel('Longitude')
            plt.ylabel('Latitude')
            plt.show()
        else:
            print(f"Cannot plot {variable}: data is not 2D or missing coordinates.")


def setup_fuzzy_logic():
    # Set up the fuzzy logic system
    snow = ctrl.Antecedent(np.arange(0, 750, 5), 'snow')
    mslp = ctrl.Antecedent(np.arange(1000E2, 1070E2, 0.5E2), 'mslp')
    wind = ctrl.Antecedent(np.arange(0, 20, 0.125), 'wind')
    solar = ctrl.Antecedent(np.arange(100, 1100, 10), 'solar')
    ozone = ctrl.Consequent(np.arange(20, 140, 1), 'ozone')

    # Define membership functions for inputs and outputs
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
    ozone['background'] = fuzz.gaussmf(ozone.universe, 40, 6)
    ozone['moderate'] = fuzz.gaussmf(ozone.universe, 52, 5.5)
    ozone['elevated'] = fuzz.gaussmf(ozone.universe, 67, 6)
    ozone['extreme'] = fuzz.gaussmf(ozone.universe, 95, 10)

    # Create rules to connect inputs to outputs
    rule1 = ctrl.Rule((snow['negligible'] | mslp['low'] | wind['breezy']), ozone['background'])
    rule2 = ctrl.Rule(snow['sufficient'] & mslp['high'] & wind['calm'] & solar['spring'], ozone['extreme'])
    rule3 = ctrl.Rule(snow['sufficient'] & mslp['high'] & wind['calm'] & solar['winter'], ozone['elevated'])
    rule4 = ctrl.Rule(snow['sufficient'] & mslp['high'] & wind['calm'] & (solar['midwinter'] | solar['summer']),
                      ozone['moderate'])
    rule5 = ctrl.Rule(snow['sufficient'] & mslp['average'] & wind['calm'] & (solar['spring'] | solar['winter']),
                      ozone['elevated'])
    rule6 = ctrl.Rule(snow['sufficient'] & mslp['average'] & wind['calm'] & (solar['midwinter'] | solar['summer']),
                      ozone['moderate'])

    # Set up the control system simulation
    ozone_ctrl = ctrl.ControlSystem([rule1, rule2, rule3, rule4, rule5, rule6])
    ozone_simulation = ctrl.ControlSystemSimulation(ozone_ctrl)
    return ozone_simulation, ozone


def main(date, model, product, fxx):
    # Initialize the wrapper and plot a variable to test
    herbie_wrapper = HerbieWrapper(date=date, model=model, product=product, fxx=fxx)
    herbie_wrapper.plot_variable('TMP:2 m')

    # Set up fuzzy logic
    ozone_simulation, ozone = setup_fuzzy_logic()

    # Read necessary variables for the simulation
    pres = herbie_wrapper.download_and_read('PRES:sfc')
    wind = herbie_wrapper.download_and_read('WIND:10 m')
    snow = herbie_wrapper.download_and_read('SNOD:sfc')
    solar = herbie_wrapper.download_and_read('DSWRF:sfc')

    # Check if data is available before running simulation
    if pres is not None:
        ozone_simulation.input['mslp'] = pres.mean().values
    else:
        print("MSLP data not available, skipping simulation.")
        return

    if wind is not None:
        ozone_simulation.input['wind'] = wind.mean().values
    else:
        print("Wind data not available, skipping simulation.")
        return

    if snow is not None:
        ozone_simulation.input['snow'] = snow.mean().values
    else:
        print("Snow data not available, skipping simulation.")
        return

    if solar is not None:
        ozone_simulation.input['solar'] = solar.mean().values
    else:
        print("Solar data not available, skipping simulation.")
        return

    # Run the fuzzy logic simulation
    ozone_simulation.compute()
    print("Predicted Ozone Level:", ozone_simulation.output['ozone'])


if __name__ == "__main__":
    # Handle command-line arguments
    parser = argparse.ArgumentParser(description='Run Herbie and Fuzzy Logic Integration')
    parser.add_argument('--date', type=str, required=True, help='Date in YYYY-MM-DD format')
    parser.add_argument('--model', type=str, default='hrrr', help='Weather model to use (default: hrrr)')
    parser.add_argument('--product', type=str, default='sfc', help='Product type (default: sfc)')
    parser.add_argument('--fxx', type=int, default=0, help='Forecast hour (default: 0)')

    args = parser.parse_args()

    # Convert date input to a datetime object
    try:
        date = datetime.strptime(args.date, '%Y-%m-%d')
    except ValueError:
        print("Invalid date format. Please use YYYY-MM-DD.")
        exit(1)

    # Run the main function with provided arguments
    main(date, args.model, args.product, args.fxx)