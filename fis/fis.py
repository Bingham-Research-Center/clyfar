"""Class to create a fuzzy inference system (FIS).

This is written from scratch rather than using scikit-fuzzy (skfuzzy).
We want more access to inner parameters.

This is independent of Clyfar version, in general.

This should be for methods and functions related to fuzzy inference systems
in general, and we import membership functions and rules from each version's
configuration in files like "v0p9.py".
"""

import os
import logging

import numpy as np
import pandas as pd

from skfuzzy import control as ctrl

class FIS:
    def __init__(self,):
        """Initialise the fuzzy-logic inference system.

        Begin by setting up universes for inputs and outputs.

        Adding variables and rules occur later with methods.

        The blank dicts etc will be filled by child classes.

        TODO:
        * Do we put plotting for FIS in this class?
        * Might do fisplots.py for a FISPlots class.
        * Don't need input uods as we will load everything from config file
        """
        # The universes of discourse for each variable
        self.universes = {}

        # The ruleset, preferable {int(1): rule}, etc (begin with 1)
        self.rules = {}

        # Membership functions for inputs and outputs. {variable: {category: np.array}}
        # self.mfs = {v: {} for v in self.vrbls}
        self.mfs = {}

        # Pandas dataframe to hold input and output values
        # Initialise with float dtype, but empty rows
        # Set column names from self.input_vrbls
        # Later methods will add defuzzified values of ozone, possibilities etc

        # self.df = self.create_data_df()

        self.input_vars = list()
        self.output_vars = list()

    def create_control_simulation(self):
        control_system = ctrl.ControlSystem(self.rules)
        simulation = ctrl.ControlSystemSimulation(control_system)
        return control_system, simulation

    def create_data_df(self):
        """Clear out the FIS dataframe's values for the inputs and outputs.

        Usage:
            The dataframe has the day as index (local, 00 LT to 00 LT), with
            input and output variables as columns. These will be progressively
            filled during running the inference.

        """
        return pd.DataFrame(columns=self.input_vars, dtype=float)

    def clear_cache(self):
        """Remove input and output data to set up a new run with same model.

        The data is kept in self.fis_df. Only the values should be removed.
        """
        self.df.loc[:, :] = np.nan
        return

    def compute_membership(self, variable, category, value):
        """Also known as fuzzification."""
        return np.interp(value, self.universes[variable],
                         self.mfs[variable][category])

    @staticmethod
    def alpha_cut(mf: np.ndarray, alpha: float) -> np.ndarray:
        """Clips a membership function at given activation level.

        Args:
            mf: Membership function (values in [0,1])
            alpha: Activation level (in [0,1])
        Returns:
            Clipped membership function
        """
        if alpha is None:
            return np.full_like(mf, 0.0)
        return np.fmin(mf, alpha)

    def add_mf(self, variable: str, category: str, mf: np.ndarray) -> None:
        """Add a membership function to the FIS.

        Args:
            variable: The variable to add the membership function to
            category: The category of the variable
            mf: The membership function to add
        """
        self.mfs[variable][category] = mf

    def clipped_mfs_from_dict(self, vrbl, activation_df: pd.DataFrame
                                ) -> list[np.ndarray]:
        acts = []
        mfs = []
        for cat in self.mfs[vrbl].keys():
            mf = self.mfs[vrbl][cat]
            # This can't be None - find the source
            act = activation_df.loc[cat]['possibility']
            act = 0.0 if not isinstance(act, float) else act
            mfs.append(mf)
            acts.append(act)
        clipped_mf = self.compute_clipped_mfs(mfs, acts)
        return clipped_mf

    @staticmethod
    def compute_clipped_mfs(mfs: list[np.ndarray], activations: list[float]) -> list[np.ndarray]:
        """Compute clipped membership functions for each MF-activation pair.

        Args:
            mfs: List of membership functions
            activations: List of activation levels
        Returns:
            List of clipped membership functions
        """
        return [np.fmin(mf, activation) for mf, activation in zip(mfs, activations)]

    @staticmethod
    def aggregate_maximal(*distributions: np.ndarray) -> np.ndarray:
        """Aggregates distributions using maximum operator.

        Args:
            distributions: Arrays to aggregate
        Returns:
            Maximum across all distributions
        """
        return np.fmax.reduce(distributions)

    @staticmethod
    def combine_minimal(*distributions: np.ndarray) -> np.ndarray:
        """Combines distributions using minimum operator.

        Args:
            distributions: Arrays to combine
        Returns:
            Minimum across all distributions
        """
        return np.fmin.reduce(distributions)

    @staticmethod
    def defuzzify_percentiles(x_uod, y_agg, percentiles=None,
                              do_plot=False, plot_fill=False, save_path=None,
                              print_percentiles=False):
        """Defuzzify the aggregated membership function to specific percentiles.

        TODO: there's maybe a simpler way to do area under curve for piecewise linear..?
        """
        if percentiles is None:
            percentiles = [10, 50, 90]

        method = 2

        if method == 1:
            total_area = np.trapezoid(y_agg, x_uod)
            cumulative_area = np.cumsum((y_agg[:-1] + y_agg[1:]) / 2 * np.diff(x_uod))
            if total_area == 0:
                logging.getLogger(__name__).warning(
                    "Defuzzification skipped due to zero aggregated support")
                return {p: np.nan for p in percentiles}
            cumulative_area_normalized = cumulative_area / total_area

            percentile_results = {}
            for p in percentiles:
                idx = np.where(cumulative_area_normalized >= p / 100.0)[0]
                if idx.size > 0:
                    percentile_results[p] = x_uod[idx[0]]
                else:
                    # percentile_results[f'{p}th percentile'] = x_uod[-1]
                    percentile_results[p] = x_uod[-1]

        elif method == 2:
            percentile_results = {}
            for p in percentiles:
                val_x = FIS.find_percentile_by_area(x_uod, y_agg, p/100)
                percentile_results[p] = val_x

        else:
            raise ValueError("Invalid method")

        if print_percentiles:
            print("Percentiles:")
            for k, v in percentile_results.items():
                print(f"  {k}th: {v:.2f} ppb")

        return percentile_results

    @staticmethod
    def find_percentile_by_area(x: np.ndarray, y: np.ndarray,
                                pc: float,) -> float:
        """Computes x-value corresponding to specified area percentile under piecewise linear curve.

        Assumes y values are bounded [0,1] and curve is piecewise linear. Employs trapezoidal
        integration with linear interpolation for precise threshold determination.

        Args:
            x: Monotonically increasing x-coordinates
            y: Corresponding y-values, bounded [0,1]
            target_percentile: Desired cumulative area fraction (default: 0.9)

        Returns:
            x-coordinate at which cumulative area reaches target_percentile of total area
        """
        # Compute areas of trapezoids between consecutive points
        dx = np.diff(x)
        y_avg = (y[1:] + y[:-1]) / 2
        incremental_areas = dx * y_avg

        # Compute cumulative areas and normalize
        cumulative_areas = np.concatenate(([0], np.cumsum(incremental_areas)))
        total_area = cumulative_areas[-1]
        if total_area == 0:
            logging.getLogger(__name__).warning(
                "Defuzzification skipped due to zero aggregated support")
            return float('nan')

        normalized_areas = cumulative_areas / total_area

        # Find bracketing indices
        idx = np.searchsorted(normalized_areas, pc)
        if idx == 0:
            val_x = x[0]
        else:
            # Linear interpolation between bracketing points
            area_fraction = (pc-normalized_areas[idx-1]) / (
                                normalized_areas[idx]-normalized_areas[idx-1])

            val_x =  x[idx-1] + area_fraction * (x[idx] - x[idx-1])

        # Make this val_x value the nearest integer so we can look up the index
        # in the x_uod array
        val_x = np.rint(val_x)
        return val_x

    def __give_inputs(self, inputs: pd.DataFrame):
        """Set inputs to FIS run, held until fresh_start() is called or
        inputs overwritten.

        Args:
            inputs (pd.DataFrame): The inputs to the FIS. The dataframe has
            rows of datetime index w/ columns of variable names,
            with each row having a value for each variable.

        Returns:
            pd.DataFrame: Void, as we updated the dataframe in-place.

        """
        # Check that the input variables (columns) match class instance
        assert inputs.columns == self.input_vrbls, ("Columns must match "
                                            "input variables.")
        # Put the volues into the class dataframe object
        # This existing fis_df may have other datetime, so raise an
        # error if the indices clash. Otherwise, place the rows
        # where they need to go to maintain index chronological order.
        self.df.update(inputs)

    @staticmethod
    def create_trapz(x_uod: np.ndarray, s_left: float, c_left: float,
                     c_right: float, s_right: float,
                     h_max: float = 1.0,
                     h_min: float = 0.0) -> np.ndarray:
        """Creates an asymmetric trapezoidal membership function.

        Args:
            x_uod: Universe of discourse (x-axis points)
            s_left: Leftmost point of support (where membership begins to rise from h_min)
            c_left: Left point of core (where membership reaches h_max)
            c_right: Right point of core (where membership begins to decrease from h_max)
            s_right: Rightmost point of support (where membership returns to h_min)
            h_max: Maximum height of membership function (default: 1.0)
            h_min: Minimum height of membership function (default: 0.0)

        Returns:
            np.ndarray: Membership function values over x_uod

        Note:
            The function creates a trapezoid with these key regions:
            - Support: Region where membership > h_min, bounded by [s_left, s_right]
            - Core: Region of maximum membership (h_max), bounded by [c_left, c_right]
            - Left slope: Linear increase from s_left to c_left
            - Right slope: Linear decrease from c_right to s_right
        """
        # Initialize output array with minimum height
        y = np.full_like(x_uod, h_min, dtype=float)

        # Core region (maximum membership)
        core_mask = (x_uod >= c_left) & (x_uod <= c_right)
        y[core_mask] = h_max

        # Left slope region
        left_mask = (x_uod >= s_left) & (x_uod < c_left)
        y[left_mask] = h_min + (h_max - h_min) * (
                x_uod[left_mask] - s_left) / (c_left - s_left)

        # Right slope region
        right_mask = (x_uod > c_right) & (x_uod <= s_right)
        y[right_mask] = h_max - (h_max - h_min) * (
                x_uod[right_mask] - c_right) / (s_right - c_right)

        return y


    @staticmethod
    def create_piecewise_linear_sigmoid(x_uod: np.ndarray, h_left: float,
                                        m_left: float, m_right: float,
                                        h_right: float) -> np.ndarray:
        """Creates a piecewise linear sigmoid (monotonic) membership function.

        Args:
            x_uod: Universe of discourse points
            h_left: Height at left inflection point (start of transition)
            m_left: Left inflection point on x-axis
            m_right: Right inflection point on x-axis
            h_right: Height at right inflection point (end of transition)

        Returns:
            Membership values over x_uod

        Note:
            Creates a monotonic function with three regions:
            - Left region: Constant h_left for x < m_left
            - Middle region: Linear transition from h_left to h_right between m_left and m_right
            - Right region: Constant h_right for x > m_right

        Raises:
            ValueError: If m_right <= m_left or h_right == h_left
        """
        if m_right <= m_left:
            raise ValueError("Right point must be greater than left point")
        if h_right == h_left:
            raise ValueError("Heights must differ to create transition")

        width = m_right - m_left
        delta_h = h_right - h_left

        # Initialize with left height
        y = np.full_like(x_uod, h_left, dtype=float)

        # Linear transition region
        mask = (x_uod >= m_left) & (x_uod <= m_right)
        y[mask] = h_left + delta_h * (x_uod[mask] - m_left) / width

        # Right region
        y[x_uod > m_right] = h_right

        return y

    @staticmethod
    def __trapmf_from_quintuple(x_uod: np.ndarray, x_left: float, m_lower: float,
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
    def __plsmf_from_quadruple(x_uod: np.ndarray, h_left: float, x_left: float,
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

    def add_rule(self, rule, rule_number=None,):
        """Add a rule to the FIS.

        The rule should be in the format used by skfuzz.

        Args:
            rule_number: The integer key for the rule (starting at zero!)
            rule (dict): The rule string - see Example

        """
        if rule_number is None:
            rule_number = len(self.rules) + 1
        self.rules[rule_number] = rule
        print(f"There are currently {len(self.rules)} rules in the FIS.")
        return

    def compute_aggregated_distr(self,poss_df, ozone):
        y_list = []
        for ozone_cat in ozone.terms.keys():
            activation = poss_df['possibility'][ozone_cat]
            # clipped_mf = self.compute_activation(
            #             'ozone', ozone_cat, activation)
            clipped_mf = self.alpha_cut(
                        self.mfs['ozone'][ozone_cat], activation)
            y_list.append(clipped_mf)

        # We are missing the information of x-axis locations of these y values.

        y_agg = np.maximum.reduce(y_list)
        return y_agg

    def create_possibility_array(self, sim, fis_ctrl, normalize=False):
        possibility_array = np.array([k.membership_value[sim] for k in
                                        fis_ctrl.terms.values()])
        if normalize:
            print("Normalizing")
            possibility_array = self.do_normalization(possibility_array)
        return possibility_array

    @staticmethod
    def do_normalization(possibility_array):
        # Rescale the possibility array to ensure sup(possibility) = 1
        # Not sure what axis!
        possibility_array_norm = possibility_array / np.max(possibility_array)
        return possibility_array_norm

    def create_possibility_df(self, sim, consequent, category_names, normalize=False):
        possibility_array = self.create_possibility_array(
                                sim, consequent, normalize=normalize)
        df = pd.DataFrame(index=category_names)
        df['possibility'] = possibility_array
        return df
