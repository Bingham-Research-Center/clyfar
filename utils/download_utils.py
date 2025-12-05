"""Helper functions for downloading data from the internet.
"""

import logging
import os
import time
from functools import wraps
import requests
from urllib3.exceptions import ReadTimeoutError

import numpy as np

logger = logging.getLogger(__name__)

# Network errors that are always retryable
_NETWORK_EXCEPTIONS = (
    requests.exceptions.ReadTimeout,
    requests.exceptions.ConnectionError,
    ReadTimeoutError,
)

# File corruption errors - retryable if cache is cleared
_CORRUPTION_EXCEPTIONS = (
    EOFError,  # Truncated GRIB file
)


def _is_retryable_key_error(exc: KeyError) -> bool:
    """
    Check if a KeyError is a retryable "data not ready" error vs a programming bug.

    The 'href' KeyError occurs when Herbie parses an incomplete .idx file
    from NOAA - the GEFS data isn't fully published yet.
    """
    key = exc.args[0] if exc.args else None
    # Log the actual key for debugging (helps catch typos if pattern changes)
    logger.info(f"KeyError encountered: key='{key}' - checking if retryable")

    # Known retryable keys from Herbie/NOAA incomplete index files
    retryable_keys = {'href', 'range'}

    if key in retryable_keys:
        logger.info(f"KeyError '{key}' is retryable (data not ready)")
        return True
    else:
        logger.warning(f"KeyError '{key}' is NOT retryable (possible bug) - will raise")
        return False


def retry_download_backoff(retries=3, backoff_in_seconds=1):
    """Retry a function with exponential backoff. Use as decorator.

    Retries on:
    - Network errors (timeout, connection reset)
    - EOFError (corrupted/truncated cached files)
    - KeyError for 'href'/'range' (GEFS data not fully available yet)

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
                except _NETWORK_EXCEPTIONS as e:
                    if x == retries:
                        raise e
                    sleep = (backoff_in_seconds * 2 ** x +
                             np.random.uniform(0, 1))
                    time.sleep(sleep)
                    x += 1
                    logger.info(f"Network error: {type(e).__name__}. Retry {x}/{retries} after {sleep:.1f}s")
                    print(f"Retry {x} after {sleep:.1f}s sleep (network error)")
                except _CORRUPTION_EXCEPTIONS as e:
                    if x == retries:
                        raise e
                    sleep = (backoff_in_seconds * 2 ** x +
                             np.random.uniform(0, 1))
                    time.sleep(sleep)
                    x += 1
                    logger.warning(f"Corruption error: {type(e).__name__}: {e}. Retry {x}/{retries} after {sleep:.1f}s")
                    print(f"Retry {x} after {sleep:.1f}s sleep (corruption: {type(e).__name__})")
                except KeyError as e:
                    if not _is_retryable_key_error(e):
                        raise  # Re-raise programming bugs immediately
                    if x == retries:
                        raise e
                    sleep = (backoff_in_seconds * 2 ** x +
                             np.random.uniform(0, 1))
                    time.sleep(sleep)
                    x += 1
                    logger.info(f"Data not ready (KeyError). Retry {x}/{retries} after {sleep:.1f}s")
                    print(f"Retry {x} after {sleep:.1f}s sleep (data not ready)")
        return wrapper
    return decorator