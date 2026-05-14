# Cold-start handoff: reforecast-prep plan
Date written: 2026-05-13
Audience: the next session (human or agent) starting cold on Clyfar reforecast prep.

This is the **near-term action plan** to take Clyfar from "hibernating with a known storage-policy violation" to "able to run reforecast sweeps end-to-end on scratch with durable outputs on Cottonwood." It is intentionally scoped to the prerequisites *before* a real winter reforecast run begins. Long-term v1.1 work lives in [`v1.1-roadmap.md`](v1.1-roadmap.md); seasonal pause/resume mechanics live in [`../HIBERNATION.md`](../HIBERNATION.md); the existing storage-safe smoke recipe lives in [`chpc-v106-dry-run.md`](chpc-v106-dry-run.md).

## Context (what just happened)

On 2026-05-13 (commit `9f71927` on `main`):

- `docs/STORAGE-GUIDE.md` rewritten thin. The canonical CHPC reference is now `~/gits/brc-knowledge/scholarium/reference-base/resources/chpc-team-resource-inventory.md` — quotas, mounts, autofs caveats, owned-node terms all live there. **Do not restate quota numbers in Clyfar docs**; they drift.
- `HIBERNATION.md` trimmed from 160 to 56 lines (runbook only); the 16-item dev roadmap moved to `docs/v1.1-roadmap.md`.
- `scripts/storage_inventory.sh`: archive base now `CLYFAR_ARCHIVE_BASE`-configurable with `lawson-group6` default; scratch defaults are `/scratch/general/vast/$USER/clyfar`; added a mount smoke-test that warns (no-fails) when the configured Cottonwood volume is autofs-faulted on the current node.
- `scripts/submit_clyfar.sh`: **TODO(policy)** comment above the `DATA_ROOT` default — flagging that the operational submit script still writes active-run data to `$HOME/basinwx-data/clyfar` against the stated policy. **Behavior is unchanged.** That's the next change.

So: storage *docs* are now correct and policy is unambiguous. Storage *code* still violates the policy in one important spot (`DATA_ROOT`) and one likely spot (`brc-tools/get_map_obs.py`). The plan below fixes both before any real reforecast loop runs.

## Constraints the cold-start session needs to know

1. **`main` is protected.** A push to `main` works only because the human user has bypass permission; routine work belongs on a feature branch with a PR. Default: branch off `main` for the changes below.
2. **lawson-group6 is the active Cottonwood store** (group5 had autofs faults from `notch392` on 2026-05-13). Always smoke-test the mount with `df -hT /uufs/chpc.utah.edu/common/home/lawson-group6` before staging or archiving. If group6 is faulted on the current node, try a different node before re-pointing at group5.
3. **Reforecast invocation pattern.** `scripts/submit_clyfar.sh` accepts `$1 = YYYYMMDDHH` as an explicit init time and `--no-retry` to disable transient-failure resubmission (codes 75–79). Reforecasts always specify an explicit init; never auto-detect.
4. **Upload guard.** `CLYFAR_ENABLE_UPLOAD=0` disables all uploads to BasinWx (forecast JSON, figures, LLM PDF). Reforecasts must run with this set so no historical cycle pollutes the website. `CLYFAR_SKIP_INTERNAL_EXPORT=1` is the default and should stay.
5. **Cron stays paused.** Reforecasts are batch-launched on demand; do not edit the user crontab. The hibernation runbook describes the cron state to preserve.
6. **Conda env: `clyfar-nov2025`.** `texlive` lives at `/uufs/chpc.utah.edu/sys/installdir/texlive/2022/bin/x86_64-linux`; `claude` CLI at `~/.local/bin/claude`. These are added by `submit_clyfar.sh` itself; don't duplicate them at the wrapper layer.

## Micro-step plan

### Step 1 — Branch and inventory pre-existing $HOME data (read-only)

```bash
cd ~/gits/clyfar
git checkout -b reforecast-prep
du -sh ~/basinwx-data/clyfar 2>/dev/null
find ~/basinwx-data/clyfar -maxdepth 2 -type d -name "20*" 2>/dev/null | sort | head
df -hT /uufs/chpc.utah.edu/common/home/lawson-group6
```

Goal: confirm what's already sitting in `$HOME/basinwx-data/clyfar`. If there are recent cycles there that the operator wants to keep, a one-time rsync to `lawson-group6/clyfar/archive/` is the cleanest path *before* the DATA_ROOT default flips — otherwise old cycles get orphaned. Do not delete anything in this step.

### Step 2 — Flip `submit_clyfar.sh` DATA_ROOT default + add archive rsync

In `scripts/submit_clyfar.sh`:

- Change the `DATA_ROOT` default (around line 80, marked with `TODO(policy):`) to `/scratch/general/vast/$USER/clyfar` and drop the `TODO(policy)` comment in the same edit.
- After the BasinWx export block (after the `STATUS_FORECAST_EXPORT=` line, before the LLM block), add a guarded rsync that copies the **archive subset** to Cottonwood:

  Files to copy: `$DATA_ROOT/dailymax/`, `$DATA_ROOT/clyfar*_df.parquet` (just the aggregated ones if size-sensitive; see `STORAGE-GUIDE.md` archive list), `$FIG_ROOT/heatmaps/`, and any `metadata.json` in the run root.

  Target: `$CLYFAR_ARCHIVE_BASE/archive/$INIT_TIME/` where `CLYFAR_ARCHIVE_BASE` defaults to `/uufs/chpc.utah.edu/common/home/lawson-group6/clyfar` (matching `storage_inventory.sh`).

  The rsync block must:
  - First `df -hT "$CLYFAR_ARCHIVE_BASE"` and `continue` (i.e., `STATUS_ARCHIVE=SKIPPED reason=mount_faulted`) if the volume is unmounted on this node. Do not fail the job — the science output is already on scratch.
  - Emit a `STATUS_ARCHIVE=SUCCESS|FAILED|SKIPPED` marker so triage rg patterns can find it.
  - Be guardable with `CLYFAR_SKIP_ARCHIVE=1` for ad-hoc / dry-run cases that own their own destination.

- Also update the "Output locations:" trailing echo to reflect the new defaults.

Do **not** change anything about `LOG_DIR` (it still lives in `$HOME/logs/basinwx`, which is fine — logs are small and convenient there) or the cron command body in `HIBERNATION.md`.

### Step 3 — Add `scripts/reforecast_one.sh` (smallest useful dry-run wrapper)

A thin wrapper that exercises the new flow with safety rails. Pseudocode:

```bash
#!/usr/bin/env bash
# Usage: scripts/reforecast_one.sh YYYYMMDDHH [scratch-subdir]
# Submits a single historical cycle with uploads disabled and an
# isolated scratch DATA_ROOT, so multiple dry-runs don't collide.

set -euo pipefail
INIT="${1:?INIT_TIME (YYYYMMDDHH) required}"
SUBDIR="${2:-dryrun-$(date -u +%Y%m%d_%H%M%S)}"
ROOT="/scratch/general/vast/$USER/clyfar/reforecast/$SUBDIR/$INIT"

mkdir -p "$ROOT"
cd ~/gits/clyfar

CLYFAR_ENABLE_UPLOAD=0 \
CLYFAR_SKIP_ARCHIVE=1 \
DATA_ROOT="$ROOT/data" \
FIG_ROOT="$ROOT/figures" \
EXPORT_DIR="$ROOT/basinwx_export" \
  sbatch scripts/submit_clyfar.sh "$INIT" --no-retry
```

Notes for the cold-start session:

- `--no-retry` is deliberate for dry-runs: a 404 on historical GEFS should fail fast, not resubmit on a 30-minute delay for hours.
- `CLYFAR_SKIP_ARCHIVE=1` is the dry-run-only switch; production runs leave it unset so Step 2's rsync fires.
- Pick `SUBDIR` names that are meaningful (`smoke-2024010100`, `winter2425-batch1`) so the scratch tree is browsable.

### Step 4 — Smoke 2–3 historical cycles

Recommended cycle selection (good obs coverage, no live-upload risk, span dynamics):

- `2024010100` — already named in `chpc-v106-dry-run.md` as the first safe init; matches what's been tested before.
- `2024121500` — winter inversion period, exercises the snow/stagnation code paths.
- `2025020600` — mid-winter, post-holiday data steady-state.

For each:

```bash
scripts/reforecast_one.sh 2024010100 smoke-baseline
scripts/reforecast_one.sh 2024121500 smoke-inversion
scripts/reforecast_one.sh 2025020600 smoke-midwinter
```

Verification per cycle (after job completes):

```bash
ROOT=/scratch/general/vast/$USER/clyfar/reforecast/smoke-baseline/2024010100
ls -la "$ROOT/data/dailymax/" "$ROOT/figures/heatmaps/" "$ROOT/basinwx_export/" 2>/dev/null
rg -n "STATUS_FORECAST_EXPORT|STATUS_LLM_STAGE|STATUS_ARCHIVE" \
  ~/logs/basinwx/clyfar_*.out ~/logs/basinwx/clyfar_*.err | tail -20
```

Gate: all three cycles must produce a non-empty `dailymax/`, at least one heatmap PNG, a populated `basinwx_export/`, and `STATUS_FORECAST_EXPORT=SUCCESS`. LLM stage success is desirable but **not** a gate (Phase B is non-blocking by design).

### Step 5 — Verify Step 2's rsync path on one *non-dry-run* cycle

The dry-runs in Step 4 set `CLYFAR_SKIP_ARCHIVE=1`, so they exercise everything *except* the archive rsync. Do one extra run *without* the skip, with a clearly-marked dry-run init time, to confirm Cottonwood writes work:

```bash
# Same wrapper, but unset the skip
CLYFAR_ENABLE_UPLOAD=0 \
DATA_ROOT="/scratch/general/vast/$USER/clyfar/reforecast/archive-test/2024010100/data" \
FIG_ROOT="/scratch/general/vast/$USER/clyfar/reforecast/archive-test/2024010100/figures" \
EXPORT_DIR="/scratch/general/vast/$USER/clyfar/reforecast/archive-test/2024010100/basinwx_export" \
CLYFAR_ARCHIVE_BASE=/uufs/chpc.utah.edu/common/home/lawson-group6/clyfar-dryrun \
  sbatch scripts/submit_clyfar.sh 2024010100 --no-retry
```

Note `CLYFAR_ARCHIVE_BASE` overridden to a sibling path so the live archive root isn't contaminated with dry-run material. Verify with `ls /uufs/chpc.utah.edu/common/home/lawson-group6/clyfar-dryrun/archive/2024010100/` and clean up after.

### Step 6 — Audit + fix `brc-tools/get_map_obs.py`

Current state: `~/gits/brc-tools/brc_tools/download/get_map_obs.py` has a comment "Save to scratch or temp directory" but writes to `~/gits/brc-tools/data/` (in-repo, under `$HOME`). It runs every 5 minutes via cron.

Two options:

a. **Minimal:** add the same `TODO(policy)` comment style there and leave behavior unchanged. Punts the actual move.

b. **Recommended:** flip it to `${BRC_OBS_DATA_ROOT:-/scratch/general/vast/$USER/obs/maps}` with `os.makedirs(..., exist_ok=True)`. This is a 2-line change. The downstream consumer (whatever reads the obs maps) must be checked — grep for the existing `~/gits/brc-tools/data` path in both repos before flipping.

Either way, this is a **separate PR** in the `brc-tools` repo, not in Clyfar. Do not bundle. The Clyfar cron line that runs `get_map_obs.py` will pick up the new path automatically once the brc-tools PR merges and the conda env doesn't need to change.

If the obs-map output path is consumed by any other downstream tool, that tool needs to be informed in the same PR. Check `brc-tools` and `ubair-website` and `ubwo-fcst` for grep matches against `brc-tools/data`.

### Step 7 — Compose `scripts/reforecast_window.sh` for batch sweeps

Once Steps 4 and 5 pass, the batch driver is straightforward. Sketch:

```bash
#!/usr/bin/env bash
# Usage: scripts/reforecast_window.sh START_DATE END_DATE [SUBDIR]
# Submits all 00/06/12/18Z cycles in [START_DATE, END_DATE] as a SLURM
# array, with CLYFAR_ENABLE_UPLOAD=0 and an isolated DATA_ROOT per cycle.
```

Implementation choices to weigh before writing:

- **SLURM job array vs. shell loop:** an array is more polite to the scheduler and gives one `sacct` row per cycle. A shell loop is one-liner-shorter. Default to an array.
- **Cycle list generation:** Python or bash-based `seq` + `date`. Keep dependency-free if possible (bash + `date -d` arithmetic).
- **Concurrency cap:** `--array=0-419%8` (or similar) keeps the queue polite. Tune after the smoke run shows per-cycle wallclock.
- **Failure handling:** the array should not stop on first failure; log STATUS markers per cycle and produce a summary at the end. Keep `--no-retry` so a 404 doesn't churn for hours; reforecast data is historical and either available or not.

The 2024-12-01 → 2025-03-15 winter window is ~420 cycles. A single sbatch array with `%8` concurrency on `notchpeak-shared-short` (8-hour walltime per cycle, current default) gets through it in roughly a day if each cycle finishes in <1 hour.

Migrating reforecast submissions to the owned `lawson-np` partition (14-day walltime, no preemption) is a worthwhile follow-up but is out-of-scope for this handoff — see [`v1.1-roadmap.md`](v1.1-roadmap.md). For the smoke and the first batch, stay on `notchpeak-shared-short` to match current production behavior.

### Step 8 — Open the PR

Once Steps 2–5 are clean and Step 7 is drafted:

```bash
git push -u origin reforecast-prep
gh pr create --title "Reforecast prep: flip DATA_ROOT to scratch, add Cottonwood rsync, dry-run wrappers" \
  --body "..."
```

PR body should include: the policy citation from `STORAGE-GUIDE.md`, the test-plan checklist (Steps 4 and 5), explicit confirmation that `HIBERNATION.md` cron state is untouched, and a note that `brc-tools/get_map_obs.py` is a separate follow-up.

## Verification gates (cumulative)

- [ ] Step 1: pre-existing `$HOME/basinwx-data/clyfar` inventory written down somewhere (PR description, or a one-off file).
- [ ] Step 2: `submit_clyfar.sh` `DATA_ROOT` default = scratch; `STATUS_ARCHIVE=` marker present in log output; `CLYFAR_SKIP_ARCHIVE` honored; archive rsync conditional on `df -hT` succeeding.
- [ ] Step 3: `scripts/reforecast_one.sh` exists, is executable (`chmod +x`), and runs in <2 lines for the trivial case.
- [ ] Step 4: three smoke cycles produce non-empty `dailymax/`, heatmap PNGs, populated `basinwx_export/`, and `STATUS_FORECAST_EXPORT=SUCCESS` in logs.
- [ ] Step 5: one archive-test cycle lands under `lawson-group6/clyfar-dryrun/archive/2024010100/` and the dry-run sibling is cleaned up afterward.
- [ ] Step 6: separate `brc-tools` PR opened (link in the Clyfar PR description), or explicit decision documented to defer.
- [ ] Step 7: `scripts/reforecast_window.sh` drafted, runs end-to-end on a 2-cycle window (`scripts/reforecast_window.sh 2024010100 2024010106`).
- [ ] Step 8: PR opened against `main`, all gates green, awaiting review.

## What is explicitly out of scope here

- Resuming live cron submissions. Hibernation stays in effect; that decision is the user's, not the agent's.
- Changing the SLURM account/partition from `notchpeak-shared-short` to the owned `lawson-np`. Worthwhile, but separate.
- Cleaning up `$HOME/basinwx-data/clyfar` after the default flips. The PR adds the new path but doesn't move historical data; that's a one-time human decision (keep / archive / delete).
- Reforecast methodology choices: which window, which init cycles, which scoring rules. This handoff is the engineering plumbing only.
- Any change to `LLM-GENERATE.sh`, the LLM CLI invocation, or texlive/pandoc plumbing. Reforecast LLM outputs are useful but not gating.

## Pointers

- Storage policy (thin, Clyfar-side): [`STORAGE-GUIDE.md`](STORAGE-GUIDE.md)
- Canonical CHPC reference (sibling repo): `~/gits/brc-knowledge/scholarium/reference-base/resources/chpc-team-resource-inventory.md`
- Earlier dry-run note (overlapping but specific to v1.0.6 smoke): [`chpc-v106-dry-run.md`](chpc-v106-dry-run.md)
- Pause/resume mechanics: [`../HIBERNATION.md`](../HIBERNATION.md)
- Long-term v1.1 roadmap: [`v1.1-roadmap.md`](v1.1-roadmap.md)
- Submit script (the file most edits land in): `scripts/submit_clyfar.sh`
- Storage audit script (already updated 2026-05-13): `scripts/storage_inventory.sh`
