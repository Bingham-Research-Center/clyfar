# TODO: Herbie Integration Refactor

**Created:** 2025-11-25
**Priority:** Post-integration

## Problem

The `nwp/gefsdata.py` code has accumulated bandaid fixes:
1. `int(f)` casts for numpy.int64 → timedelta
2. Custom indexpath removal (conflicted with Herbie 2025.11.x)
3. Legacy fallback paths with stale dates
4. Complex retry/lock logic that may not be needed with modern Herbie

## Root Cause

Code was written for older Herbie versions. Instead of updating to use Herbie 2025.11.x properly, we patched around errors.

## Solution

1. Read Herbie 2025.11.x docs and changelog
2. Rewrite GEFS download using modern Herbie patterns:
   - `FastHerbie` for parallel downloads
   - Native xarray integration without custom cfgrib kwargs
   - Remove legacy fallback code
3. Remove `_pressure_index_path`, `_CFGRIB_INDEX_DIR` complexity
4. Use Herbie's built-in retry/caching

## Files to Refactor

- `nwp/gefsdata.py` (primary)
- `nwp/download_funcs.py`
- `preprocessing/representative_nwp_values.py`

## Blocked By

Integration testing must complete first.
