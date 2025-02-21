"""Helper functions for downloading data from the internet.
"""

import os
import time
from functools import wraps
import requests
from urllib3.exceptions import ReadTimeoutError

import numpy as np

def retry_download_backoff(retries=3, backoff_in_seconds=1):
    """Retry a function with exponential backoff. Use as decorator.

    Args:
        retries (int): Number of retries.
        backoff_in_seconds (int): Initial backoff time in seconds.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            x = 0
            while True:
                try:
                    return func(*args, **kwargs)
                except (requests.exceptions.ReadTimeout,
                        requests.exceptions.ConnectionError,
                        ReadTimeoutError) as e:
                    if x == retries:
                        raise e
                    sleep = (backoff_in_seconds * 2 ** x +
                             np.random.uniform(0, 1))
                    time.sleep(sleep)
                    x += 1
                    print(f"Retry {x} after {sleep:.1f}s sleep")
        return wrapper
    return decorator