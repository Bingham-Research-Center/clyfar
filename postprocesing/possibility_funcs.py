"""Functions generating possibility and necessity infomration from FIS outputs, including an "unsure" category.
"""

import numpy as np

def normalize_distribution(values):
    """
    Normalises such that at least one maximum value is 1.0.

    Parameters:
    - values (numpy array): Values to be normalized, between 0 and 1.

    Returns:
    - normalized (numpy array): The normalized values.
    """
    max_value = np.max(values)
    if max_value == 0:
        # Avoid division by zero; return zeros or handle as needed
        # TODO - deal with this elegantly
        raise Exception
        # return np.zeros_like(values)

    normalized = values / max_value
    return normalized

def generate_unsure_possibility(poss_arr):
    """From subnormal possibility distribution, generate "unsure" category."""
    unsure_poss = 1 - np.max(poss_arr)
    return unsure_poss

def compute_necessity_distribution(poss_arr):
    """Compute necessity distribution from possibility distribution.

    Necessity for x in the distribution is 1 - max possibility for not-x.
    """
    necess_arr = np.zeros_like(poss_arr)

    # Necessity is 0 if possibility is less than 1
    # Necessity greater than 0 if possibility equal to 1
    # Then necessity is 1 - max(possibility for not-x)

    # First find indices where possibility is 1
    max_poss_idx = np.where(poss_arr == 1)[0]

    # Calculate necessity for these indices
    for i in max_poss_idx:
        necess_arr[i] = 1 - np.max(np.delete(poss_arr, i))

    return necess_arr



