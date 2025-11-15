# Clyfar Baseline v0.9.x
Date updated: 2025-11-11

## Scope
- Components: GEFS downloads → masked spatial quantiles (Hazen) → FIS v0p9 → defuzz percentiles → plots.
- Inputs: snow, mslp, wind, solar; ozone as output; temp for plotting only.
- Ensemble: configurable members; smoke tests use small subsets.
- Goal: freeze hotfixes into 0.9.5 before v1.0 refactor.

## Repro (Smoke)
- Env: Python 3.11.9 (Miniforge `clyfar-2025` env), `pip install -r requirements.txt`.
- Command: `python run_gefs_clyfar.py -i 2024010100 -n 2 -m 2 -d ./data -f ./figures --testing` (or `scripts/run_smoke.sh 2024010100`).
- Artefacts: `data/20240101_0000Z/*.parquet`, `figures/20240101_00Z/*.png`.
- Git SHA (baseline build): `83a2298`.
- Log file: `data/baseline_0_9/logs/smoke_2024010100.log`.
- Run metadata lives in `data/baseline_0_9/<run_id>/run.json` (see Logging section).

## Repro (Regression sample)
- Command template: `python run_gefs_clyfar.py -i <YYYYMMDDHH> -n 8 -m 10 -d ./data -f ./figures --log-fis`.
- Coverage: run at least three inits (`2024010100`, `2024021500`, `2024030500`) to span inversion, storm, clear regimes.
- Store outputs under `data/baseline_0_9/<YYYYMMDDHH>/` and `figures_archive/v0_9/<YYYYMMDDHH>/`.

## Inputs and Units
- Snow: GEFS `sde` converted m → mm; label “mm”.
- MSLP: GEFS `prmsl` in Pa; label “Pa”.
- Wind: 10 m speed (m/s).
- Solar: DSWRF (W/m^2).
- Ozone: ppb (defuzzified percentiles 10/50/90).

## Data Flow
- Download GEFS (0p25 to 240h, 0p5 beyond; skip duplicate 240h at 0p5).
- Create elevation‑based masks per resolution; broadcast to grids.
- Compute masked spatial quantiles (Hazen) → timeseries per variable.
- Feed Clyfar v0p9; aggregate/clipped MFs → defuzz percentiles.
- Save parquet + plots (meteogram, possibility, heatmaps).

## Validation Checklist
- High‑snowfall regression: confirm masked quantiles behave (no edge artefacts).
- Mask orientation and broadcasting verified for 0p25/0p5.
- 0p25→0p5 stitching: no duplicated/missing hours.
- UOD guard: warn/clip values outside FIS domains.
- See: `docs/v0p9_testing_checklist.md`.

## Sync With Report
- Record code commit and LaTeX commit/Overleaf version here.
- LaTeX repo: `/Users/johnlawson/Documents/GitHub/preprint-clyfar-v0p9`.
- External refs: `docs/EXTERNAL_RESOURCES.md`.
- Section to update per release:
  - `Code SHA:` `TODO_SHA`
  - `Report SHA/tag:` `TODO_report_ref`
  - `Constraints file:` `constraints/baseline-0.9.txt`

## Logging & Artefact Map
- Smoke run outputs: `data/baseline_0_9/smoke_<YYYYMMDDHH>/` (parquet) + `figures_archive/v0_9/smoke_<YYYYMMDDHH>/`.
- Regression outputs: `data/baseline_0_9/<init>/` + `figures_archive/v0_9/<init>/`.
- Logs: `data/baseline_0_9/logs/<init>.log` (stdout/stderr) and `performance_log.txt` (global timings).
- Metadata: each run writes `run.json` with git SHA, CLI args, env hash, and timestamp.
- Automation: `scripts/run_smoke.sh` wraps the smoke CLI (defaults to init `2024010100`, `NCPUS=2`, `NMEMBERS=2`) and mirrors log lines into `performance_log.txt`.

## Notes
- No tagging until hotfix checks pass; target freeze: `v0.9.5`.
- General NWP scripts should live in sibling repo `../brc-tools` to avoid duplication.
