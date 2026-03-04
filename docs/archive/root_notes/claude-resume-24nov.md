# Claude Resume - November 24, 2025

**Session:** CHPC Clyfar v0.9.5 Integration Testing
**Status:** BLOCKED - MSLP extraction failing
**Branch:** `integration-clyfar-v0.9.5`
**Location:** CHPC notchpeak (Rocky Linux 8.10)

---

## Critical Blocker: MSLP Extraction Failure

### Symptoms
```
MSLP fetch failed for f360-f384 (invalid index to scalar variable.); storing NaN
ValueError: MSLP dataframe for p01 contains only NaNs; aborting before writing parquet.
```

### Pattern
- ✅ **Works:** atmos.25 product (f000-f240, 0.25° resolution)
- ❌ **Fails:** atmos.5 product (f246-f384, 0.5° resolution)
- Error: "invalid index to scalar variable" from cfgrib
- Warning: "incompatible index file" but raw GRIB read also fails

### Code Location
- `nwp/gefsdata.py:252-307` - PRMSL extraction via cfgrib
- `preprocessing/representative_nwp_values.py:460-520` - MSLP time series collection

### Root Cause (Suspected)
1. GEFS atmos.5 format changed (PRMSL variable structure different?)
2. cfgrib version incompatible with current atmos.5 files
3. Dimension mismatch (scalar vs array) in atmos.5 PRMSL data

---

## Attempted Fixes (All Failed)

1. **Cleared cfgrib index cache**
   ```bash
   rm -rf ~/gits/clyfar/data/herbie_cache/cfgrib_indexes/*
   ```
   Result: Indexes regenerate, still fail

2. **Disabled custom indexpath**
   - File: `nwp/gefsdata.py` line 376
   - Changed: `"indexpath": str(index_path),` → commented out
   - Result: Uses cfgrib default, still fails

3. **Updated environment packages**
   - Created `clyfar-dec2025` with herbie 2025.6.0, cfgrib 0.9.15
   - Result: MSLP issue persists (environment-related, not version-related)

---

## Next Debugging Steps

### 1. Test pygrib Fallback (HIGH PRIORITY)
The code has a pygrib fallback path (line 284) that triggers after cfgrib fails twice.

**Check:** Is pygrib being tried? Does it work?

**Test:**
```python
# On CHPC, test direct pygrib access
import pygrib
from herbie import Herbie

H = Herbie('2025112300', model='gefs', product='atmos.5', member='p01', fxx=360)
grib_path = H.download()

with pygrib.open(grib_path) as grib_obj:
    msg = grib_obj.select(shortName="prmsl", typeOfLevel="meanSea")[0]
    print(f"Found PRMSL: {msg.values.shape}, {msg.values.min()}-{msg.values.max()}")
```

### 2. Verify PRMSL Variable Exists
```bash
# Check what's actually in atmos.5 files
python -c "
from herbie import Herbie
H = Herbie('2025112300', model='gefs', product='atmos.5', member='p01', fxx=360)
print(H.inventory().to_string())
" | grep -i prmsl
```

### 3. Try Alternative Solutions
- **Option A:** Skip atmos.5 hours (limit forecast to 240 hours)
- **Option B:** Use atmos.25 product for all hours (if available past f240)
- **Option C:** Downgrade cfgrib to older version
- **Option D:** Force pygrib-only (disable cfgrib path)

---

## Environment Status

### Working Environment: `clyfar-dec2025`
**Created via:** Run-crash-install cycle (messy but functional)

**Key Packages:**
- Python 3.11.10
- numpy 1.26.4 (intentionally < 2.0 to avoid breaking changes)
- herbie-data 2025.6.0
- cfgrib 0.9.15.0
- pygrib 2.1.5

**Discovered Missing Dependencies:**
- synopticpy (initially had WRONG version: 0.4.0 vs 3.0.2)
- astral
- matplotlib
- pytz
- pygrib
- psutil

**TODO (Not Blocking):**
1. Systematic dependency audit (scan all imports)
2. Rebuild clean environment from complete requirements
3. Resolve conda/mamba/pip mixing

---

## Test Command

```bash
# On CHPC compute node (lawson-np partition)
conda activate clyfar-dec2025
export PYTHONPATH="$PYTHONPATH:~/gits/clyfar"
export POLARS_ALLOW_FORKING_THREAD=1

python ~/gits/clyfar/run_gefs_clyfar.py \
  -i "2025112300" \
  -n "8" \
  -m "3" \
  -d "/scratch/general/vast/clyfar_test/v0p9/2025112300" \
  -f "/scratch/general/vast/clyfar_test/figs/2025112300"
```

**Fails at:** MSLP processing for member p01, f360-f384

---

## PR Status (All Blocked)

1. **clyfar #12** - Export module, Slurm script, CHPC docs
2. **website #107** - DATA_MANIFEST v1.1.0, analytics middleware
3. **brc-tools #4** - Cross-repo coordination docs
4. **preprint #1** - Contradictions report

**All on branch:** `integration-clyfar-v0.9.5`
**Blocked by:** CHPC testing failure (MSLP issue)

---

## Key Files

**Environment:**
- `environment-chpc.yml` - Conda environment spec (updated 2025-11-24)
- `setup-chpc.sh` - Automated setup script
- `CHPC-SETUP-GUIDE.md` - Deployment documentation

**MSLP Code:**
- `nwp/gefsdata.py` - GRIB download/parsing (line 252-307 for PRMSL)
- `preprocessing/representative_nwp_values.py` - MSLP time series (line 460-520)
- `scripts/check_mslp.py` - Diagnostic script (works for atmos.25, fails for atmos.5)

**Docs:**
- `CHPC-TEST-RESUME.md` - Previous session context (similar issue)
- `CONDA-VS-PIP.md` - Package management guide
- `CONTRADICTIONS-REPORT.md` - MSLP unit mismatch (Pa vs hPa)

---

## Quick Diagnostic Commands

```bash
# Test MSLP extraction (atmos.25 works, atmos.5 fails)
python ~/gits/clyfar/scripts/check_mslp.py -i 2025112300 -m p01 -p atmos.25 -f 0 6 12
python ~/gits/clyfar/scripts/check_mslp.py -i 2025112300 -m p01 -p atmos.5 -f 246 252 258

# Check Herbie inventory for atmos.5
python -c "from herbie import Herbie; H = Herbie('2025112300', model='gefs', product='atmos.5', member='p01', fxx=360); print(H.inventory())" | grep -i prmsl

# Check cfgrib version
python -c "import cfgrib; print(cfgrib.__version__)"

# Check pygrib availability
python -c "import pygrib; print(pygrib.__version__)"
```

---

## Session Timeline (2025-11-24)

1. **Environment creation issues** - Missing dependencies discovered iteratively
2. **Conda solver failures** - Fixed by using version ranges instead of exact pins
3. **Run-crash-install cycle** - Added: synopticpy, astral, matplotlib, pytz, pygrib, psutil
4. **Test started** - Run GEFS download + Clyfar inference
5. **MSLP failure** - atmos.5 product extraction fails with "invalid index to scalar variable"
6. **Session ended** - Same blocker as previous session (CHPC-TEST-RESUME.md)

---

## Next Session Action Items

**IMMEDIATE (Unblock testing):**
1. Debug why atmos.5 PRMSL extraction fails (test pygrib fallback)
2. Implement workaround (skip atmos.5 OR force pygrib OR limit to f240)
3. Complete 3-member test run
4. Verify export module generates 63 JSON files

**LATER (Tech debt):**
1. Complete dependency audit (scan imports, build clean environment)
2. Resolve MSLP unit contradiction (Pa vs hPa in tech report)
3. Merge PRs after successful testing
4. Set up production cron (4× daily)

---

**Created:** 2025-11-24 21:05 UTC
**For:** Next Claude Code session
**Priority:** Fix MSLP atmos.5 extraction
