"""Class to create a fuzzy inference system (FIS).

This is written from scratch rather than using scikit-fuzzy (skfuzzy).
We want more access to inner parameters.

This is independent of Clyfar version, in general.
"""

import os

import numpy as np
import pandas as pd

class FIS:
    def __init__(self, input_universes, output_universe):
        """Initialise the fuzzy-logic inference system.

        Begin by setting up universes for inputs and outputs.

        Adding variables and rules occur later with methods.

        Args:
            input_universes (dict): The universes of discourse for the input
                variable. Format {'variable_name": np.array}.
            output_universe (np.array): As input_universe but for
                (single) output
        """
        self.input_vrbls = list(input_universes.keys())
        self.output_vrbl = list(output_universe.keys())[0]
        self.vrbls = self.input_vrbls + [self.output_vrbl]

        self.input_universes = input_universes
        self.output_universe = output_universe
        self.universes = {**input_universes, **output_universe}

        # The ruleset, preferable {int(1): rule}, etc (begin with 1)
        self.rules = {}

        # Membership functions for inputs and outputs. {variable: {category: np.array}}
        self.mfs = {v: {} for v in self.vrbls}

        # Pandas dataframe to hold input and output values
        # Initialise with float dtype, but empty rows
        # Set column names from self.input_vrbls
        # Later methods will add defuzzified values of ozone, possibilities etc
        # TODO - isn't  best way to do this; fresh_start should return just df
        self.fresh_start()

    def fresh_start(self):
        """Clear out the FIS dataframe's values for the inputs and outputs.
        """
        # Reset the dataframe to empty
        self.fis_df = pd.DataFrame(columns=self.input_vrbls
                                           + [self.output_vrbl])
        return

    def compute_membership(self, variable, category, value):
        """Also known as fuzzification."""
        return np.interp(value, self.universes[variable],
                         self.mfs[variable][category])

    @staticmethod
    def compute_activation(*memberships):
        return np.fmin(*memberships)

    def generate_mf_cut(self, variable, category, activation_val):
        """Generate the membership function cut for a given value.

        Args:
            variable (str): The variable to cut.
            value (float): The activation to cut the variable at.

        Returns:
            np.ndarray: The membership function for the variable "activated"
                or cut at the value given
        """
        return np.minimum(self.mfs[variable][category], activation_val)

    def add_mf(self, variable, category, mf):
        """Add a membership function to the FIS.

        Args:
            variable (str): The variable to add the membership function to.
            category (str): The category of the variable.
            mf (np.array): The membership function to add.
        """
        self.mfs[variable][category] = mf
        return

    @staticmethod
    def aggregate_activations(*acts):
        return np.fmax(*acts)

    @staticmethod
    def compute_union(*arrs):
        return np.maximum.reduce(*arrs)

    @staticmethod
    def compute_intersection(*arrs):
        return np.minimum.reduce(*arrs)

    @staticmethod
    def defuzzify_percentile(x_uod, y_distr, pc):
        """Defuzzify a distribution using a percentile of area under curve.

        Args:
            x_uod (np.ndarray): Universe of discourse for the x-axis.
            y_distr (np.ndarray): The distribution to defuzzify.
            pc (float): The percentile to use for defuzzification.

        Returns:
            float: The defuzzified value.
        """
        return np.percentile(x_uod, pc, weights=y_distr)


    def set_inputs(self, input_values):
        """Set inputs to FIS run, held until fresh_start() is called or
        inputs overwritten.

        Args:
            inputs (dict): The inputs to the FIS in the
                format {'variable_name': value}

        """
        # for variable_name, value in input_values.items():

        return

    @staticmethod
    def trapmf_from_quintuple(x_uod: np.ndarray, x_left: float, m_lower: float,
                              m_upper: float, x_right: float,
                              h: float = 1.0) -> np.ndarray:

        """Create trapezium from five arguments that describe the shape.

        This version uses explicit x-coordinates instead of slopes, making it more
        intuitive to specify the shape. The parameters define:
        - The support (total range) of the function: [x_left, x_right]
        - The core (plateau) of the function: [m_lower, m_upper]
        - The height of the plateau: h

        Notes:
            Modified from Lawson 2024 pre-print for easier use. Instead of slopes,
            we directly specify the x-coordinates where membership starts and ends.
            The core [m_lower, m_upper] defines where membership reaches its maximum h,
            while [x_left, x_right] defines the total range of non-zero membership.

        We assert that y=0 at the left and right extremes as we do not consider variables where all x
        are constantly possible for a given category.

        Args:
            x_uod (np.ndarray): Universe of discourse for the x-axis
            x_left (float): Leftmost point where membership becomes non-zero
            m_lower (float): Lower boundary of trapezoid plateau (core start)
            m_upper (float): Upper boundary of trapezoid plateau (core end)
            x_right (float): Rightmost point where membership becomes zero
            h (float, optional): Height of trapezoid. Defaults to 1.0

        Returns:
            np.ndarray: Array same shape as x_uod containing membership values
        """
        # Input validation
        assert x_left < m_lower <= m_upper < x_right, ("Must satisfy:"
                                "x_left < m_lower <= m_upper < x_right")
        assert 0 <= h <= 1, "h must be in [0, 1]"

        # Create result array
        result = np.zeros_like(x_uod, dtype=float)

        # Left slope region
        mask_left = (x_left <= x_uod) & (x_uod < m_lower)
        slope_left = h / (m_lower - x_left)  # Calculate slope from points
        result[mask_left] = slope_left * (x_uod[mask_left] - x_left)

        # Plateau region
        mask_plateau = (m_lower <= x_uod) & (x_uod <= m_upper)
        result[mask_plateau] = h

        # Right slope region
        mask_right = (m_upper < x_uod) & (x_uod <= x_right)
        slope_right = -h / (x_right - m_upper)  # Calculate slope from points
        result[mask_right] = h + slope_right * (x_uod[mask_right] - m_upper)

        # All other regions remain 0 by initialization
        return result

    @staticmethod
    def plsmf_from_quadruple(x_uod: np.ndarray, h_left: float, x_left: float,
                             x_right: float, h_right: float,
                             ) -> np.ndarray:
        """Create a piecewise linear signoid-like shape from four arguments.

        Usually both h_left and h_right are in {0, 1} as a transition from one
        state (e.g., True) to another (False). We could also assume that h_left
        and h_right are 0 or 1 and set whether rising slope is True or False, but
        that loses potential future functionality to have non-binary ends.

        Args:
            x_uod (np.array): Universe of discourse for the x-axis.
            h_left (float): Height at left inflection point.
            x_left (float): x-value at left inflection point.
            x_right (float): x-value at right inflection point.
            h_right (float): Height at right inflection point.

        Returns:
            np.ndarray: Array same shape as x_uod containing membership values.
        """
        assert x_left < x_right, "x_left must be less than x_right"
        assert 0 <= h_left <= 1, "h_left must be in [0, 1]"
        assert 0 <= h_right <= 1, "h_right must be in [0, 1]"
        # JRL: I don't think the below is needed because we do interpolation.
        # assert x_left in x_uod, "x_left must be in x_uod"
        # assert x_right in x_uod, "x_right must be in x_uod"

        # Create the piecewise linear function numpy array same size as x_uod
        result = np.zeros_like(x_uod, dtype=float)

        # Masking better for performance and clear "zones"

        # Left constant region
        mask_left = x_uod <= x_left
        result[mask_left] = h_left

        # Middle sloped region, here linear
        mask_middle = (x_left < x_uod) & (x_uod < x_right)
        slope = (h_right - h_left) / (x_right - x_left)
        result[mask_middle] = h_left + slope * (x_uod[mask_middle] - x_left)

        # Right constant region
        mask_right = x_right <= x_uod
        result[mask_right] = h_right

        return result

    def add_rule(self, rule_key, rule):
        """Add a rule to the FIS.

        Usage:
        Rule string similar to skfuzz: OR (|), AND (&), and NOT (~) operators.
            "AND" is np.fmin; "OR" is np.fmax; "NOT" is NOT implemented. Haha!
            "THEN" is "=>" which will split the rule string into two parts.

        Example:
            The following string:



            "z['lv1'] & y['set3'] & (x['cat1'] | x['cat2']) => v['output5']"

            becomes (LHS equals)

            np.fmin(z['lv1'], np.fmin(y['set3'], np.fmax(x['cat1'], x['cat2'])))

        Args:
            rule_key: The key for the rule, e.g., "rule1" or int(2)
            rule (dict): The rule string - see Example

        """
        self.rules[rule_key] = rule
        return

    def hardcoded_rules(self):
        """Just in case we can't see add_rule working, here are my rules hardcoded.

        Fuzzy operators:
            OR (|) is np.fmax
            AND (&) is np.fmin
            (then we won't bother with 'not' yet.)

        # Rule 1: Catching cases where ozone cannot build
        rule1 = (snow['negligible'] | mslp['low'] | wind['breezy']) => ozone['background']

        # Rules: snow sufficient, pressure high, wind calm - depends on insolation
        rule2 = (snow['sufficient'] & mslp['high'] & wind['calm'] & solar['high']
                ) => ozone['extreme']
        rule3 = (snow['sufficient'] & mslp['high'] & wind['calm'] & solar['moderate']
                ) => ozone['elevated'] # sun ok, but conditions good
        rule4 = (snow['sufficient'] & mslp['high'] & wind['calm'] & solar['low']
                ) => ozone['moderate'] # sun weak, but other conditions good

        # Cusp cases
        rule5 = (snow['sufficient'] & mslp['moderate'] & wind['calm'] & solar['high']
                ) => ozone['elevated']
        rule6 = (snow['sufficient'] & mslp['moderate'] & wind['calm'] & solar['moderate']
                ) => ozone['moderate']
        # rule7 = (snow['sufficient'] & mslp['moderate'] & wind['calm'] & solar['low']
                ) => ozone['background']) # Feels like low-to-moderate!

        """
        # Rule 1
        rule1 = np.fmax(
            self.mfs['snow']['negligible'],
            np.fmin(
                self.mfs['mslp']['low'],
                self.mfs['wind']['breezy'])
            )

        return


    @staticmethod
    def convert_rulestring_to_func(rule):
        """Convert a rule string to a function using the ast module.

        Args:
            rule (str): The rule string to convert.

        """
        # Split the rule into LHS and RHS
        try:
            lhs, rhs = rule.split('=>')
        except ValueError:
            raise ValueError("Rule must contain one '=>' for 'LHS implies RHS.' ")

        # Remove white space at start or end
        lhs = lhs.strip()
        rhs = rhs.strip()

