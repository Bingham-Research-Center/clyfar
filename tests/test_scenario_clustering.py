import numpy as np
import pandas as pd

from utils.scenario_clustering import build_clustering_summary


def _build_poss_df(index, background, elevated, extreme):
    background = np.asarray(background, dtype=float)
    elevated = np.asarray(elevated, dtype=float)
    extreme = np.asarray(extreme, dtype=float)
    moderate = np.clip(1.0 - (background + elevated + extreme), 0.0, 1.0)
    return pd.DataFrame(
        {
            "background": background,
            "moderate": moderate,
            "elevated": elevated,
            "extreme": extreme,
        },
        index=index,
    )


def _build_pct_df(index, p50, p90):
    return pd.DataFrame({"p50": p50, "p90": p90}, index=index)


def test_build_clustering_summary_null_first_behavior():
    index = pd.date_range("2026-01-01", periods=15, freq="D")

    member_poss = {
        "clyfar000": _build_poss_df(index, background=0.84, elevated=0.04, extreme=0.01),
        "clyfar001": _build_poss_df(index, background=0.80, elevated=0.05, extreme=0.02),
        "clyfar002": _build_poss_df(index, background=0.76, elevated=0.07, extreme=0.02),
        "clyfar010": _build_poss_df(index, background=0.35, elevated=0.32, extreme=0.12),
        "clyfar011": _build_poss_df(index, background=0.25, elevated=0.40, extreme=0.16),
        "clyfar012": _build_poss_df(index, background=0.12, elevated=0.52, extreme=0.24),
    }

    member_pct = {
        "clyfar000": _build_pct_df(index, p50=np.full(15, 35.0), p90=np.full(15, 45.0)),
        "clyfar001": _build_pct_df(index, p50=np.full(15, 38.0), p90=np.full(15, 48.0)),
        "clyfar002": _build_pct_df(index, p50=np.full(15, 40.0), p90=np.full(15, 50.0)),
        "clyfar010": _build_pct_df(index, p50=np.full(15, 55.0), p90=np.full(15, 70.0)),
        "clyfar011": _build_pct_df(index, p50=np.full(15, 60.0), p90=np.full(15, 78.0)),
        "clyfar012": _build_pct_df(index, p50=np.full(15, 68.0), p90=np.full(15, 88.0)),
    }

    summary = build_clustering_summary(
        norm_init="20260101_0000Z",
        member_poss=member_poss,
        member_percentiles=member_pct,
        weather_data={},
    )

    assert summary["schema_version"] == "1.1"
    assert summary["n_members"] == 6
    assert set(summary["member_assignment"].keys()) == set(member_poss.keys())

    clusters = summary["clusters"]
    ids = {c["id"] for c in clusters}
    assert 0 in ids

    null_cluster = [c for c in clusters if c["id"] == 0][0]
    assert null_cluster["kind"] == "null"
    assert len(null_cluster["members"]) >= 2

    null_high = null_cluster["risk_profile"]["weighted_high"]
    non_null_high = [
        c["risk_profile"]["weighted_high"]
        for c in clusters
        if c["id"] != 0
    ]
    if non_null_high:
        assert null_high < min(non_null_high)


def test_build_clustering_summary_flags_dropped_members_without_percentiles():
    index = pd.date_range("2026-01-01", periods=15, freq="D")

    member_poss = {
        "clyfar000": _build_poss_df(index, background=0.82, elevated=0.05, extreme=0.01),
        "clyfar001": _build_poss_df(index, background=0.30, elevated=0.35, extreme=0.15),
    }
    member_pct = {
        "clyfar000": _build_pct_df(index, p50=np.full(15, 36.0), p90=np.full(15, 46.0)),
    }

    summary = build_clustering_summary(
        norm_init="20260101_0000Z",
        member_poss=member_poss,
        member_percentiles=member_pct,
        weather_data={},
    )

    dropped = summary["quality_flags"]["dropped_members_missing_percentiles"]
    assert dropped == ["clyfar001"]
    assert set(summary["member_assignment"].keys()) == {"clyfar000"}
