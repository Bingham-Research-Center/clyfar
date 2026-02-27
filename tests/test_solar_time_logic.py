import datetime as dt

import numpy as np
import pandas as pd
import pytz

from preprocessing.representative_nwp_values import (
    LOCAL_SOLAR_TIMEZONE,
    _fill_late_solar_with_persistence,
)
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


def test_fill_late_solar_uses_anchor_median_per_local_hour():
    init_dt = dt.datetime(2026, 2, 27, 0, 0)
    base = _synthetic_solar_df(init_dt, max_h=240, delta_h=3)

    # Distort one sample so expected post-240h value must still be the local-hour
    # median, not simply a copied terminal value.
    first_idx = base.index[0]
    base.loc[first_idx, "sdswrf"] = -999.0

    target_ts = pd.Timestamp(init_dt) + pd.Timedelta(hours=255)
    target_local_hour = target_ts.tz_localize("UTC").tz_convert(LOCAL_SOLAR_TIMEZONE).hour

    idx_utc = pd.DatetimeIndex(base.index).tz_localize("UTC")
    fxx = np.round(
        (idx_utc - pd.Timestamp(init_dt, tz="UTC")).total_seconds() / 3600.0
    ).astype(int)
    anchor = base.loc[fxx <= 240, "sdswrf"]
    anchor_hours = idx_utc[fxx <= 240].tz_convert(LOCAL_SOLAR_TIMEZONE).hour
    expected_value = float(anchor.groupby(anchor_hours).median().loc[target_local_hour])

    filled = _fill_late_solar_with_persistence(
        solar_df=base,
        init_dt_naive=init_dt,
        delta_h=3,
        max_h=264,
        local_tz=LOCAL_SOLAR_TIMEZONE,
    )

    assert float(filled.loc[target_ts, "sdswrf"]) == expected_value


def test_fill_late_solar_uses_nearest_hour_when_target_hour_missing():
    init_dt = dt.datetime(2026, 2, 27, 0, 0)
    base = _synthetic_solar_df(init_dt, max_h=240, delta_h=3)
    target_ts = pd.Timestamp(init_dt) + pd.Timedelta(hours=249)
    target_local_hour = target_ts.tz_localize("UTC").tz_convert(LOCAL_SOLAR_TIMEZONE).hour

    idx_utc = pd.DatetimeIndex(base.index).tz_localize("UTC")
    fxx = np.round(
        (idx_utc - pd.Timestamp(init_dt, tz="UTC")).total_seconds() / 3600.0
    ).astype(int)
    target_hour_mask = (fxx <= 240) & (
        idx_utc.tz_convert(LOCAL_SOLAR_TIMEZONE).hour == target_local_hour
    )

    sparse = base.copy()
    sparse.loc[sparse.index[target_hour_mask], "sdswrf"] = np.nan
    anchor_df = sparse.loc[(fxx <= 240), ["sdswrf"]].copy()
    anchor_df["hour"] = idx_utc[fxx <= 240].tz_convert(LOCAL_SOLAR_TIMEZONE).hour
    grouped = anchor_df.dropna(subset=["sdswrf"]).groupby("hour")["sdswrf"].median()
    available_hours = sorted(int(h) for h in grouped.index.tolist())
    nearest_hour = min(
        available_hours,
        key=lambda h: min((h - target_local_hour) % 24, (target_local_hour - h) % 24),
    )
    expected_value = float(grouped.loc[nearest_hour])

    filled = _fill_late_solar_with_persistence(
        solar_df=sparse,
        init_dt_naive=init_dt,
        delta_h=3,
        max_h=264,
        local_tz=LOCAL_SOLAR_TIMEZONE,
    )

    assert float(filled.loc[target_ts, "sdswrf"]) == expected_value
    assert int(filled.loc[target_ts, "fxx"]) == 249


def test_fill_late_solar_dst_transition_does_not_collapse_to_single_value():
    init_dt = dt.datetime(2026, 2, 25, 18, 0)
    base = _synthetic_solar_df(init_dt, max_h=240, delta_h=3)

    filled = _fill_late_solar_with_persistence(
        solar_df=base,
        init_dt_naive=init_dt,
        delta_h=3,
        max_h=384,
        local_tz=LOCAL_SOLAR_TIMEZONE,
    )

    # After DST starts (2026-03-08), long-lead samples are 6-hourly.
    # They should map to nearest local-hour anchors, not collapse to one
    # anchor-wide median value.
    sample_hours = [258, 264, 270, 276]
    sample_values = [
        float(filled.loc[pd.Timestamp(init_dt) + pd.Timedelta(hours=h), "sdswrf"])
        for h in sample_hours
    ]
    assert len(set(sample_values)) > 1


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
