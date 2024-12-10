"""Class to create a fuzzy inference system (FIS).

This is written from scratch rather than using scikit-fuzzy (skfuzzy).
We want more access to inner parameters.

This is independent of Clyfar version, in general.

This should be for methods and functions related to fuzzy inference systems
in general, and we import membership functions and rules from each version's
configuration in files like "v1p0.py".
"""

import os

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
    def clip_activate(distr: np.ndarray, activation: float) -> np.ndarray:
        """
        Clips a possibility distribution at given activation level.

        Args:
            distr: Possibility distribution (values in [0,1])
            activation: Alpha-cut level (in [0,1])
        Returns:
            Clipped distribution
        """
        return np.minimum(distr, activation)


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
    def alpha_cut(membership_function: np.ndarray, alpha: float) -> np.ndarray:
        """Implements α-cut operation with NaN-safe behavior for robust inference.
        Particularly suitable for systems where missing values may be encountered.

        This is an activation computation over the x-axis (uod).
        """
        if alpha is None:
            return np.full_like(membership_function, 0.0)
        return np.fmin(membership_function, alpha)

    @staticmethod
    def aggregate_activations(*acts):
        return np.fmax(*acts)

    @staticmethod
    def joining_activations(*memberships: np.ndarray) -> np.ndarray:
        return np.fmin.reduce(memberships)

    @staticmethod
    def compute_union(*arrs):
        return np.maximum.reduce(*arrs)

    @staticmethod
    def compute_intersection(*arrs):
        return np.minimum.reduce(*arrs)

    @staticmethod
    def aggregate_maximal_possibilities(
            *distributions: np.ndarray,
            sequential: bool = False
    ) -> np.ndarray:
        """Aggregates possibility distributions using maximum operator."""
        return (np.fmax.reduce(distributions) if sequential
                else np.fmax(*distributions))

    @staticmethod
    def combine_possibility_measures(
            *distributions: np.ndarray,
            sequential: bool = True
    ) -> np.ndarray:
        """Combines possibility distributions using minimum operator, implementing
        conjunctive fusion. Essential for scenarios requiring simultaneous
        satisfaction of multiple possibility constraints."""
        return (np.fmin.reduce(distributions) if sequential
                else np.fmin(*distributions))


    @staticmethod
    def compute_crisp_union(
            *sets: np.ndarray,
            sequential: bool = True
    ) -> np.ndarray:
        """Performs union operation on crisp sets using maximum, without NaN handling.
        Applicable in classical set operations where NaN handling is not a concern."""
        return (np.maximum.reduce(sets) if sequential
                else np.maximum(*sets))


    @staticmethod
    def compute_crisp_intersection(
            *sets: np.ndarray,
            sequential: bool = True
    ) -> np.ndarray:
        """Performs intersection operation on crisp sets using minimum, without NaN
        handling. Suitable for classical set operations where computational efficiency
        is prioritized over NaN handling."""
        return (np.minimum.reduce(sets) if sequential
                else np.minimum(*sets))


    @staticmethod
    def defuzzify_percentiles(x_uod, y_agg, percentiles=None,
                              do_plot=False, plot_fill=False, save_path=None,
                              print_percentiles=False):
        """Defuzzify the aggregated membership function to specific percentiles.

        TODO: there's maybe a simpler way to do area under curve for piecewise linear..?
        """
        if percentiles is None:
            percentiles = [10, 50, 90]
        total_area = np.trapezoid(y_agg, x_uod)
        cumulative_area = np.cumsum((y_agg[:-1] + y_agg[1:]) / 2 * np.diff(x_uod))
        if total_area == 0:
            # Avoid div. by zero error
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
    def create_trapz(x_uod: np.ndarray, m_left: float, c_left: float,
                            c_right: float, m_right: float,
                            h_max: float = 1.0,
                            h_min: float = 0.0) -> np.ndarray:
        """Generates a generalized trapezoidal membership function with variable height
        boundaries.

        This implementation supports both standard and inverted trapezoidal shapes through
        specification of minimum and maximum height parameters. The function accommodates
        asymmetrical trapezoids through independent specification of left and right core
        distances.

        Terminology Note:
        In fuzzy set literature, there exists a terminological variance between American
        English ("trapezoid") and British English ("trapezium"). This implementation uses
        "trapezoidal" as it is most common in international fuzzy set literature,
        particularly in possibility theory (cf. Dubois and Prade, 1988).

        Mathematical formulation:
        Let x be the input variable. The membership function μ(x) is defined as:

        μ(x) = h_min                                                  for x < m_left - c_left
        μ(x) = h_min + (h_max - h_min)(x - (m_left - c_left))/c_left
                                                          for m_left - c_left ≤ x < m_left
        μ(x) = h_max                                     for m_left ≤ x ≤ m_right
        μ(x) = h_max - (h_max - h_min)(x - m_right)/c_right
                                                    for m_right < x ≤ m_right + c_right
        μ(x) = h_min                                    for x > m_right + c_right

        Args:
            x_uod (np.ndarray): Universe of discourse (x-axis values).
            m_left (float): Left modal value (start of core).
            m_right (float): Right modal value (end of core).
            c_left (float): Left core distance (spread from m_left to left boundary).
            c_right (float): Right core distance (spread from m_right to right boundary).
            h_max (float): Maximum membership value, constrained to [0,1].
                It's most common to have the trapezoid peak at 1.0.
            h_min (float, optional): Minimum membership value. Defaults to 0.0.

        Returns:
            np.ndarray: Membership values μ(x) for the given universe of discourse.
        """
        # Initialize output array with h_min values
        y = np.full_like(x_uod, h_min, dtype=float)

        # Define key x-axis points
        x_left_boundary = m_left - c_left
        x_right_boundary = m_right + c_right

        # Core region (flat top)
        core_mask = (x_uod >= m_left) & (x_uod <= m_right)
        y[core_mask] = h_max

        # Left slope region
        left_mask = (x_uod >= x_left_boundary) & (x_uod < m_left)
        y[left_mask] = h_min + (h_max - h_min) * (
                x_uod[left_mask] - x_left_boundary) / c_left

        # Right slope region
        right_mask = (x_uod > m_right) & (x_uod <= x_right_boundary)
        y[right_mask] = h_max - (h_max - h_min) * (
                x_uod[right_mask] - m_right) / c_right

        return y


    @staticmethod
    def create_piecewise_linear_sigmoid(x_uod: np.ndarray, h_left: float,
                                            m_left: float, m_right: float,
                                            h_right: float) -> np.ndarray:
        """Constructs a piecewise linear approximation of a sigmoid membership function.

        This function implements a trapezoidal-based approximation of a sigmoid curve
        characterized by two critical points (m_left, m_right) that define the transition
        region, and two height parameters (h_left, h_right) that specify the membership
        degrees at these points. The monotonicity of the sigmoid (increasing or decreasing)
        is determined by the relationship between h_left and h_right.

        Mathematical formulation:
        Let width = m_right - m_left and delta_h = h_right - h_left

        When h_right > h_left (increasing):
            mu(x) = h_left                                    for x < m_left
            mu(x) = h_left + delta_h * (x - m_left)/width    for m_left ≤ x ≤ m_right
            mu(x) = h_right                                  for x > m_right

        When h_right < h_left (decreasing):
            mu(x) = h_left                                   for x < m_left
            mu(x) = h_left + delta_h * (x - m_left)/width    for m_left ≤ x ≤ m_right
            mu(x) = h_right                                  for x > m_right

        Args:
            x_uod (np.ndarray): Universe of discourse (x-axis values).
            m_left (float): Left modal point on x-axis marking transition onset.
            m_right (float): Right modal point marking transition completion.
            h_left (float): Membership degree at the left modal point (m_left).
            h_right (float): Membership degree at the right modal point (m_right).

        Returns:
            np.ndarray: Membership values mu(x) for the given universe of discourse.

        Raises:
            ValueError: If m_right <= m_left, violating the monotonicity requirement.
            ValueError: If h_right == h_left, indicating a degenerate case.
        """
        if m_right <= m_left:
            raise ValueError("Right modal point must be strictly greater than left modal point")
        if h_right == h_left:
            raise ValueError("Terminal membership degrees must differ to define a transition")

        width = m_right - m_left
        delta_h = h_right - h_left

        # Initialize with the left boundary value
        y = np.full_like(x_uod, h_left, dtype=float)

        # Compute transition region using a unified formula
        mask = (x_uod >= m_left) & (x_uod <= m_right)
        y[mask] = h_left + delta_h * (x_uod[mask] - m_left) / width

        # Set terminal region
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