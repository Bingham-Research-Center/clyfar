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

        Args:
            inputs (dict): The inputs to the FIS.

        """
        for key, value in inputs.items():
            self.simulation.input[key] = value
        return

    def create_possibility_array(self,):
        possibility_array = np.array([k.membership_value[self.simulation] for k in self.ozone_mfs.terms.values()])
        return possibility_array
