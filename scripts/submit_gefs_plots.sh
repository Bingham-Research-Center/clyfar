#!/bin/bash
#SBATCH --job-name=gefs-plots
#SBATCH --account=notchpeak-shared-short
#SBATCH --partition=notchpeak-shared-short
#SBATCH --time=02:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=48G
#SBATCH --output=/uufs/chpc.utah.edu/common/home/%u/logs/basinwx/gefs_plots_%j.out
#SBATCH --error=/uufs/chpc.utah.edu/common/home/%u/logs/basinwx/gefs_plots_%j.err
#SBATCH --mail-type=FAIL
#SBATCH --mail-user=%u@utah.edu

#####################################################################
# GEFS meteograms - CHPC Slurm submission, independent of Clyfar
#####################################################################
#
# Purpose: keep the GEFS weather meteograms (wind, solar, snow, mslp, temp)
#          flowing to BasinWx year-round, without running the ozone model.
#
# Why this exists: submit_clyfar.sh is a monolith -- model, then export, then
# upload, then LLM outlook. The GEFS meteograms are produced by the *download*
# half of run_gefs_clyfar.py and need none of the fuzzy inference, but because
# they only shipped as part of that job they stopped dead when the Clyfar cron
# was commented out on 2026-03-30 ("season ended"). This job runs the GEFS half
# alone via --no-clyfar and pushes the meteograms on their own.
#
# Cost: keeps submit_clyfar.sh's 2 h / 48 GB. An earlier 1 h / 24 GB sizing was
# wrong: dropping the FIS removes the *inference*, but the GEFS download this job
# keeps (31 members x 5 variables x 16-day horizon, parallel workers) is the
# memory-hungry half. 24 GB fit once (32 min, 2026-08-27 18Z) and OOM-killed four
# workers the next run (2026-08-31 12Z), which thrashed the download into the 1 h
# wall. Do not trim these again without watching MaxRSS across several inits --
# the partition allows 8 h, so headroom is nearly free.
#
# Schedule: 4x daily, 4.25 h after each GEFS cycle, matching what ozone season
#           used. Install on notchpeak1:
#   15 3,9,15,21 * * * /bin/bash -c 'source ~/.bashrc_basinwx && export PATH=$PATH:/uufs/notchpeak.peaks/sys/installdir/slurm/std/bin && cd ~/gits/clyfar && sbatch scripts/submit_gefs_plots.sh >> ~/logs/gefs_plots_submit.log 2>&1'
#
# Usage:
#   Manual:  sbatch scripts/submit_gefs_plots.sh [YYYYMMDDHH]
#   No-push: GEFS_PLOTS_ENABLE_UPLOAD=0 sbatch scripts/submit_gefs_plots.sh
#
# John Lawson & Claude, August 2026
#####################################################################

set -euo pipefail

echo "================================================================"
echo "GEFS meteograms - CHPC compute node"
echo "Job ID: ${SLURM_JOB_ID:-<none>}  Node: ${SLURM_NODELIST:-<none>}"
echo "CPUs: ${SLURM_CPUS_PER_TASK:-1}  Start: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo "================================================================"

if [ -f ~/.bashrc_basinwx ]; then
    source ~/.bashrc_basinwx
else
    echo "ERROR: ~/.bashrc_basinwx not found (needs DATA_UPLOAD_API_KEY)"
    exit 1
fi

source ~/software/pkg/miniforge3/etc/profile.d/conda.sh
conda activate "${CONDA_ENV:-clyfar-nov2025}" || {
    echo "ERROR: could not activate conda env ${CONDA_ENV:-clyfar-nov2025}"
    exit 1
}

CLYFAR_DIR="${CLYFAR_DIR:-$HOME/gits/clyfar}"
DATA_ROOT="${DATA_ROOT:-$HOME/basinwx-data/clyfar}"
FIG_ROOT="${FIG_ROOT:-$DATA_ROOT/figures}"
LOG_DIR="${LOG_DIR:-$HOME/logs/basinwx}"
NMEMBERS="${NMEMBERS:-all}"
UPLOAD_BUCKET="${UPLOAD_BUCKET:-images}"

# 1 (default) -> push to BasinWx; 0 -> render locally only.
GEFS_PLOTS_ENABLE_UPLOAD="${GEFS_PLOTS_ENABLE_UPLOAD:-1}"

mkdir -p "$DATA_ROOT" "$FIG_ROOT" "$LOG_DIR"

# Compute nodes do not share the login node's /tmp, so a CLYFAR_DIR under it
# vanishes here and Slurm only says "couldn't chdir ... going to /tmp instead".
# Fail with the reason instead.
if [ ! -d "$CLYFAR_DIR" ]; then
    echo "ERROR: CLYFAR_DIR does not exist on this node: $CLYFAR_DIR"
    echo "       Compute nodes see /uufs (home, scratch) but not the login"
    echo "       node's /tmp. Point CLYFAR_DIR at shared storage."
    exit 1
fi
cd "$CLYFAR_DIR"

# The cron does `cd ~/gits/clyfar && sbatch ...`, so this job runs whatever
# branch is checked out. Say which, so a surprise is visible in the log rather
# than in the output.
echo "Repo: $CLYFAR_DIR @ $(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo '?') ($(git rev-parse --short HEAD 2>/dev/null || echo '?'))"

INIT_TIME="${1:-}"
if [ -n "$INIT_TIME" ]; then
    echo "Using provided init time: $INIT_TIME"
else
    # Anchor on Slurm submit time, not now: a queued job must not skip a cycle.
    SUBMIT_TIME_EPOCH=""
    if [ -n "${SLURM_JOB_ID:-}" ] && command -v scontrol >/dev/null 2>&1; then
        SUBMIT_TIME_RAW=$(scontrol show job "$SLURM_JOB_ID" -o 2>/dev/null \
            | sed -n 's/.*SubmitTime=\([^ ]*\).*/\1/p' | head -n1)
        if [ -n "${SUBMIT_TIME_RAW:-}" ] && [ "$SUBMIT_TIME_RAW" != "Unknown" ]; then
            SUBMIT_TIME_EPOCH=$(date -d "$SUBMIT_TIME_RAW" +%s 2>/dev/null || true)
        fi
    fi
    INIT_TIME=$(SUBMIT_TIME_EPOCH="$SUBMIT_TIME_EPOCH" python3 - <<'PY'
from datetime import datetime, timedelta
import os
submit_epoch = os.environ.get("SUBMIT_TIME_EPOCH", "").strip()
anchor = None
if submit_epoch:
    try:
        anchor = datetime.utcfromtimestamp(int(submit_epoch))
    except ValueError:
        anchor = None
if anchor is None:
    anchor = datetime.utcnow()
# GEFS runs 00/06/12/18Z and lands ~3 h later; the cron fires at +4.25 h.
target = anchor - timedelta(hours=4, minutes=30)
init_dt = target.replace(hour=(target.hour // 6) * 6, minute=0,
                         second=0, microsecond=0)
print(init_dt.strftime('%Y%m%d%H'))
PY
)
    echo "Auto-detected init time: $INIT_TIME (GEFS ${INIT_TIME:8:2}Z)"
fi

if ! [[ "$INIT_TIME" =~ ^[0-9]{10}$ ]]; then
    echo "ERROR: init time must be YYYYMMDDHH, got: $INIT_TIME"
    exit 1
fi

echo "================================================================"
echo "GEFS download + meteograms for $INIT_TIME (no Clyfar inference)"
echo "================================================================"

# Retry contract, ported from submit_clyfar.sh: run_gefs_clyfar.py exits
# 75-79 for transient failures (404 data-not-ready, incomplete index, network
# timeout, pool timeout) expecting a resubmit. The #23 extraction dropped the
# consumer, so a hung Herbie fetch (exit 78 after the 90-min pool watchdog)
# killed the run silently under `set -e` — no ALERT line, nothing retried.
RETRY_COUNT=${RETRY_COUNT:-0}
MAX_RETRIES=${GEFS_PLOTS_MAX_RETRIES:-2}
RETRY_DELAY_MINUTES=30
EXIT_CODE_RETRY_MIN=75
EXIT_CODE_RETRY_MAX=79
echo "Retry status: attempt $((RETRY_COUNT + 1)) of $((MAX_RETRIES + 1))"

# --no-clyfar runs the download/save/visualise half only: no FIS, no ozone
# heatmaps, no LLM stage.
set +e
python3 run_gefs_clyfar.py \
    -i "$INIT_TIME" \
    -d "$DATA_ROOT" \
    -f "$FIG_ROOT" \
    -n "${SLURM_CPUS_PER_TASK:-4}" \
    -m "$NMEMBERS" \
    --no-clyfar
STAGE_EXIT=$?
set -e

if [ $STAGE_EXIT -ge $EXIT_CODE_RETRY_MIN ] && [ $STAGE_EXIT -le $EXIT_CODE_RETRY_MAX ]; then
    if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
        NEW_RETRY_COUNT=$((RETRY_COUNT + 1))
        RETRY_JOB_ID=$(sbatch --parsable \
               --begin=now+${RETRY_DELAY_MINUTES}minutes \
               --export=ALL,RETRY_COUNT=$NEW_RETRY_COUNT \
               "$CLYFAR_DIR/scripts/submit_gefs_plots.sh" "$INIT_TIME")
        echo "STATUS_GEFS_STAGE=RETRY_SCHEDULED init=$INIT_TIME exit=$STAGE_EXIT attempt=$NEW_RETRY_COUNT job=$RETRY_JOB_ID"
        echo "Retryable failure (exit $STAGE_EXIT); retry job $RETRY_JOB_ID begins in $RETRY_DELAY_MINUTES min. This job exits 0."
        exit 0
    else
        echo "ALERT_GEFS_STAGE_FAILED init=$INIT_TIME exit=$STAGE_EXIT retries_exhausted=$MAX_RETRIES"
        echo "STATUS_GEFS_STAGE=FAILED init=$INIT_TIME exit=$STAGE_EXIT"
        exit $STAGE_EXIT
    fi
elif [ $STAGE_EXIT -ne 0 ]; then
    echo "ALERT_GEFS_STAGE_FAILED init=$INIT_TIME exit=$STAGE_EXIT"
    echo "STATUS_GEFS_STAGE=FAILED init=$INIT_TIME exit=$STAGE_EXIT"
    exit $STAGE_EXIT
fi

echo "STATUS_GEFS_STAGE=SUCCESS init=$INIT_TIME"

echo "================================================================"
if [ "$GEFS_PLOTS_ENABLE_UPLOAD" = "1" ]; then
    echo "Uploading meteograms to BasinWx (bucket: $UPLOAD_BUCKET)"
    if python3 scripts/push_gefs_plots.py \
            --init "$INIT_TIME" \
            --fig-root "$FIG_ROOT" \
            --data-type "$UPLOAD_BUCKET"; then
        echo "STATUS_GEFS_PLOTS_PUSH=SUCCESS init=$INIT_TIME"
    else
        PUSH_EXIT=$?
        echo "ALERT_GEFS_PLOTS_PUSH_FAILED init=$INIT_TIME exit=$PUSH_EXIT"
        echo "STATUS_GEFS_PLOTS_PUSH=FAILED init=$INIT_TIME exit=$PUSH_EXIT"
        exit $PUSH_EXIT
    fi
else
    echo "STATUS_GEFS_PLOTS_PUSH=SKIPPED init=$INIT_TIME reason=upload_disabled"
fi

echo "================================================================"
echo "Done. End: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo "  Figures: $FIG_ROOT/meteograms"
echo "  Parquet: $DATA_ROOT"
echo "  sacct -j ${SLURM_JOB_ID:-<none>} --format=JobID,JobName,Elapsed,State,ExitCode"
echo "================================================================"
