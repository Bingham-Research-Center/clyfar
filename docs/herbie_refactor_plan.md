# Herbie MSLP Refactor Checklist

Tracking micro-tasks for the clean rewrite of the pressure download path.

## Phase 1 – Reliable data access
- [x] Confirm current Herbie/cfgrib versions; document exact dependencies for reproducibility.
  - Verified in the clyfar Python 3.11 environment on 2025-02-14: `herbie-data==2025.11.1`, `cfgrib==0.9.15.1`. Keep these pinned in `requirements.txt` for v0.9.5 release notes.
- [ ] Build a standalone helper (`GEFSData.fetch_pressure`) that calls `Herbie.xarray` with explicit `filter_by_keys` for PRMSL.
- [ ] Add pygrib-based fallback for PRMSL when cfgrib still raises.
- [ ] Create `scripts/check_mslp.py` that exercises the helper for a few forecast hours and reports success/NaN counts.
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
