# Clyfar Baseline v0.9.x
Date updated: 2025-11-11

## Scope
- Components: GEFS downloads → masked spatial quantiles (Hazen) → FIS v0p9 → defuzz percentiles → plots.
- Inputs: snow, mslp, wind, solar; ozone as output; temp for plotting only.
- Ensemble: configurable members; smoke tests use small subsets.
- Goal: freeze hotfixes into 0.9.5 before v1.0 refactor.

## Repro (Smoke)
- Env: Python 3.11.9 (conda), `pip install -r requirements.txt`.
- Command: `python run_gefs_clyfar.py -i 2024010100 -n 2 -m 2 -d ./data -f ./figures --testing`.
- Artefacts: `data/<run_id>/*.parquet`, `figures/<run_id>/*.png`.

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

## Notes
- No tagging until hotfix checks pass; target freeze: `v0.9.5`.
- General NWP scripts should live in sibling repo `../brc-tools` to avoid duplication.
