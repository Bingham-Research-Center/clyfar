# Handoff Document - 25 November 2025

## Session Summary

**Branch:** `integration-clyfar-v0.9.5`
**Environment:** `clyfar-nov2025` (Herbie 2025.11.3, numpy 1.26.4)

### What Got Done
- ✅ Clean conda environment (100% conda-forge)
- ✅ MSLP diagnostic test PASSED with direct Herbie call
- ✅ Frontend Plotly charts for forecast visualization
- ✅ `upload_batch.py` for batch JSON upload
- ✅ Canonical `brc-tools/docs/CHPC-REFERENCE.md`
- ✅ Test run completed (3 members, figures generated)

### What's Broken
- ❌ MSLP extraction fails in clyfar code path (NaN for all atmos.5 hours)
- ❌ Multiple bandaid fixes applied instead of proper solution

---

## The MSLP Problem

### Symptoms
```
MSLP fetch failed for f384 (invalid index to scalar variable.); storing NaN
```
- Affects: atmos.5 product (f246-f384, 0.5° resolution)
- Works: atmos.25 product (f000-f240, 0.25° resolution)

### Key Discovery
**Direct Herbie call WORKS:**
```python
from herbie import Herbie
H = Herbie('2025-11-24 00:00', model='gefs', product='atmos.5', member='p01', fxx=360)
ds = H.xarray(':PRMSL:', remove_grib=True)
# SUCCESS: Shape (361, 720), Range 94706-103596 Pa
```

**Clyfar code FAILS** even with same Herbie version because of:
1. Custom `backend_kwargs` with `filter_by_keys`
2. Custom `indexpath` settings (now removed but still failing)
3. Complex retry/lock logic
4. Legacy fallback paths

### Root Cause
The `nwp/gefsdata.py` code was written for older Herbie versions and has accumulated hacks. The custom cfgrib configuration conflicts with Herbie 2025.11.x's internal handling.

---

## Required Fix: Herbie Refactor

**See:** `TODO-HERBIE-REFACTOR.md`

### Approach
1. **Read Herbie 2025.11.x documentation** - understand the modern API
2. **Write minimal MSLP extraction** - just `H.xarray(':PRMSL:')` without custom kwargs
3. **Test against both products** - atmos.25 and atmos.5
4. **Replace `GEFSData` class** - with simpler, modern implementation
5. **Use `FastHerbie`** - for parallel downloads (built-in to Herbie)

### Files to Refactor
```
nwp/gefsdata.py          # Primary - GEFSData class
nwp/download_funcs.py    # Helper functions
preprocessing/representative_nwp_values.py  # MSLP time series
```

### What to Remove
- `_build_pressure_backend_kwargs()` - custom cfgrib config
- `_pressure_index_path()` - custom index directories
- `_CFGRIB_INDEX_DIR` - let Herbie manage indexes
- Complex retry logic - Herbie has built-in retry
- Legacy fallback paths with 2023 dates

---

## Current Test Output

```
/scratch/general/vast/clyfar_test/v0p9/2025112400/
├── *.parquet (3 files - wind, solar, temp, snow, mslp per member)
├── dailymax/
└── 20251124_0000Z_run/run.json

/scratch/general/vast/clyfar_test/figs/2025112400/
├── 20251124_00Z/meteogram_*.png
└── heatmap/*.png
```

---

## To Continue Integration (After MSLP Fix)

1. **Export JSON:** `python export/to_basinwx.py` (needs dailymax data)
2. **Upload:** `python export/upload_batch.py --json-dir <path>`
3. **Akamai:** Pull website branch, create `/public/api/static/forecasts/`
4. **Cron:** Use `scripts/submit_clyfar.sh` for Slurm scheduling

---

## Key Commands

```bash
# CHPC - activate environment
conda activate clyfar-nov2025
export PYTHONPATH="$PYTHONPATH:~/gits/clyfar"

# Quick MSLP test (should work)
python -c "
from herbie import Herbie
H = Herbie('2025-11-24 00:00', model='gefs', product='atmos.5', member='p01', fxx=360)
ds = H.xarray(':PRMSL:', remove_grib=True)
print(f'Shape: {list(ds.data_vars.values())[0].shape}')
"

# Run test
./test_run.sh 2025112400
```

---

## Bandaids Applied (to be removed in refactor)

| File | Change | Why |
|------|--------|-----|
| `nwp/gefsdata.py:70` | `int(f)` cast | numpy.int64 → timedelta |
| `nwp/gefsdata.py:71` | `int(f)` cast | numpy.int64 → Herbie fxx |
| `nwp/gefsdata.py:133` | Removed indexpath | Conflicted with Herbie |
| `nwp/gefsdata.py:376` | Removed indexpath | Conflicted with Herbie |
| `preprocessing/representative_nwp_values.py:497` | `int(fxx)` cast | numpy.int64 |
| `run_gefs_clyfar.py:386` | Warning not error | MSLP NaN non-fatal |

---

## Next Session Priority

1. **Investigate why direct Herbie works but clyfar wrapper doesn't**
   - Compare exact xarray() call parameters
   - Check what `filter_by_keys` does to cfgrib

2. **Write minimal working MSLP extraction**
   - No custom backend_kwargs
   - No custom indexpath
   - Test with atmos.5 f360, f372, f378, f384

3. **Replace GEFSData._fetch_pressure_dataset()**
   - Use the minimal working version
   - Remove pygrib fallback (shouldn't be needed)

4. **Clean up bandaids**
   - Once MSLP works, audit int() casts
   - Remove warning workaround in run_gefs_clyfar.py
