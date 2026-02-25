# Clyfar v1.0 Readiness Gates
Date updated: 2026-02-25

This checklist is the blocking definition of done for the v1.0 label.

## Gate 1: Snow Edge-Pixel Representation
- Status: In progress
- Requirement:
  - Compare representative GEFS snow against representative observed snow for the deep-dive case (`2025012500`) with lead-wise bias/MAE.
  - Include visual review (time series + error by lead day), not only scalar metrics.
  - Resolution criterion: demonstrable improvement over the current method, with bounded/defensible behavior changes.
- Tooling:
  - `scripts/analyze_snow_edge_case.py` (new in this branch)
- Commands:
  - Preferred case: `python scripts/analyze_snow_edge_case.py --init 2025012500`
  - If local case data is missing: generate run artifacts first, then rerun the command.
  - If Synoptic obs access is unavailable: provide precomputed obs file or use `--allow-no-obs` for forecast-only diagnostics.

## Gate 2: Solar Time/Physics Safety for v1.0
- Status: In progress
- Requirement:
  - Timezone handling is correct and deterministic for US Mountain local-time logic.
  - DST transition handling explicitly validated for Sunday March 8, 2026.
  - Forecast hours beyond 240 use a documented deterministic persistence rule.
  - Behavior is covered by tests.

## Operational Safety (non-blocking unless regressed)
- Keep `run_gefs_clyfar.py` smoke behavior stable.
- Do not break Ffion (`scripts/run_llm_outlook.sh`) workflow assumptions.
- Keep interface-level backward compatibility for existing exports unless explicitly documented.

## Evidence Bundle for v1.0 Decision
- Snow deep-dive figure + CSV/JSON metrics for the canonical case.
- Solar DST/persistence tests and notes.
- Short risk register (what changed, why safe, what is deferred).
- Final checklist update in this file (`Done`/`Deferred` with rationale).
