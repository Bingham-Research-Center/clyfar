# Clyfar Storage Guide

Clyfar-specific storage layout and archival workflow. **Quota numbers, mount paths, and CHPC-wide policy live in the durable team reference** — this doc deliberately does not restate them so they cannot drift.

## Canonical reference

For CHPC quotas, mount paths, autofs caveats, owned-node terms, and the Lawson-group storage best-practice workflow:

```
~/gits/brc-knowledge/scholarium/reference-base/resources/chpc-team-resource-inventory.md
```

That file is the source of truth for: home/scratch/group quotas, the `lawson-group{4,5,6}` tier (group6 is currently the active archive store; group5 has shown autofs faults), the 60-day atime-based scratch purge, and the recommended scratch-first workflow.

If you are about to archive or stage data, **smoke-test the mount first**:

```bash
df -hT /uufs/chpc.utah.edu/common/home/lawson-group{4,5,6} 2>&1
```

A `Too many levels of symbolic links` result means autofs has faulted on this node — try another node before assuming the volume is gone.

## Clyfar output tree

Same structure under scratch (active runs) and under the chosen Cottonwood archive root (durable):

```
clyfar/v0p9/
└── YYYYMMDDHH/
    ├── parquet/
    │   ├── timeseries/       # GEFS station time series
    │   └── dailymax/         # Aggregated daily values
    ├── figures/
    │   ├── heatmaps/         # Possibility heatmaps
    │   ├── meteograms/       # Station plots
    │   └── synoptic/         # Future: 600 hPa maps, etc.
    └── json/
        └── basinwx_export/   # Website JSON
```

## Archive vs delete

**Archive** (copy from scratch to `lawson-group6/clyfar/archive/`):

- `parquet/dailymax/` — aggregated results
- `parquet/timeseries/` — methodology data
- `figures/heatmaps/` — publication-ready
- `metadata.json` — run configuration

**Delete** (regenerable from GEFS/Herbie):

- Full GRIB files
- Full gridded parquet
- Intermediate figures
- cfgrib index files

## Quick commands

```bash
# Local inventory (sizes, run counts, archive-base mount check)
scripts/storage_inventory.sh

# Interactive cleanup
scripts/storage_inventory.sh --clean

# Clear Herbie cache
rm -rf /scratch/general/vast/$USER/clyfar/herbie_cache/*

# Archive a run (group6 is the current active store; verify mount first)
df -hT /uufs/chpc.utah.edu/common/home/lawson-group6 \
  && cp -r /scratch/general/vast/$USER/clyfar/v0p9/YYYYMMDDHH \
           /uufs/chpc.utah.edu/common/home/lawson-group6/clyfar/archive/

# Override archive base for storage_inventory.sh (e.g., to point at group5 if group6 is faulted)
CLYFAR_ARCHIVE_BASE=/uufs/chpc.utah.edu/common/home/lawson-group5/clyfar \
  scripts/storage_inventory.sh
```

## Known follow-ups

- `scripts/submit_clyfar.sh` currently defaults `DATA_ROOT=$HOME/basinwx-data/clyfar`, which writes active-run data into `$HOME` instead of scratch. The script honors `DATA_ROOT` / `FIG_ROOT` / `EXPORT_DIR` env overrides today; a future change should flip the default to `/scratch/general/vast/$USER/clyfar` with a post-run rsync to group6.
- No automated archival, Herbie-cache cleanup, or pre-purge alerting yet.

## Sources

- `~/gits/brc-knowledge/scholarium/reference-base/resources/chpc-team-resource-inventory.md` (canonical)
- [CHPC File Storage Policies](https://www.chpc.utah.edu/documentation/policies/3.1FileStoragePolicies.php)
