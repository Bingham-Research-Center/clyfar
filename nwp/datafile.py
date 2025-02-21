"""Blah"""
import time
from functools import wraps
import requests
from urllib3.exceptions import ReadTimeoutError

import numpy as np

class DataFile:
    def __init__(self, fpath=None):
        self.fpath = fpath


