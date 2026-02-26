# Clyfar v1.0 Risk Register
Date updated: 2026-02-25

This register tracks pre-v1.0 risks discovered during `release/v1.0-prep`.

## High
| ID | Risk | Evidence | Status | Action |
|---|---|---|---|---|
| R1 | Snow science gate not yet closed | Canonical deep-dive case (`2025012500`) data not found locally during this pass; script/tooling now exists but case evidence still pending. | Open | Run `scripts/analyze_snow_edge_case.py --init 2025012500` once case artifacts exist; review visual + MAE/bias outputs before v1.0 label. |
| R2 | Solar late-horizon behavior previously under-specified | Prior logic/notes left >+240h behavior ambiguous and easy to misread as naive-hour or daily-max persistence. | Mitigated | Deterministic local-hour persistence implemented in `preprocessing/representative_nwp_values.py` (median by `America/Denver` local hour from valid `<=240h` anchors, with anchor-median fallback); DST-aware checks added in `tests/test_solar_time_logic.py`. |

## Medium
| ID | Risk | Evidence | Status | Action |
|---|---|---|---|---|
| R3 | Observation dependency volatility | In this environment, Synoptic client call path reported missing `stations_metadata` attribute during deep-dive script run. | Open | Keep `--obs-file` path in deep-dive script for offline reproducibility; validate Synoptic package/API compatibility in operational env before final snow gate decision. |
| R4 | Local validation tooling gap | `pytest` command and `python -m pytest` are unavailable in this shell environment. | Open | Install pytest in active env for full unit-test execution before release decision; continue compile + smoke checks meanwhile. |
| R5 | Timezone naming inconsistency | Legacy code still contains some `US/Mountain` usage outside updated solar-noon/persistence paths. | Open | Normalize remaining timezone usage to `America/Denver` in a follow-up cleanup patch (non-behavioral where possible). |

## Low
| ID | Risk | Evidence | Status | Action |
|---|---|---|---|---|
| R6 | Guidance drift for top-level agent docs | `AGENT-INDEX.md` and `CLAUDE.md` were stale/conflicting with current operational context. | Closed | Removed both and made `AGENTS.md` canonical. |

## Release Gate Notes
- v1.0 remains blocked until R1 (snow gate) and solar gate evidence in `docs/v1_0_readiness.md` are both closed.
- This register should be updated with commit SHAs and artifact paths as each risk closes.
