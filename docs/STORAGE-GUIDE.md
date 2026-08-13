# Clyfar Storage Guide

Quick reference for CHPC storage locations, replay output policy, and archival strategy.

---

## Storage Locations

| Location | Auto-Purge | Use For |
|----------|------------|---------|
| `/scratch/general/vast/$USER/` | **60 days** | Active runs, Herbie cache, Matplotlib cache |
| `/uufs/chpc.utah.edu/common/home/lawson-group6/clyfar/replay/` | Never | Durable replay archive |
| `~/` | Never, small quota | Code, configs, lightweight logs only |
| `/scratch/local/` | Reboot + short retention | Job temp files |
| `/tmp/` | Reboot | Fallback temp files only |

**Warning:** Scratch is scrubbed weekly. Files not accessed for >60 days are deleted.

Source: [CHPC File Storage Policies](https://www.chpc.utah.edu/documentation/policies/3.1FileStoragePolicies.php)

---

## Winter Replay Roots

```bash
RUN_ROOT=/scratch/general/vast/$USER/clyfar_replay/winter_2025_2026
ARCHIVE_ROOT=/uufs/chpc.utah.edu/common/home/lawson-group6/clyfar/replay/winter_2025_2026
```

Durable replay review outputs belong under the archive root, especially:
`cases/`, `data/`, `figures/`, `basinwx_export/`, `logs/`, `manifests/`,
`quicklooks/`, and `ledger.csv`.

## Non-Repo Output Rule

Do not let replay, reforecast, Ffion/LLM, figure, Matplotlib, or Herbie cache
output land under the repo checkout. Gitignore protects Git, not quota or
reproducibility.

Before replay, reforecast, LLM regeneration, or analysis, set explicit roots:

```bash
RUN_ROOT=/scratch/general/vast/$USER/clyfar_replay/winter_2025_2026
export DATA_ROOT="$RUN_ROOT/data"
export FIG_ROOT="$RUN_ROOT/figures"
export EXPORT_DIR="$RUN_ROOT/basinwx_export"
export JSON_TESTS_ROOT="$RUN_ROOT/data/json_tests"
export CLYFAR_JSON_TESTS_ROOT="$JSON_TESTS_ROOT"
export CLYFAR_GEFS_DATA_ROOT="$RUN_ROOT/data/gefs_representative"
export CLYFAR_HERBIE_CACHE="$RUN_ROOT/herbie_cache"
export MPLCONFIGDIR="$RUN_ROOT/mplconfig"
export CLYFAR_PERFORMANCE_LOG="$RUN_ROOT/performance_log.txt"
export CLYFAR_ENABLE_UPLOAD=0
export LLM_SKIP_UPLOAD=1
```

For direct Clyfar runs, pass `-d "$DATA_ROOT" -f "$FIG_ROOT"`.
For Ffion-only regeneration, set `CLYFAR_JSON_TESTS_ROOT`; otherwise
`scripts/run_llm_outlook.sh` defaults to `~/basinwx-data/clyfar/json_tests`.

## Output Directory Structure

```
/scratch/general/vast/$USER/clyfar/<run-kind>/
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

Use the same structure for durable archive material under `lawson-group6`.

## Herbie Cache Policy

Use a Herbie cache during active research when it materially speeds reruns, but
keep it on scratch, not in the repo.

- Good active cache: `$RUN_ROOT/herbie_cache`.
- Bad cache: repo-local `data/herbie_cache`.
- Long-term default: archive derived products, logs, manifests, ledgers, CASE
  outputs, Ffion text/PDFs, export JSON, and final figures.
- Do not archive broad GRIB/index cache trees unless bitwise input
  reproducibility becomes a documented science requirement.

## Legacy Checkout Cleanup SOP

Do not treat everything under `data/` as one movable unit. Classify it first:

1. **Tracked static inputs:** retain `data/geog/` in the checkout.
2. **Derived outputs:** move reviewed run/CASE/figure material to one explicit
   scratch recovery or durable archive root, keeping the original directory
   names. If a tree contains many small files, first rename it into an explicit
   staging path on the same filesystem, then use a monitored resumable `rsync`
   job. Do not hold an interactive session open on a cross-filesystem `mv`.
3. **Regenerable caches:** handle `data/herbie_cache/` separately. Do not bundle
   it into a cross-filesystem `mv` with derived outputs; a deeply nested cache
   can dominate the operation and create a long partial-copy window.

For a repo-local cache, first verify the exact path and that no job is using it.
Delete it as regenerable data after a successful run, unless a documented
bitwise-input requirement explicitly justifies preservation. If preservation
is required, schedule and monitor it as its own transfer rather than doing it
inside an interactive mixed-artifact cleanup.

Use bounded checks during cold start:

```bash
find data -mindepth 1 -maxdepth 1 -printf '%f\n' | sort
find figures figures_parallel -mindepth 1 -maxdepth 1 -type d -printf '%p\n'
```

Avoid unbounded recursive `du` or `find` over a cache on shared storage. The
inventory helper times size scans out rather than allowing one cache tree to
hold the whole audit open.

---

## What to Archive vs Delete

**Archive (to group storage):**
- `parquet/dailymax/` - aggregated results
- `parquet/timeseries/` - methodology data
- `figures/heatmaps/` - publication-ready
- `basinwx_export/` - website JSON
- `data/json_tests/CASE_*/` - CASE bundles and LLM/Ffion outputs
- `logs/`, `manifests/`, `quicklooks/`, `ledger.csv` - replay review evidence

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
: "${CLYFAR_HERBIE_CACHE:?set CLYFAR_HERBIE_CACHE first}"
find "$CLYFAR_HERBIE_CACHE" -mindepth 1 -maxdepth 1 -exec rm -rf -- {} +

# Check home quota
df -h ~

# Archive a reviewed run to group storage
cp -r "$RUN_ROOT/YYYYMMDDHH" "$ARCHIVE_ROOT/"
```

---

## Sources

- [CHPC File Storage Policies](https://www.chpc.utah.edu/documentation/policies/3.1FileStoragePolicies.php)
- [CHPC Storage Services](https://www.chpc.utah.edu/resources/storage_services.php)
- `brc-tools/docs/CHPC-REFERENCE.md`
