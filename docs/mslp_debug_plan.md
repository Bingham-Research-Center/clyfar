# PRMSL Download Investigation Plan (v0.9.5)

Context:
- Pre-refactor runs (e.g., `data/20241207_1200Z/20241207_1200Z_mslp_p01_df.parquet`) contain reasonable pressures (~1018–1036 hPa) confirming the GEFS pipeline produced valid PRMSL in late 2024.
- Tag `v0.9.1` shows `GEFSData.safe_get_CONUS` calling `Herbie.xarray(":PRMSL:", ...)` without custom caches and wrote to Herbie’s default directories. Today’s helper adds repo-local caches, cfgrib `filter_by_keys`, and a pygrib fallback (`nwp/gefsdata.py`), but cfgrib errors (“expected string or bytes-like object, got 'PosixPath'”) plus missing `pygrib` lead to all-NaN parquet files (`data/20250125_0600Z/*mslp*.parquet`).

Objectives:
1. Restore reliable cfgrib reads for PRMSL (structured query, per-file index path).
2. Ensure `pygrib` fallback executes whenever cfgrib/Herbie fails so we never regress to NaNs silently.
3. Provide tooling + docs so operators can quickly validate pressure downloads locally or on Unix servers.

Microtasks (ordered):
1. **Environment parity**
   - Install `pygrib>=2.1.5` in `clyfar-2025`; capture the command + version in `docs/herbie_refactor_plan.md`.
   - Expose a CLI/env flag to toggle `GEFSData.clear_cache` for cold/hot cache testing.
   - Track upstream `herbie-data` releases (see `docs/external_data_references.md`) and upgrade if new cfgrib/PRMSL fixes land; document any version bumps explicitly.
2. **cfgrib index handling**
   - Update `_build_pressure_backend_kwargs` to generate a unique index file per GRIB (e.g., `cfgrib_indexes/<grib-basename>.idx`) instead of pointing to the directory root, preventing the PosixPath error and stale-index warnings.
   - Add debug logging describing the resolved index path and filter keys.
3. **pygrib fallback validation**
   - Confirm fallback runs end-to-end by deleting cfgrib indexes, forcing a failure, and checking `scripts/check_mslp.py` output (min/max stats should still appear).
   - Serialize a short troubleshooting section (what errors mean, how to clean caches) in `docs/baseline_0_9.md`.
4. **Baseline comparison**
   - Spin up a clean worktree at `v0.9.1`, run the new `scripts/check_mslp.py` there, and document the request parameters/logs for the same init time (2025012506). Use the diff to reason about regressions.
5. **Automation + guards**
   - Update `do_nwpval_mslp` to call `fetch_pressure`, emit quantile diagnostics (p10/p50/p90), and fail fast if parquet outputs are all NaN.
   - Extend smoke tests with PRMSL stats; integrate into CI once available.

Supporting references:
- External inventories and Herbie examples: `docs/external_data_references.md`.
- Active checklist: `docs/herbie_refactor_plan.md`.
