import numpy as np
import pandas as pd
import pytest

from preprocessing.representative_obs import (
    convert_to_local_date,
    daily_station_ozone_mda8,
    do_repval_ozone,
    station_ozone_mda8_windows,
)
from utils.utils import compute_local_daily_max


def hourly_ozone_frame(values_by_station, start="2026-01-02 14:00Z"):
    """Build hourly data beginning at 07:00 fixed MST."""
    rows = []
    index = []
    for station, values in values_by_station.items():
        station_index = pd.date_range(start, periods=len(values), freq="h")
        rows.extend(
            {"stid": station, "ozone_concentration": value}
            for value in values
        )
        index.extend(station_index)
    return pd.DataFrame(rows, index=pd.DatetimeIndex(index))


def test_local_date_is_physical_day_without_next_day_shift():
    index = pd.to_datetime(
        ["2026-01-02 06:30Z", "2026-01-02 07:30Z"], utc=True
    )
    frame = pd.DataFrame({"value": [1.0, 2.0]}, index=index)

    local = convert_to_local_date(frame)

    assert list(local["date"]) == [
        pd.Timestamp("2026-01-01"),
        pd.Timestamp("2026-01-02"),
    ]


def test_local_date_handles_dst_boundary_in_mountain_time():
    index = pd.to_datetime(
        ["2026-03-08 06:30Z", "2026-03-08 07:30Z"], utc=True
    )
    frame = pd.DataFrame({"value": [1.0, 2.0]}, index=index)

    local = convert_to_local_date(frame)

    assert list(local["date"]) == [
        pd.Timestamp("2026-03-07"),
        pd.Timestamp("2026-03-08"),
    ]


def test_mda8_uses_seventeen_start_hour_windows_and_crosses_midnight():
    frame = hourly_ozone_frame({"QRS": [40.0] * 24})

    windows = station_ozone_mda8_windows(frame, ["QRS"])
    day = windows.loc[
        windows["verification_day"].eq(pd.Timestamp("2026-01-02"))
    ]

    assert len(day) == 17
    assert day.iloc[0]["window_start_standard"].hour == 7
    assert day.iloc[-1]["window_start_standard"].hour == 23
    assert day.iloc[-1]["window_end_standard"] == pd.Timestamp(
        "2026-01-03 07:00", tz="-07:00"
    )
    assert day["valid_hour_count"].eq(8).all()


def test_mda8_uses_available_hour_divisor_for_six_or_seven_hours():
    values = [40.0] * 24
    values[2:4] = [np.nan, np.nan]
    frame = hourly_ozone_frame({"QRS": values})

    windows = station_ozone_mda8_windows(frame, ["QRS"])
    first = windows.loc[
        windows["window_start_standard"].eq(
            pd.Timestamp("2026-01-02 07:00", tz="-07:00")
        )
    ].iloc[0]

    assert first["valid_hour_count"] == 6
    assert first["window_valid"]
    assert first["mda8_ppb_unrounded"] == 40.0


def test_fewer_than_six_hours_only_survive_zero_fill_exceedance():
    high = hourly_ozone_frame({"QRS": [120.0] * 5 + [np.nan] * 19})
    low = hourly_ozone_frame({"QRS": [40.0] * 5 + [np.nan] * 19})

    high_first = station_ozone_mda8_windows(high, ["QRS"]).iloc[0]
    low_first = station_ozone_mda8_windows(low, ["QRS"]).iloc[0]

    assert high_first["valid_hour_count"] == 5
    assert high_first["window_validity_reason"] == "zero_fill_exceeds_standard"
    assert high_first["mda8_ppb_unrounded"] == 75.0
    assert not low_first["window_valid"]
    assert pd.isna(low_first["mda8_ppb_unrounded"])


def test_station_day_requires_thirteen_windows_unless_maximum_exceeds_standard():
    complete = hourly_ozone_frame({"QRS": [40.0] * 24})
    incomplete_high = hourly_ozone_frame(
        {"QRS": [120.0] * 5 + [np.nan] * 19}
    )
    incomplete_low = hourly_ozone_frame(
        {"QRS": [40.0] * 5 + [np.nan] * 19}
    )

    complete_day = daily_station_ozone_mda8(complete, ["QRS"]).iloc[0]
    high_day = daily_station_ozone_mda8(incomplete_high, ["QRS"]).iloc[0]
    low_day = daily_station_ozone_mda8(incomplete_low, ["QRS"]).iloc[0]

    assert complete_day["valid_window_count"] == 17
    assert complete_day["daily_validity_reason"] == "thirteen_or_more_windows"
    assert high_day["daily_validity_reason"] == "maximum_exceeds_standard"
    assert high_day["station_mda8_ppb"] == 75.0
    assert not low_day["daily_valid"]
    assert pd.isna(low_day["station_mda8_ppb"])


def test_representative_ozone_is_station_mda8_then_spatial_quantile():
    frame = hourly_ozone_frame(
        {"QRS": [40.9] * 24, "QV4": [50.9] * 24}
    )

    station_daily = daily_station_ozone_mda8(frame, ["QRS", "QV4"])
    station_daily = station_daily.loc[station_daily["daily_valid"]]
    representative = do_repval_ozone(frame, ["QRS", "QV4"])

    assert station_daily["station_mda8_ppb"].tolist() == pytest.approx(
        [40.9, 50.9]
    )
    assert station_daily["station_mda8_epa_truncated_ppb"].tolist() == [
        40.0,
        50.0,
    ]
    assert representative.index.tolist() == [pd.Timestamp("2026-01-02")]
    assert representative.iloc[0] == pytest.approx(50.8)


def test_mda8_retains_qc_and_range_rejection_counts():
    frame = hourly_ozone_frame({"QRS": [40.0] * 24})
    frame["qc_flagged"] = False
    frame.iloc[0, frame.columns.get_loc("qc_flagged")] = True
    frame.iloc[1, frame.columns.get_loc("ozone_concentration")] = 200.0

    first = station_ozone_mda8_windows(frame, ["QRS"]).iloc[0]

    assert first["valid_hour_count"] == 6
    assert first["qc_flagged_count"] == 1
    assert first["range_rejected_count"] == 1


def test_station_mda8_uses_earliest_window_on_tie():
    frame = hourly_ozone_frame({"QRS": [40.0] * 24})

    day = daily_station_ozone_mda8(frame, ["QRS"]).iloc[0]

    assert day["selected_window_start_standard"].hour == 7


def test_mda8_fixed_standard_clock_is_distinct_from_dst_display_clock():
    frame = hourly_ozone_frame(
        {"QRS": [45.0] * 24}, start="2026-03-08 14:00Z"
    )

    windows = station_ozone_mda8_windows(frame, ["QRS"])
    first = windows.loc[
        windows["verification_day"].eq(pd.Timestamp("2026-03-08"))
    ].iloc[0]

    assert first["window_start_standard"].hour == 7
    assert first["window_start_standard"].utcoffset().total_seconds() == -7 * 3600
    assert first["window_start_local"].hour == 8
    assert first["window_start_local"].utcoffset().total_seconds() == -6 * 3600


def test_daily_forecast_peak_carries_one_complete_row():
    index = pd.to_datetime(
        ["2026-01-02 18:00Z", "2026-01-02 21:00Z"], utc=True
    )
    frame = pd.DataFrame(
        {
            "ozone_50pc": [60.0, 55.0],
            "background": [0.2, 1.0],
            "moderate": [0.8, 0.0],
            "elevated": [0.3, 0.0],
            "extreme": [0.0, 0.0],
        },
        index=index,
    )

    daily = compute_local_daily_max(frame)

    assert len(daily) == 1
    assert daily.iloc[0]["ozone_50pc"] == 60.0
    assert daily.iloc[0]["background"] == 0.2
    assert daily.iloc[0]["moderate"] == 0.8
    assert daily.iloc[0]["peak_valid_time_utc"] == index[0]


def test_daily_forecast_peak_uses_earliest_time_on_tie():
    index = pd.to_datetime(
        ["2026-01-02 21:00Z", "2026-01-02 18:00Z"], utc=True
    )
    frame = pd.DataFrame(
        {"ozone_50pc": [60.0, 60.0], "background": [0.9, 0.2]}, index=index
    )

    daily = compute_local_daily_max(frame)

    assert daily.iloc[0]["background"] == 0.2
    assert daily.iloc[0]["peak_valid_time_utc"] == pd.Timestamp(
        "2026-01-02 18:00Z"
    )


def test_forecast_verification_day_does_not_follow_dst_midnight():
    index = pd.to_datetime(
        ["2026-03-09 06:30Z", "2026-03-09 07:30Z"], utc=True
    )
    frame = pd.DataFrame(
        {"ozone_50pc": [55.0, 60.0], "background": [0.8, 0.2]}, index=index
    )

    daily = compute_local_daily_max(frame)

    assert daily.index.tolist() == [
        pd.Timestamp("2026-03-08"),
        pd.Timestamp("2026-03-09"),
    ]
    assert daily.iloc[0]["peak_valid_time_local"].date() == pd.Timestamp(
        "2026-03-09"
    ).date()


def test_daily_forecast_peak_rejects_missing_anchor_column():
    frame = pd.DataFrame(
        {"background": [1.0]},
        index=pd.to_datetime(["2026-01-02 00:00Z"], utc=True),
    )
    with pytest.raises(KeyError, match="anchor column"):
        compute_local_daily_max(frame)
