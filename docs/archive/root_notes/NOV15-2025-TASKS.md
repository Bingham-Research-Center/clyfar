## MSLP Status Snapshot
- Current PRMSL pipeline still returns all-NaNs. Logs show repeated `Herbie download failed… (cannot convert float NaN to integer)` for every forecast hour; parquet outputs (`data/20250125_0600Z/*mslp*.parquet`) confirm NaNs.
- Temporary mitigations: Herbie cache now lives under `data/herbie_cache/` with a shared `cfgrib_indexes/` folder, but the query still uses wildcard `':PRMSL:'` and relies on cfgrib’s best guess.
- Debug prints are in `GEFSData.safe_get_CONUS` to log model/product/member/grib paths when failures happen; remove once the new helper is in place.
- Smoke script defaults to `2025012506` so the problem reproduces quickly.

## New Task Tracker
- Added `docs/herbie_refactor_plan.md` with three phases:
  1. Build a structured Herbie helper + probe script + pygrib fallback.
  2. Replace `do_nwpval_mslp`, drop legacy code, add regression guards/logging.
  3. Update docs/examples (including LaTeX) and note the future `brc-tools` migration.
- Use that checklist as the canonical micro-task list; update it instead of scattering TODOs.

## Outstanding Actions (ordered)
1. Implement `GEFSData.fetch_pressure` using `Herbie.xarray` with explicit `filter_by_keys` (`shortName='prmsl'`, `typeOfLevel='meanSea'`, etc.) plus pygrib fallback.
2. Draft `scripts/check_mslp.py` to exercise the helper for a few `fxx` values; log min/max/NaN counts.
3. Swap `do_nwpval_mslp` over to the new helper; delete the legacy fallback NaN builder and q_str path.
4. Extend smoke output to include pressure p10/p50/p90 and fail if parquet is all NaN.
5. Update `docs/baseline_0_9.md` (and the LaTeX science doc) with the new workflow + canonical command examples; reference eventual `brc-tools` sharing.

## Gotchas / Constraints
- Writing inside `.git/` is blocked (macOS Full Disk Access issue). You’ll need to add/commit locally once permissions are fixed.
- Clearing `~/data/gefs` isn’t enough anymore; the repo cache is `data/herbie_cache`, so delete there between tests if you need fresh downloads.
- Avoid cfgrib auto-index creation outside the cache; the helper must always set `indexpath` to our writable folder.

## Pointers
- Refactor plan: `docs/herbie_refactor_plan.md`
- Current failure evidence: `data/baseline_0_9/logs/smoke_2025012506.log`
- GEFS cache: `data/herbie_cache/gefs/<init>/…`
- MSLP parquet samples: `data/20250125_0600Z/20250125_0600Z_mslp_p0{1,2}_df.parquet`

Bring this summary into the next session to pick up right where we left off.
