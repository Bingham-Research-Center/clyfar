#!/bin/bash
#SBATCH --job-name=clyfar-forecast
#SBATCH --account=notchpeak-shared-short
#SBATCH --partition=notchpeak-shared-short
#SBATCH --time=02:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=48G
#SBATCH --output=/uufs/chpc.utah.edu/common/home/%u/logs/basinwx/clyfar_%j.out
#SBATCH --error=/uufs/chpc.utah.edu/common/home/%u/logs/basinwx/clyfar_%j.err
#SBATCH --mail-type=FAIL
#SBATCH --mail-user=%u@utah.edu

#####################################################################
# Clyfar Ozone Forecast - CHPC Slurm Submission Script
#####################################################################
#
# Purpose: Run Clyfar ozone forecasts on CHPC compute nodes
#          instead of login nodes to avoid resource constraints
#
# Schedule: Run 4x daily at local 03:15, 09:15, 15:15, 21:15
#           on the CHPC scheduler host (Mountain time; MST/MDT).
#           These map to GEFS 00Z, 06Z, 12Z, 18Z cycle handling.
#           Keep local-vs-UTC anchoring explicit when debugging.
#
# Usage:
#   Manual:   sbatch submit_clyfar.sh [YYYYMMDDHH] [--no-retry]
#   Cron:     15 3,9,15,21 * * * sbatch ~/gits/clyfar/scripts/submit_clyfar.sh
#
# Arguments:
#   $1: Optional forecast initialization time (YYYYMMDDHH)
#       If not provided, auto-detects most recent GEFS run
#   --no-retry: Disable automatic retry on transient failures (for ad-hoc runs)
#
# Environment variables required (set in ~/.bashrc_basinwx):
#   - DATA_UPLOAD_API_KEY
#   - SYNOPTIC_API_TOKEN (if used)
#
# Upload destinations are NOT an env var here. They come from
# ~/.config/ubair-website/website_urls (comma-separated, first = primary,
# rest = best-effort mirrors), or BASINWX_API_URLS to override. The singular
# BASINWX_API_URL was retired on 2026-08-13 -- do not reinstate it.
#
# Created by: John Lawson & Claude
# Last updated: 2026-03-07
#####################################################################

set -euo pipefail  # Exit on error, undefined variables, pipe failures

echo "================================================================"
echo "Clyfar Ozone Forecast - CHPC Compute Node"
echo "================================================================"
echo "Job ID: $SLURM_JOB_ID"
echo "Node: $SLURM_NODELIST"
echo "CPUs: $SLURM_CPUS_PER_TASK"
echo "Memory: $SLURM_MEM_PER_NODE MB"
echo "Start time: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo "================================================================"

# Load environment
if [ -f ~/.bashrc_basinwx ]; then
    echo "Loading BasinWx environment..."
    source ~/.bashrc_basinwx
else
    echo "ERROR: ~/.bashrc_basinwx not found"
    echo "Create it with: cp ~/.bashrc ~/.bashrc_basinwx and add environment variables"
    exit 1
fi

# Activate conda environment
echo "Activating clyfar-nov2025 conda environment..."
source ~/software/pkg/miniforge3/etc/profile.d/conda.sh
conda activate clyfar-nov2025 || {
    echo "ERROR: Failed to activate conda environment 'clyfar-nov2025'"
    echo "Check conda env list"
    exit 1
}

# Set paths (overridable for isolated test runs)
CLYFAR_DIR="${CLYFAR_DIR:-$HOME/gits/clyfar}"
DATA_ROOT="${DATA_ROOT:-$HOME/basinwx-data/clyfar}"
FIG_ROOT="${FIG_ROOT:-$DATA_ROOT/figures}"
EXPORT_DIR="${EXPORT_DIR:-$DATA_ROOT/basinwx_export}"
LOG_DIR="${LOG_DIR:-$HOME/logs/basinwx}"
JSON_TESTS_ROOT="${JSON_TESTS_ROOT:-${CLYFAR_JSON_TESTS_ROOT:-$DATA_ROOT/json_tests}}"

# Upload control:
#   1 (default) -> normal operational uploads
#   0           -> local-only run (no BasinWx uploads)
CLYFAR_ENABLE_UPLOAD="${CLYFAR_ENABLE_UPLOAD:-1}"

# Internal export control:
#   1 (default here) -> run_gefs_clyfar skips its own export block, and this
#                       script performs the single upload/export pass.
#   0                -> run_gefs_clyfar may also export/upload (can duplicate uploads).
CLYFAR_SKIP_INTERNAL_EXPORT="${CLYFAR_SKIP_INTERNAL_EXPORT:-1}"

# In normal operations, the last internal retry may proceed with incomplete
# GEFS data. Replay/evaluation drivers can disable that and let an external
# retry supervisor handle retryable failures instead.
CLYFAR_ALLOW_INCOMPLETE_ON_FINAL_RETRY="${CLYFAR_ALLOW_INCOMPLETE_ON_FINAL_RETRY:-1}"

# Ensure child processes (run_gefs_clyfar.py, inline Python export block) receive
# upload-control flags from this orchestrator.
export CLYFAR_ENABLE_UPLOAD
export CLYFAR_SKIP_INTERNAL_EXPORT
export CLYFAR_ALLOW_INCOMPLETE_ON_FINAL_RETRY
export CLYFAR_JSON_TESTS_ROOT="$JSON_TESTS_ROOT"

# Create directories if needed
mkdir -p "$DATA_ROOT" "$FIG_ROOT" "$EXPORT_DIR" "$LOG_DIR" "$JSON_TESTS_ROOT"

cd "$CLYFAR_DIR" || {
    echo "ERROR: Clyfar directory not found at $CLYFAR_DIR"
    exit 1
}

# Parse arguments
NO_RETRY=false
INIT_TIME=""

for arg in "$@"; do
    case $arg in
        --no-retry)
            NO_RETRY=true
            echo "Ad-hoc mode: automatic retries disabled"
            ;;
        *)
            # Assume it's the init time
            INIT_TIME=$arg
            ;;
    esac
done

# Determine forecast initialization time
if [ -n "$INIT_TIME" ]; then
    echo "Using provided init time: $INIT_TIME"
else
    # Auto-detect most recent GEFS run.
    # Important: use Slurm submit time as anchor so queue delays don't skip cycles.
    # GEFS runs at 00Z, 06Z, 12Z, 18Z; schedule is 4.5h after cycle availability.
    SUBMIT_TIME_RAW=""
    SUBMIT_TIME_EPOCH=""
    if [ -n "${SLURM_JOB_ID:-}" ] && command -v scontrol >/dev/null 2>&1; then
        SUBMIT_TIME_RAW=$(scontrol show job "$SLURM_JOB_ID" -o 2>/dev/null | sed -n 's/.*SubmitTime=\([^ ]*\).*/\1/p' | head -n1)
        # Slurm SubmitTime is typically in scheduler local time with no timezone suffix.
        # Convert to epoch using local-time interpretation, then anchor in UTC math.
        if [ -n "$SUBMIT_TIME_RAW" ] && [ "$SUBMIT_TIME_RAW" != "Unknown" ]; then
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

target = anchor - timedelta(hours=4, minutes=30)
gefs_hour = (target.hour // 6) * 6
init_dt = target.replace(hour=gefs_hour, minute=0, second=0, microsecond=0)
print(init_dt.strftime('%Y%m%d%H'))
PY
)

    GEFS_HOUR=${INIT_TIME:8:2}
    echo "Auto-detected init time: $INIT_TIME (GEFS ${GEFS_HOUR}Z run)"
    if [ -n "$SUBMIT_TIME_RAW" ] && [ "$SUBMIT_TIME_RAW" != "Unknown" ]; then
        echo "Init anchor (Slurm submit local): $SUBMIT_TIME_RAW"
    fi
    if [ -n "$SUBMIT_TIME_EPOCH" ]; then
        echo "Init anchor UTC (converted): $(date -u -d "@$SUBMIT_TIME_EPOCH" '+%Y-%m-%d %H:%M:%S')"
    else
        echo "Init anchor UTC (fallback current): $(date -u '+%Y-%m-%d %H:%M:%S')"
    fi
    echo "Current UTC: $(date -u '+%Y-%m-%d %H:%M:%S')"
fi

# Validate init time format
if ! [[ "$INIT_TIME" =~ ^[0-9]{10}$ ]]; then
    echo "ERROR: Invalid init time format. Expected YYYYMMDDHH, got: $INIT_TIME"
    exit 1
fi

# Retry configuration
# RETRY_COUNT is passed via --export when resubmitting
RETRY_COUNT=${RETRY_COUNT:-0}
if [ "$NO_RETRY" = true ]; then
    MAX_RETRIES=0
else
    MAX_RETRIES=5
fi
RETRY_DELAY_MINUTES=30
# Retryable exit codes (must match run_gefs_clyfar.py):
#   75 = HTTP 404 (data not yet available)
#   76 = Herbie KeyError (incomplete index file)
#   77 = Network timeout/connection error
EXIT_CODE_RETRY_MIN=75
EXIT_CODE_RETRY_MAX=79

echo "Retry status: attempt $((RETRY_COUNT + 1)) of $((MAX_RETRIES + 1))"
echo "DEBUG: RETRY_COUNT=$RETRY_COUNT, MAX_RETRIES=$MAX_RETRIES, RETRY_CODES=${EXIT_CODE_RETRY_MIN}-${EXIT_CODE_RETRY_MAX}"

# Run Clyfar forecast
echo "================================================================"
echo "Running Clyfar forecast for init time: $INIT_TIME"
echo "================================================================"
if [ "$CLYFAR_SKIP_INTERNAL_EXPORT" = "1" ]; then
    echo "Internal run_gefs export: DISABLED (submit script owns export/upload)"
else
    echo "Internal run_gefs export: ENABLED (may duplicate export/upload)"
fi

# Disable pipefail temporarily so we can capture exit code
set +e

# On final retry, allow incomplete data (fill with NaNs)
INCOMPLETE_FLAG=""
if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
    if [ "$CLYFAR_ALLOW_INCOMPLETE_ON_FINAL_RETRY" = "1" ]; then
        echo "Final retry attempt - will proceed with incomplete data if needed"
        INCOMPLETE_FLAG="--allow-incomplete"
    else
        echo "Final retry attempt - incomplete-data fallback disabled"
    fi
fi

python3 run_gefs_clyfar.py \
    -i "$INIT_TIME" \
    -d "$DATA_ROOT" \
    -f "$FIG_ROOT" \
    -n "$SLURM_CPUS_PER_TASK" \
    -m all \
    --log-fis \
    $INCOMPLETE_FLAG

CLYFAR_EXIT_CODE=$?
set -e

echo "DEBUG: Python exit code = $CLYFAR_EXIT_CODE"

# Handle exit codes
# Retryable codes: 75-79 (404, KeyError, network errors)
if [ $CLYFAR_EXIT_CODE -ge $EXIT_CODE_RETRY_MIN ] && [ $CLYFAR_EXIT_CODE -le $EXIT_CODE_RETRY_MAX ]; then
    # Transient failure - schedule retry
    if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
        NEW_RETRY_COUNT=$((RETRY_COUNT + 1))
        echo "================================================================"
        echo "RETRYABLE FAILURE (exit code $CLYFAR_EXIT_CODE)"
        echo "Scheduling retry $NEW_RETRY_COUNT of $MAX_RETRIES in $RETRY_DELAY_MINUTES minutes..."
        echo "================================================================"

        # Submit new job with delay
        RETRY_JOB_ID=$(sbatch --parsable \
               --begin=now+${RETRY_DELAY_MINUTES}minutes \
               --export=ALL,RETRY_COUNT=$NEW_RETRY_COUNT \
               "$CLYFAR_DIR/scripts/submit_clyfar.sh" "$INIT_TIME")

        echo "Retry job $RETRY_JOB_ID submitted for $(date -u -d "+${RETRY_DELAY_MINUTES} minutes" '+%Y-%m-%d %H:%M:%S UTC')"
        echo "This job exiting successfully (retry scheduled)."
        exit 0  # This job succeeded (it scheduled the retry)
    else
        echo "================================================================"
        echo "ERROR: Max retries ($MAX_RETRIES) exceeded."
        echo "GEFS data still not available after $((MAX_RETRIES * RETRY_DELAY_MINUTES)) minutes."
        echo "Manual intervention may be required."
        echo "Exiting with retryable code $CLYFAR_EXIT_CODE for external retry supervisors."
        echo "================================================================"
        exit $CLYFAR_EXIT_CODE
    fi
elif [ $CLYFAR_EXIT_CODE -ne 0 ]; then
    echo "ERROR: Clyfar forecast failed with exit code $CLYFAR_EXIT_CODE"
    exit $CLYFAR_EXIT_CODE
fi

echo "================================================================"
echo "Clyfar forecast complete!"
echo "================================================================"

# ---------------------------------------------------------------------------
# Export + upload, then the LLM outlook.
#
# Both used to be inline here -- a ~95-line Python heredoc, then a ~130-line
# LLM block -- which welded them to the model run. Re-pushing a run after a
# host was unreachable, back-filling a newly added mirror, or regenerating a
# single meta-responded outlook all meant re-running this entire 2 h job.
#
# They are now scripts/push_clyfar_products.py and scripts/run_llm_stage.sh,
# each callable on its own against artifacts already on disk. This script
# orchestrates the three stages; it no longer implements two of them.
# ---------------------------------------------------------------------------

export CLYFAR_DIR DATA_ROOT FIG_ROOT EXPORT_DIR JSON_TESTS_ROOT

echo "================================================================"
echo "Exporting forecast data to BasinWx..."
PUSH_ARGS=()
if [ "$CLYFAR_ENABLE_UPLOAD" = "1" ]; then
    echo "Upload mode: ENABLED"
else
    echo "Upload mode: DISABLED (CLYFAR_ENABLE_UPLOAD=$CLYFAR_ENABLE_UPLOAD)"
    PUSH_ARGS+=(--no-upload)
fi

EXPORT_EXIT=0
python3 scripts/push_clyfar_products.py \
    --init "$INIT_TIME" \
    --data-root "$DATA_ROOT" \
    --fig-root "$FIG_ROOT" \
    --export-dir "$EXPORT_DIR" \
    --json-tests-root "$JSON_TESTS_ROOT" \
    "${PUSH_ARGS[@]}" || EXPORT_EXIT=$?

if [ $EXPORT_EXIT -ne 0 ]; then
    echo "WARNING: Export to BasinWx failed with exit code $EXPORT_EXIT"
    echo "ALERT_FORECAST_EXPORT_FAILED init=$INIT_TIME exit=$EXPORT_EXIT"
    echo "STATUS_FORECAST_EXPORT=FAILED init=$INIT_TIME exit=$EXPORT_EXIT"
    echo "  Retry without re-running the model:"
    echo "    scripts/push_clyfar_products.py --init $INIT_TIME"
    # Deliberately not fatal: the forecast data is saved locally regardless.
else
    echo "STATUS_FORECAST_EXPORT=SUCCESS init=$INIT_TIME"
fi

echo "================================================================"
echo "Generating LLM outlook..."
if [ "$CLYFAR_ENABLE_UPLOAD" = "1" ]; then
    unset LLM_SKIP_UPLOAD 2>/dev/null || true
else
    export LLM_SKIP_UPLOAD=1
fi

LLM_EXIT=0
"$CLYFAR_DIR/scripts/run_llm_stage.sh" "$INIT_TIME" || LLM_EXIT=$?
if [ $LLM_EXIT -ne 0 ]; then
    echo "WARNING: LLM stage exited $LLM_EXIT"
    echo "  Retry without re-running the model:"
    echo "    scripts/run_llm_stage.sh $INIT_TIME"
    # Deliberately not fatal: the forecast data is already exported.
fi

# Report completion
echo "================================================================"
echo "Job complete!"
echo "End time: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo "================================================================"
echo ""
echo "Output locations:"
echo "  Parquet data: $DATA_ROOT"
echo "  Figures: $FIG_ROOT"
echo "  JSON exports: $EXPORT_DIR"
echo "  CASE data: $JSON_TESTS_ROOT"
echo "  Logs: $LOG_DIR"
echo ""
echo "View job details: sacct -j $SLURM_JOB_ID --format=JobID,JobName,Elapsed,State,ExitCode"
