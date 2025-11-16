# Herbie MSLP Refactor Checklist

Tracking micro-tasks for the clean rewrite of the pressure download path.

## Phase 1 – Reliable data access
- [x] Confirm current Herbie/cfgrib versions; document exact dependencies for reproducibility.
  - Verified in the clyfar Python 3.11 environment on 2025-02-14: `herbie-data==2025.11.1`, `cfgrib==0.9.15.1`. Keep these pinned in `requirements.txt` for v0.9.5 release notes.
- [x] Build a standalone helper (`GEFSData.fetch_pressure`) that calls `Herbie.xarray` with explicit `filter_by_keys` for PRMSL.
  - `nwp/gefsdata.py` now exposes `fetch_pressure`, which locks per forecast, constrains `Herbie.xarray` with `shortName='prmsl'/typeOfLevel='meanSea'`, and crops to the UB domain.
- [x] Add pygrib-based fallback for PRMSL when cfgrib still raises.
  - When cfgrib parsing blows up, `fetch_pressure` re-downloads the GRIB and uses `pygrib` to extract PRMSL before deleting cached artifacts (pygrib is now added to `requirements.txt`).
- [x] Create `scripts/check_mslp.py` that exercises the helper for a few forecast hours and reports success/NaN counts.
  - New CLI script prints per-hour min/max/NaN diagnostics (in hPa) so we can smoke-test `fetch_pressure` without running the full workflow.
- [ ] Ensure the helper writes/reads from the repo-local `data/herbie_cache` and shared cfgrib index directory only.

## Phase 2 – Pipeline integration
- [ ] Replace `do_nwpval_mslp` to use the new helper instead of `get_latlon_timeseries_df`.
- [ ] Remove legacy PRMSL-specific code branches (fallback NaN dataset creation, string queries).
- [ ] Update smoke test logging to include pressure diagnostics (min/median/p90).
- [ ] Add a regression guard that fails the run if the stored MSLP parquet is all NaN.

## Phase 3 – Documentation & Examples
- [ ] Document the new workflow in `docs/baseline_0_9.md` (parameters, cache paths, troubleshooting).
- [ ] Add a short “Herbie API Cheatsheet” with the exact structured calls we use (keep under `docs/` for local lookup).
- [ ] Capture canonical command examples (e.g., how to run `scripts/check_mslp.py` and a smoke test) for future agents.
- [ ] Cross-reference planned `brc-tools` sharing so the helper can be ported later.
- [ ] Sync any science-facing LaTeX docs with the refreshed download description.
