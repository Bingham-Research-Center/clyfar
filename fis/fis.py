"""Class to create a fuzzy inference system (FIS).

"""

import os

import numpy as np

class FIS:
    def __init__(self, rules, inputs, outputs):
        self.rules = rules
        self.inputs = inputs
        self.outputs = outputs

    def