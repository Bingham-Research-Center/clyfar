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
        # Strict-background members should be the only members in cluster 0.
        "clyfar000": _build_poss_df(index, background=1.0, elevated=0.0, extreme=0.0),
        "clyfar001": _build_poss_df(index, background=1.0, elevated=0.0, extreme=0.0),
        # Non-background members (moderate and/or elevated) must not land in cluster 0.
        "clyfar010": _build_poss_df(index, background=0.65, elevated=0.05, extreme=0.00),
        "clyfar011": _build_poss_df(index, background=0.55, elevated=0.18, extreme=0.02),
        "clyfar012": _build_poss_df(index, background=0.42, elevated=0.30, extreme=0.08),
    }

    member_pct = {
        "clyfar000": _build_pct_df(index, p50=np.full(15, 34.0), p90=np.full(15, 44.0)),
        "clyfar001": _build_pct_df(index, p50=np.full(15, 36.0), p90=np.full(15, 46.0)),
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

    assert summary["schema_version"] == "1.2"
    assert summary["n_members"] == 5
    assert set(summary["member_assignment"].keys()) == set(member_poss.keys())

    cluster_by_id = {c["id"]: c for c in summary["clusters"]}
    assert 0 in cluster_by_id

    null_cluster = cluster_by_id[0]
    assert null_cluster["kind"] == "null"
    assert set(null_cluster["members"]) == {"clyfar000", "clyfar001"}

    # All non-background members must be assigned to a non-null cluster.
    for member in ("clyfar010", "clyfar011", "clyfar012"):
        assert summary["member_assignment"][member] != 0

    assert summary["quality_flags"]["null_fallback_applied"] is False
    assert summary["quality_flags"]["strict_null_members"] == 2


def test_build_clustering_summary_uses_adaptive_active_window():
    index = pd.date_range("2026-01-01", periods=15, freq="D")

    # Two strict-background members.
    bg = np.ones(15)
    member_poss = {
        "clyfar000": _build_poss_df(index, background=bg, elevated=np.zeros(15), extreme=np.zeros(15)),
        "clyfar001": _build_poss_df(index, background=bg, elevated=np.zeros(15), extreme=np.zeros(15)),
    }

    # Two scenario members with non-background signal only on last two days.
    b2 = np.ones(15)
    b2[-2:] = [0.20, 0.25]
    e2 = np.zeros(15)
    e2[-2:] = [0.15, 0.10]
    member_poss["clyfar010"] = _build_poss_df(index, background=b2, elevated=e2, extreme=np.zeros(15))

    b3 = np.ones(15)
    b3[-2:] = [0.10, 0.30]
    e3 = np.zeros(15)
    e3[-2:] = [0.20, 0.05]
    x3 = np.zeros(15)
    x3[-2:] = [0.05, 0.00]
    member_poss["clyfar011"] = _build_poss_df(index, background=b3, elevated=e3, extreme=x3)

    member_pct = {
        "clyfar000": _build_pct_df(index, p50=np.full(15, 35.0), p90=np.full(15, 45.0)),
        "clyfar001": _build_pct_df(index, p50=np.full(15, 36.0), p90=np.full(15, 46.0)),
        "clyfar010": _build_pct_df(index, p50=np.full(15, 52.0), p90=np.full(15, 68.0)),
        "clyfar011": _build_pct_df(index, p50=np.full(15, 54.0), p90=np.full(15, 70.0)),
    }

    summary = build_clustering_summary(
        norm_init="20260101_0000Z",
        member_poss=member_poss,
        member_percentiles=member_pct,
        weather_data={},
    )

    # Non-background signal appears only on the last two days.
    assert summary["quality_flags"]["active_window_days"] == 2
    assert set(
        c["id"] for c in summary["clusters"]
    ) >= {0}
    assert set(summary["clusters"][0]["members"]) == {"clyfar000", "clyfar001"}
    assert summary["member_assignment"]["clyfar010"] != 0
    assert summary["member_assignment"]["clyfar011"] != 0


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
