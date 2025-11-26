# Claude Handoff - 26 Nov 2025 ~09:00 UTC

## Session Summary
**20+ hour MSLP bug RESOLVED.** Pipeline now fully operational.

## What Was Fixed (This Session)

### Root Causes Found & Fixed
1. **Scalar time indexing** - `ds.time.values[0]` failed when `ndim=0`
2. **Wrong valid_time** - Used `ds.time` (init time) instead of `init_dt + fxx`
3. **Over-engineered Herbie wrappers** - Deleted ~130 lines of broken `filter_by_keys`, `backend_kwargs`, pygrib fallback
4. **Timestamp mismatch** - MSLP 6-hourly vs other vars 3-hourly (used `method='nearest'`)
5. **Plotting edge case** - Empty `forecast_transition` array

### Commits (branch: `integration-clyfar-v0.9.5`)
- `8be86f6` - Simplify MSLP/PRMSL fetch - trust Herbie defaults
- `a37e94e` - Fix scalar time indexing bug
- `faf337e` - Guard empty forecast_transition in plot
- `5a1c667` - Use nearest MSLP value for timestamp alignment
- `92c1118` - Use init_dt + fxx for valid_time (CRITICAL FIX)

### Key Files Modified
- `nwp/gefsdata.py` - Simplified `_fetch_pressure_dataset()`, removed dead code
- `preprocessing/representative_nwp_values.py` - Fixed valid_time calculation
- `nwp/download_funcs.py` - Removed broken `_CFGRIB_INDEX_DIR` reference
- `viz/plotting.py` - Guarded empty array access
- `run_gefs_clyfar.py` - Fixed MSLP timestamp lookup
- `scripts/test_mslp_pipeline.py` - NEW: standalone debug test

## Current State
- **Branch:** `integration-clyfar-v0.9.5`
- **Environment:** `clyfar-nov2025` (Herbie 2025.11.3)
- **Tests passing:** Full pipeline completes, MSLP has 105 unique values
- **CHPC:** User has `lawson-np` partition with high resources

## Test Commands
```bash
# Activate
conda activate clyfar-nov2025
cd ~/gits/clyfar
export PYTHONPATH="$PYTHONPATH:$(pwd)"

# Quick MSLP test
python scripts/test_mslp_pipeline.py

# Full run
salloc -n 32 -N 1 -t 2:00:00 -A lawson-np -p lawson-np
python run_gefs_clyfar.py -i 2025112600 -n 16 -m 10 \
  -d /scratch/general/vast/clyfar_test/v0p9 \
  -f /scratch/general/vast/clyfar_test/figs
```

## Output Locations
- Parquet: `/scratch/general/vast/clyfar_test/v0p9/YYYYMMDDHH/`
- Figures: `/scratch/general/vast/clyfar_test/figs/YYYYMMDDHH/`
- Meteograms: `.../20251124_00Z/meteogram_*.png`
- Heatmaps: `.../heatmap/*.png`

## Known Behaviors (Not Bugs)
- "Defuzzification skipped due to zero aggregated support" - Normal when no ozone rules fire (no snow, wrong season)
- "UOD clip: mslp=994.5 outside [995,1050]" - Valid clipping for extreme low pressure

## Next Steps (User's "Grand Plan")
User wants to proceed with broader integration/deployment. Suggested areas:
1. Merge `integration-clyfar-v0.9.5` to main
2. Set up operational cron on CHPC
3. Export to basinwx.com website
4. Documentation cleanup

## Critical Learnings
- **Trust Herbie defaults** - Over-specifying `filter_by_keys` breaks cfgrib
- **Herbie `ds.time` is init time, not valid time** - Compute valid_time as `init_dt + fxx`
- **Always set PYTHONPATH** when running scripts: `export PYTHONPATH="$PYTHONPATH:$(pwd)"`

## Config Reference
```python
# fis/v0p9.py
FORECAST_CONFIG = {
    'delta_h': 3,
    'max_h': {"0p25": 240, "0p5": 384},
}

# MSLP UOD range: 995-1050.5 hPa
```
