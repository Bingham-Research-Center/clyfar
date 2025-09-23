import datetime as dt
import numpy as np
import pandas as pd
import pytest

from utils.utils import (
    create_meteogram_fname,
    get_nice_tick_spacing,
    get_valid_forecast_init,
    get_closest_non_nan,
    select_nearest_neighbours,
)


def test_create_meteogram_fname_basic():
    init_t = dt.datetime(2024, 1, 1, 0, 0)
    fname = create_meteogram_fname(init_t, "UB-repr", "ozone", "GEFS")
    assert fname == "meteogram_UB-repr_ozone_20240101-0000_GEFS.png"


def test_get_nice_tick_spacing_prefers_approx_five_ticks():
    spacing = get_nice_tick_spacing(3.2, [1.0, 0.5, 0.2, 0.1])
    assert spacing == 0.5


def test_get_valid_forecast_init_force_datetime_variants():
    forced = dt.datetime(2025, 1, 2, 12, 0, tzinfo=dt.timezone.utc)
    init = get_valid_forecast_init(force_init_dt=forced)
    assert set(init.keys()) == {"utc", "naive", "local", "skipped"}
    assert init["utc"].tzinfo is not None
    assert init["naive"].tzinfo is None


def test_get_closest_non_nan_within_tolerance_and_nan_when_not():
    index = pd.date_range("2024-01-01", periods=5, freq="H")
    df = pd.DataFrame({"x": [np.nan, 2.0, np.nan, 4.0, 5.0]}, index=index)
    t_query = index[2] + pd.Timedelta(minutes=10)  # near between 2 and 3

    # Within 1.5 hours tolerance -> nearest non-NaN is 2.0
    val = get_closest_non_nan(df, "x", t_query, pd.Timedelta(hours=1, minutes=30))
    assert val == 2.0

    # Very small tolerance -> no value qualifies
    val2 = get_closest_non_nan(df, "x", t_query, pd.Timedelta(minutes=1))
    assert np.isnan(val2)


def test_select_nearest_neighbours_respects_max_diff():
    src_idx = pd.date_range("2024-01-01 00:00", periods=4, freq="H")
    tgt_idx = pd.to_datetime(["2024-01-01 00:10", "2024-01-01 02:20"])  # closest: 00:00, 02:00
    src = pd.DataFrame({"y": [1, 2, 3, 4]}, index=src_idx)
    tgt = pd.DataFrame(index=tgt_idx)
    selected = select_nearest_neighbours(src, tgt, max_diff="45min")
    assert list(selected["y"]) == [1, 3]

    # Too strict tolerance should raise
    with pytest.raises(ValueError):
        select_nearest_neighbours(src, tgt, max_diff="5min")

