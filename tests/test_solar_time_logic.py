import datetime as dt

import pandas as pd
import pytz

from preprocessing.representative_nwp_values import _fill_late_solar_with_persistence
from preprocessing.representative_obs import MOUNTAIN_TIMEZONE, get_solar_noon


def _synthetic_solar_df(init_dt: dt.datetime, max_h: int = 240, delta_h: int = 3) -> pd.DataFrame:
    """Create deterministic solar values keyed to local hour for lookup tests."""
    idx = pd.date_range(init_dt, periods=(max_h // delta_h) + 1, freq=f"{delta_h}h")
    idx_utc = idx.tz_localize("UTC")
    local_hours = idx_utc.tz_convert(MOUNTAIN_TIMEZONE).hour
    values = local_hours.astype(float) * 10.0
    return pd.DataFrame({"sdswrf": values}, index=idx)


def test_fill_late_solar_uses_local_hour_lookup_across_dst():
    init_dt = dt.datetime(2026, 2, 27, 0, 0)
    base = _synthetic_solar_df(init_dt, max_h=240, delta_h=3)

    filled = _fill_late_solar_with_persistence(
        solar_df=base,
        init_dt_naive=init_dt,
        delta_h=3,
        max_h=264,
        local_tz=MOUNTAIN_TIMEZONE,
    )

    # +249h falls after the DST transition (Sunday 2026-03-08), so local-hour
    # mapping should still resolve correctly in America/Denver.
    target_ts = pd.Timestamp(init_dt) + pd.Timedelta(hours=249)
    expected_local_hour = target_ts.tz_localize("UTC").tz_convert(MOUNTAIN_TIMEZONE).hour
    expected_value = float(expected_local_hour) * 10.0

    assert target_ts in filled.index
    assert float(filled.loc[target_ts, "sdswrf"]) == expected_value
    assert int(filled.loc[target_ts, "fxx"]) == 249


def test_get_solar_noon_is_timezone_aware_and_dst_sensitive():
    tz = pytz.timezone(MOUNTAIN_TIMEZONE)

    # Day before and day of DST start in 2026 (Sunday, March 8, 2026).
    noon_before = get_solar_noon(dt.date(2026, 3, 7), tz)
    noon_after = get_solar_noon(dt.date(2026, 3, 8), tz)

    assert noon_before.tzinfo is not None
    assert noon_after.tzinfo is not None
    assert noon_before.utcoffset() != noon_after.utcoffset()
    assert 11 <= noon_before.hour <= 13
    assert 11 <= noon_after.hour <= 13
