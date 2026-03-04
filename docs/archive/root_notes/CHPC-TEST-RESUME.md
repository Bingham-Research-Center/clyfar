# CHPC Test Session - Resume After Compact

**Session Date**: 2025-11-23
**Location**: CHPC notch137 (interactive compute node)
**Status**: Testing Clyfar v0.9.5 integration with real GEFS data

---

## Current State

### Where We Are
- ✅ **4 PRs created** across all repos (clyfar #12, website #107, brc-tools #4, preprint #1)
- ✅ **All repos on** `integration-clyfar-v0.9.5` branch
- ✅ **Local tests passed** (63 JSON files generated, 4 categories correct)
- 🔄 **CHPC testing in progress** - found critical MSLP issue

### Active Session Details
```bash
# Compute node allocation
Node: notch137
Account: lawson-np
Partition: lawson-np
CPUs: 8, Memory: 32G, Time: 1hr

# Environment
Conda: clyfar-v1p0 (Python 3.11.11)
Working dir: ~/gits/clyfar (integration-clyfar-v0.9.5 branch)
Export POLARS_ALLOW_FORKING_THREAD=1
Export PYTHONPATH="$PYTHONPATH:~/gits/clyfar"

# Test command that was running
python ~/gits/clyfar/run_gefs_clyfar.py \
  -i "2025112300" \
  -n "8" \
  -m "3" \
  -d "/scratch/general/vast/clyfar_test/v0p9/2025112300" \
  -f "/scratch/general/vast/clyfar_test/figs/2025112300"
```

---

## Critical Error Encountered

### Error Message
```
ValueError: MSLP dataframe for p01 contains only NaNs; aborting before writing parquet.
```

### What Happened
1. ✅ GEFS data **downloading successfully** from AWS
2. ✅ Snow, wind, solar, temp variables **working**
3. ❌ **MSLP (Mean Sea Level Pressure) extraction FAILING**
4. ⚠️ Code aborts when MSLP column is all NaN

### Diagnostic Output
```
2025-11-23 23:29:31.511 - SpawnPoolWorker-2 - MSLP fetch failed for f354 (invalid index to scalar variable.); storing NaN
2025-11-23 23:29:32.567 - SpawnPoolWorker-2 - MSLP fetch failed for f360 (invalid index to scalar variable.); storing NaN
[... repeats for all forecast hours ...]

Warnings:
- "Ignoring index file... incompatible with GRIB file"
- "Can't read index file... IsADirectoryError"
- "Converting non-nanosecond precision datetime values"
```

### Root Cause (Suspected)
This is the **MSLP unit mismatch** documented in CONTRADICTIONS-REPORT.md:
- Tech report says: Pa (Pascals) - 101,000-103,500 range
- Code expects: hPa (hectopascals) - 1010-1035 range
- **Likely**: GEFS GRIB variable name or extraction method changed

---

## Next Steps to Debug

### 1. Check GRIB Variable Names
```bash
# List available variables in GEFS file
python -c "
from herbie import Herbie
H = Herbie('2025112300', model='gefs', product='pgrb2a', member=1, fxx=6)
print(H.inventory().to_string())
" | grep -i mslp
```

Look for:
- `MSLP` (what code searches for)
- `PRMSL` (primary mean sea level pressure)
- `MSLET` (mean sea level pressure ETA)
- Any pressure variable at MSL

### 2. Inspect MSLP Extraction Code
**File**: `~/gits/clyfar/nwp/download_funcs.py` around line 169

Check:
- Variable name being searched: `search='MSLP'` or `search='PRMSL'`?
- Unit conversion: Pa → hPa (divide by 100)?
- Error handling: `try/except` that's storing NaN?

```bash
# View the relevant code section
sed -n '150,200p' ~/gits/clyfar/nwp/download_funcs.py
```

### 3. Test Direct GRIB Access
```python
import xarray as xr
from herbie import Herbie

H = Herbie('2025112300', model='gefs', product='pgrb2a', member=1, fxx=6)

# Try different variable names
for var in ['MSLP', 'PRMSL', 'MSLET', 'sp']:
    try:
        ds = H.xarray(var)
        print(f"✓ Found {var}:")
        print(f"  Shape: {ds.dims}")
        print(f"  Range: {ds.min().values} to {ds.max().values}")
    except Exception as e:
        print(f"✗ {var}: {e}")
```

### 4. Check Recent GEFS Format Changes
NOAA occasionally updates GRIB2 file structure. Check:
- Herbie GitHub issues: https://github.com/blaylockbk/Herbie/issues
- NCEP announcements for GEFS format changes
- cfgrib compatibility with latest GEFS files

---

## Workaround Options

### Option A: Skip MSLP (Temporary)
Modify `run_gefs_clyfar.py` to allow NaN MSLP and run without pressure variable.
**Risk**: Clyfar predictions may be degraded without MSLP input.

### Option B: Fix Variable Name
Update download code to use correct GRIB variable name (likely `PRMSL` instead of `MSLP`).

### Option C: Rollback GEFS Product
Try older GEFS product format if recent change broke extraction:
```python
product='pgrb2a'  # Current (broken)
product='pgrb2b'  # Alternative
```

---

## Session Context

### PRs Created (All on `integration-clyfar-v0.9.5`)
1. **Clyfar #12**: https://github.com/Bingham-Research-Center/clyfar/pull/12
   - Export module (3 products, 63 files)
   - Slurm script
   - CHPC deployment docs

2. **Website #107**: https://github.com/Bingham-Research-Center/ubair-website/pull/107
   - DATA_MANIFEST.json v1.1.0 (forecast schema)
   - Analytics middleware
   - Deployment guides

3. **brc-tools #4**: https://github.com/Bingham-Research-Center/brc-tools/pull/4
   - Cross-repo coordination docs

4. **Tech Report #1**: https://github.com/Bingham-Research-Center/preprint-clyfar-v0p9/pull/1
   - Contradictions report

### What We've Accomplished
- ✅ Complete export module (test_integration.py ALL PASSING locally)
- ✅ 4 ozone categories correct (background, moderate, elevated, extreme)
- ✅ Slurm submission script created
- ✅ CHPC system info documented (Rocky Linux 8.10)
- ✅ Environment setup verified on CHPC
- ✅ GEFS data accessible and downloading
- ❌ MSLP extraction broken (current blocker)

### What Needs Testing After MSLP Fix
1. ✅ GEFS download (verified working)
2. ⏸️ Clyfar inference (blocked by MSLP)
3. ⏸️ Export to 63 JSON files (blocked)
4. ⏸️ Upload to website (blocked)
5. ⏸️ Full 30-member run (blocked)
6. ⏸️ Production cron setup (blocked)

---

## Files to Check

### MSLP-Related Code
```
~/gits/clyfar/nwp/download_funcs.py (line ~169)
~/gits/clyfar/run_gefs_clyfar.py (MSLP processing)
~/gits/clyfar/fis/v0p9.py (MSLP thresholds: 1010-1035 hPa)
```

### Logs/Output
```
# Current test output in scratch
/scratch/general/vast/clyfar_test/v0p9/2025112300/

# Herbie cache (may have corrupt indexes)
~/gits/clyfar/data/herbie_cache/cfgrib_indexes/
# Consider: rm -rf ~/gits/clyfar/data/herbie_cache/cfgrib_indexes/*
```

### Documentation
```
~/gits/clyfar/CONTRADICTIONS-REPORT.md (MSLP units Pa vs hPa)
~/gits/clyfar/CHPC-SYSTEM-INFO.md (Rocky Linux 8.10 details)
~/gits/clyfar/CHPC_DEPLOYMENT_CHECKLIST.md (full deployment guide)
```

---

## Resume Commands

```bash
# Reconnect to CHPC (if disconnected)
ssh <username>@notchpeak.chpc.utah.edu

# Check if interactive node still allocated
squeue -u $USER

# If still allocated, reconnect
# (session may have died - will need new salloc)

# Reactivate environment
module use "$HOME/MyModules"
module load miniforge3/latest
source "$HOME/software/pkg/miniforge3/bin/activate"
conda activate clyfar-v1p0
export POLARS_ALLOW_FORKING_THREAD=1
export PYTHONPATH="$PYTHONPATH:~/gits/clyfar"
cd ~/gits/clyfar

# Check MSLP variable availability (diagnostic)
python -c "
from herbie import Herbie
H = Herbie('2025112300', model='gefs', product='pgrb2a', member=1, fxx=6)
print('Available variables with MSL or pressure:')
print(H.inventory().to_string())
" | grep -iE 'msl|pres|pmsl'

# Once MSLP fixed, retry test
python ~/gits/clyfar/run_gefs_clyfar.py \
  -i "2025112300" \
  -n "8" \
  -m "3" \
  -d "/scratch/general/vast/clyfar_test/v0p9/2025112300" \
  -f "/scratch/general/vast/clyfar_test/figs/2025112300"
```

---

## Questions for User After Resume

1. Should we investigate MSLP extraction or skip it temporarily?
2. Do you have access to working MSLP extraction from production runs?
3. Has GEFS format changed recently (check existing production logs)?
4. Should we test with older GEFS cycle (e.g., 2025-11-20) to see if it's a recent change?

---

**Status**: Paused at MSLP extraction failure. All setup complete, just need to fix variable extraction.

**Priority**: Debug MSLP extraction before proceeding with export testing.
