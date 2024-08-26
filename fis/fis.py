"""Class to create a fuzzy inference system (FIS).

Takes a sckit-fuzzy control system and wraps it in a class to allow visualisation etc
"""

import os

import numpy as np

import skfuzzy as fuzz
from skfuzzy import control as ctrl

class FIS:
    def __init__(self, control_system, ozone_mfs):
        """Initialise the FIS.

        Args:
            control_system (skfuzzy.control.ControlSystem): The control system to wrap.
            ozone_mfs: The membership functions for the ozone output.
        """
        self.ozone_mfs = ozone_mfs
        self.control_system = control_system
        self.simulation = ctrl.ControlSystemSimulation(control_system)

    def generate_crisp_inference(self, inputs):
        """Generate inference from the FIS (e.g., forecast).

        Args:
            inputs (dict): The inputs to the FIS.

        Returns:
            float: The crisp output of the FIS.

        """
        self.set_inputs(inputs)
        self.simulation.compute()
        return self.simulation.output['ozone']

    def set_inputs(self, inputs):
        """Set the inputs to the FIS.

        Note these are overwritten each time, then held in memory. (JRL: I think there's a "cache=False" or similar
        to make it forget/flush values after a compute.)

        Args:
            inputs (dict): The inputs to the FIS.

        """
        for key, value in inputs.items():
            self.simulation.input[key] = value
        return

    def create_possibility_array(self,):
        """Using the current simulation, create an array of the possibility distribution.

        Returns:
            np.array: The possibility distribution of the ozone output.

        """
        possibility_array = np.array([k.membership_value[self.simulation] for k in self.ozone_mfs.terms.values()])
        return possibility_array

    def quick_view_activation(self):
        """Quick view of the activation of the rules, using the scikit-fuzz convenience plotting functions.

        TODO:
        * Create more detailed plotting functions in our own viz module.

        Returns:
            tuple: The figure and axis of the plot.

        """
        fig, ax = self.ozone_mfs.view(sim=self.simulation,figsize=(10, 10), dpi=300)
        return fig, ax
