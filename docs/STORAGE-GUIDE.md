# Clyfar Storage Guide

Quick reference for CHPC storage locations, policies, and archival strategy.

---

## Storage Locations

| Location | Capacity | Auto-Purge | Use For |
|----------|----------|------------|---------|
| `/scratch/general/vast/` | 50 TB/user | **60 days** | Active runs, GRIB cache |
| Cottonwood (`lawson-group5`) | 16 TiB | Never | Archived runs, reference data |
| Home (`~/`) | 7.3 GiB | Never | Code, configs only |
| `/scratch/local/` | Node-local | **Reboot + 2 weeks** | Job temp files |
| `/tmp/` | Small | **Reboot** | Lock files only |

**Warning:** Scratch is scrubbed weekly. Files not accessed for >60 days are deleted.

Source: [CHPC File Storage Policies](https://www.chpc.utah.edu/documentation/policies/3.1FileStoragePolicies.php)

---

## Output Directory Structure

```
/scratch/general/vast/clyfar_test/v0p9/
└── YYYYMMDDHH/
    ├── parquet/
    │   ├── timeseries/       # GEFS station time series
    │   └── dailymax/         # Aggregated daily values
    ├── figures/
    │   ├── heatmaps/         # Possibility heatmaps
    │   ├── meteograms/       # Station plots
    │   └── synoptic/         # Future: 600hPa maps, etc.
    └── json/
        └── basinwx_export/   # Website JSON
```

Same structure for archive on Cottonwood.

---

## What to Archive vs Delete

**Archive (to Cottonwood):**
- `parquet/dailymax/` - aggregated results
- `parquet/timeseries/` - methodology data
- `figures/heatmaps/` - publication-ready
- `metadata.json` - run configuration

**Delete (regenerable):**
- Full GRIB files (re-downloadable)
- Full gridded parquet
- Intermediate figures
- cfgrib index files

---

## Quick Commands

```bash
# Check storage usage
scripts/storage_inventory.sh

# Interactive cleanup
scripts/storage_inventory.sh --clean

# Clear Herbie cache
rm -rf ~/gits/clyfar/data/herbie_cache/*

# Check home quota
df -h ~

# Archive a run to Cottonwood
cp -r /scratch/general/vast/clyfar_test/v0p9/YYYYMMDDHH \
      /uufs/chpc.utah.edu/common/home/lawson-group5/clyfar/archive/
```

---

## Future: Automation

Not yet implemented:
- Cron-based archival of old runs
- Auto-cleanup of Herbie cache
- Alerts before 60-day purge deadline
- Quota monitoring

---

## Sources

- [CHPC File Storage Policies](https://www.chpc.utah.edu/documentation/policies/3.1FileStoragePolicies.php)
- [CHPC Storage Services](https://www.chpc.utah.edu/resources/storage_services.php)
- `brc-tools/docs/CHPC-REFERENCE.md`
