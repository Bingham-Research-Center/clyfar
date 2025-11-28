# AI Agent Quick Reference - clyfar

**Current Task:** CHPC cron setup for 4× daily forecasts
**Status:** Script paths fixed, awaiting cron verification
**Last Session:** 2025-11-27
**Branch:** `integration-clyfar-v0.9.5`

---

## Quick Start

**This repo:** Clyfar ozone prediction model (v0.9.5)
**Integration:** Uploading forecasts to BasinWx website
**Dependencies:** brc-tools (installed via `pip install -e`)

**27 Nov Fix:** `scripts/submit_clyfar.sh` paths corrected:
- Conda: `~/software/pkg/miniforge3` (not miniconda3)
- Env: `clyfar-nov2025` (not clyfar-2025)
- Dir: `~/gits/clyfar` (not ~/clyfar)

**Resume work:**
```bash
conda activate clyfar-nov2025
cd ~/gits/clyfar  # CHPC path
# Test: sbatch scripts/submit_clyfar.sh
```

---

## Critical Context

### What Clyfar Produces
- **Output:** Dubois-Prade possibility values (0-1 scale)
- **Categories:** background, moderate, elevated, extreme (4 total)
- **Members:** 31 ensemble members (control + 30 perturbations)
- **Frequency:** 4× daily (GEFS runs: 00, 06, 12, 18Z)

### Data Structures
1. **clyfar_df_dict** - 3-hourly timeseries (~65 rows × 16 cols)
2. **dailymax_df_dict** - Daily max (~17 rows × 16 cols)

**Key columns:**
- Possibility: `background`, `moderate`, `elevated`, `extreme`
- Percentiles: `ozone_10pc`, `ozone_50pc`, `ozone_90pc`
- Met inputs: `snow`, `mslp`, `wind`, `solar`, `temp`

---

## Export Requirements (NEW)

**3 data products per run:**

1. **Possibility heatmaps** (31 files)
   - One per member: `clyfar_possibility_member001_YYYYMMDD_HHMMZ.json`
   - 4 categories × 17 days × 0-1 values

2. **Exceedance probabilities** (1 file)
   - Ensemble consensus: `clyfar_exceedance_YYYYMMDD_HHMMZ.json`
   - Fraction of members exceeding threshold

3. **Percentile scenarios** (31 files)
   - Defuzzified ppb: `clyfar_percentiles_member001_YYYYMMDD_HHMMZ.json`
   - 10th/50th/90th percentiles with error bars

**Total:** 63 JSON files per forecast run

---

## Current Status

### What's Working
- ✅ Model execution (`run_gefs_clyfar.py`)
- ✅ Parquet output (local saves)
- ✅ brc-tools package installed (editable mode)
- ✅ Environment variables (.env configured)

### What Needs Work
- ⚠️  `export/to_basinwx.py` - WRONG (uses 5 categories + aggregation)
- ⚠️  `test_integration.py` - Needs update for 4 categories
- ⚠️  `INTEGRATION_GUIDE.md` - Needs update for 3 products
- ⏳ Slurm submission script - To be created

---

## Key Files

**Core model:**
- `fis/v0p9.py` - Fuzzy inference system (categories defined here!)
- `run_gefs_clyfar.py` - Main execution

**Export (needs rewrite):**
- `export/to_basinwx.py` - JSON generation and upload
- `export/__init__.py` - Package init

**Testing:**
- `test_integration.py` - Integration validation
- `.env.example` - Environment template
- `.env` - Your secrets (gitignored)

**Documentation:**
- `INTEGRATION_GUIDE.md` - Step-by-step integration
- `GIT_COMMIT_GUIDE.md` - Safe commit procedures
- `README.md` - Multi-agent development notes

---

## Common Commands

**Test setup:**
```bash
conda activate clyfar-2025
python -c "from brc_tools.download.push_data import send_json_to_server; print('OK')"
python -c "from export.to_basinwx import export_and_upload; print('OK')"
```

**Run small test:**
```bash
python run_gefs_clyfar.py -i 2024010100 -n 2 -m 3 --testing --no-upload
```

**Test export:**
```bash
python test_integration.py  # Will fail until rewritten
```

---

## Integration with Other Repos

**Dependencies:**
- **brc-tools** - Upload functionality (`pip install -e ~/brc-tools`)
- **ubair-website** - Receives uploaded data
- **preprint-clyfar-v0p9** - Tech report (methodology reference)

**Coordination:**
- See `CROSS-REPO-SYNC.md` (to be created)
- Tech report = source of truth for methodology
- Python code = source of truth for implementation

---

## Gotchas

❌ Current export uses 5 categories (wrong!)
❌ Current export aggregates across members (wrong!)
❌ Don't run on CHPC login nodes (use Slurm!)
❌ GEFS latency varies (monitor and adjust schedule)

✅ Use 4 categories from `fis/v0p9.py:78-83`
✅ Export per-member data separately
✅ Submit as Slurm job (see scripts/ dir)
✅ Allow 3.5hr buffer for GEFS availability

---

## Next Actions

1. **Phase 1:** Review tech report for contradictions
2. **Phase 3:** Rewrite `export/to_basinwx.py` (3 products)
3. **Phase 7:** Create Slurm submission script
4. **Testing:** Validate with real GEFS data

**See:** `../ubair-website/COMPACT-RESUME-POINT.md` for full plan

---

**Last Updated:** 2025-11-23 (pre-compact)
**Model Version:** 0.9.5
**Next Review:** After export rewrite
