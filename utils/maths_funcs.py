"""General maths functions.
"""
import os

import numpy as np

def compute_weighted_mean(w: np.ndarray, x: np.ndarray) -> float:
    """Compute the weighted mean of an array.

    Args:
        w (np.ndarray): The weights.
        x (np.ndarray): The values.

    Returns:
        float: The weighted mean.
    """
    w_norm = w / np.sum(w)
    weighted_mean = np.sum(w_norm * x)
    return weighted_mean
