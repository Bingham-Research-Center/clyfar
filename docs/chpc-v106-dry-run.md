# Clyfar v1.0.6 CHPC dry-run handoff
Date updated: 2026-05-13

This is the durable Clyfar-side execution note for the v1.0.6 storage-safe
smoke and later winter rerun. Keep task priority and approval state in
`../ceidwad`; keep runnable Clyfar commands and storage rules here.

## Goal

Prove the v1.0.6 command path and storage layout before any Dec 1-Mar 15
six-hour winter rerun is scheduled.

First safe init:

```text
2024010100
```

This is a wiring smoke only. It proves command settings, upload guards,
multiprocessing, output roots, and run-summary writing. It does not close the
science verification or snow-case evidence gates.

## Storage policy

Use CHPC home only for code and small config files.

Use scratch for active runs, re-downloadable input caches, logs, and temporary
outputs:

```text
/scratch/general/vast/$USER/clyfar/dry-runs/v1.0.6/YYYYMMDD_HH00Z/
```

Promote only selected durable outputs to approved Cottonwood/group storage
after inspection:

```text
/uufs/chpc.utah.edu/common/home/lawson-group5/clyfar/archive/
```

Archive candidates:

- aggregated parquet used by the method or preprint
- publication-ready figures
- run metadata and command logs

Do not archive regenerable GRIB files, cfgrib indexes, or broad intermediate
working trees unless there is a specific reproducibility reason.

## One-init smoke command

Run from the Clyfar repo on CHPC. Keep uploads disabled.

```bash
cd ~/gits/clyfar

INIT=2024010100
RUN_ROOT="/scratch/general/vast/$USER/clyfar/dry-runs/v1.0.6/20240101_0000Z_smoke"
DATA_ROOT="$RUN_ROOT/data"
FIG_ROOT="$RUN_ROOT/figures"
EXPORT_ROOT="$RUN_ROOT/export"
LOG_ROOT="$RUN_ROOT/logs"
HERBIE_ROOT="/scratch/general/vast/$USER/clyfar/herbie_cache/v1.0.6"

mkdir -p "$DATA_ROOT" "$FIG_ROOT" "$EXPORT_ROOT" "$LOG_ROOT" "$HERBIE_ROOT"

env \
  CLYFAR_ENABLE_UPLOAD=0 \
  CLYFAR_SKIP_INTERNAL_EXPORT=1 \
  CLYFAR_HERBIE_CACHE="$HERBIE_ROOT" \
  EXPORT_DIR="$EXPORT_ROOT" \
  python run_gefs_clyfar.py \
    -i "$INIT" \
    -n 2 \
    -m 2 \
    -d "$DATA_ROOT" \
    -f "$FIG_ROOT" \
    --testing \
    > "$LOG_ROOT/run_gefs_clyfar_${INIT}.log" 2>&1
```

Inspect after the run:

- `$LOG_ROOT/run_gefs_clyfar_2024010100.log`
- run-summary JSON under `$DATA_ROOT/baseline_0_9/`
- generated data under `$DATA_ROOT`
- generated figures under `$FIG_ROOT`
- absence of new outputs under repo-level `export/`, `data/baseline_0_9/`,
  `figures_archive/v0_9/`, and operational BasinWx export paths

The log should show upload disabled and internal BasinWx export skipped.

## Promotion rule

After the smoke passes:

1. Check whether archived inputs for `2025012500` exist in the approved storage
   tier. That init is the first science-case candidate because it is already
   tied to the snow deep-dive risk notes.
2. If `2025012500` is missing, stop and decide whether to fetch/backfill that
   case or continue with smoke evidence only.
3. Do not schedule the Dec 1-Mar 15 six-hour rerun until the active scratch root
   and durable archive root are explicit in the command or Slurm wrapper.

## Source-of-truth split

- `../ceidwad`: task card, approval state, and planning report pointers.
- `../clyfar`: runnable Clyfar commands, upload guards, and storage layout.
- `../brc-tools/docs/CHPC-REFERENCE.md`: team CHPC account/storage reference.
- `../brc-knowledge/scholarium/reference-base/resources/chpc-team-resource-inventory.md`:
  observed CHPC inventory and dashboard gaps.
