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
# Purpose: Run Clyfar v0.9.5 ozone forecasts on CHPC compute nodes
#          instead of login nodes to avoid resource constraints
#
# Schedule: Run 4× daily at 04:30, 10:30, 16:30, 22:30 UTC
#           (4.5 hours after GEFS runs at 00Z, 06Z, 12Z, 18Z)
#           MST equivalents: 21:30, 03:30, 09:30, 15:30
#
# Usage:
#   Manual:   sbatch submit_clyfar.sh [YYYYMMDDHH] [--no-retry]
#   Cron:     30 4,10,16,22 * * * sbatch ~/gits/clyfar/scripts/submit_clyfar.sh
#
# Arguments:
#   $1: Optional forecast initialization time (YYYYMMDDHH)
#       If not provided, auto-detects most recent GEFS run
#   --no-retry: Disable automatic retry on transient failures (for ad-hoc runs)
#
# Environment variables required (set in ~/.bashrc_basinwx):
#   - DATA_UPLOAD_API_KEY
#   - BASINWX_API_URL
#   - SYNOPTIC_API_TOKEN (if used)
#
# Created by: John Lawson & Claude
# Last updated: 2025-11-23
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

# Set paths
CLYFAR_DIR=~/gits/clyfar
DATA_ROOT=~/basinwx-data/clyfar
FIG_ROOT=~/basinwx-data/clyfar/figures
EXPORT_DIR=~/basinwx-data/clyfar/basinwx_export
LOG_DIR=~/logs/basinwx

# Create directories if needed
mkdir -p "$DATA_ROOT" "$FIG_ROOT" "$EXPORT_DIR" "$LOG_DIR"

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
    # Auto-detect most recent GEFS run using Python datetime math
    # GEFS runs at 00Z, 06Z, 12Z, 18Z
    # We run 4.5hr after each cycle, so subtract 4.5hr and round down to nearest 6hr cycle

    INIT_TIME=$(python3 -c "
from datetime import datetime, timedelta

now_utc = datetime.utcnow()
# Subtract 4.5 hours to get approximate GEFS init time
target = now_utc - timedelta(hours=4, minutes=30)
# Round down to nearest 6-hour cycle (00, 06, 12, 18)
gefs_hour = (target.hour // 6) * 6
# Construct the init time
init_dt = target.replace(hour=gefs_hour, minute=0, second=0, microsecond=0)
print(init_dt.strftime('%Y%m%d%H'))
")

    GEFS_HOUR=${INIT_TIME:8:2}
    echo "Auto-detected init time: $INIT_TIME (GEFS ${GEFS_HOUR}Z run)"
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

# Disable pipefail temporarily so we can capture exit code
set +e

# On final retry, allow incomplete data (fill with NaNs)
INCOMPLETE_FLAG=""
if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
    echo "Final retry attempt - will proceed with incomplete data if needed"
    INCOMPLETE_FLAG="--allow-incomplete"
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
        echo "================================================================"
        exit 1
    fi
elif [ $CLYFAR_EXIT_CODE -ne 0 ]; then
    echo "ERROR: Clyfar forecast failed with exit code $CLYFAR_EXIT_CODE"
    exit $CLYFAR_EXIT_CODE
fi

echo "================================================================"
echo "Clyfar forecast complete!"
echo "================================================================"

# Export to BasinWx website (3 data products, 63 JSON files)
echo "Exporting forecast data to BasinWx..."

python3 - <<EOF
import os
import sys
from datetime import datetime
from pathlib import Path

# Add clyfar to path
sys.path.insert(0, "$CLYFAR_DIR")

from export.to_basinwx import export_all_products, export_figures_to_basinwx
import pandas as pd

# Parse init time
init_str = "$INIT_TIME"
init_dt = datetime.strptime(init_str, '%Y%m%d%H')

# Load daily max data
data_root = Path("$DATA_ROOT") / "dailymax"
if not data_root.exists():
    print(f"ERROR: Daily max data not found at {data_root}")
    sys.exit(1)

# Load all member dataframes
dailymax_df_dict = {}
for parquet_file in data_root.glob("clyfar*_dailymax.parquet"):
    member_name = parquet_file.stem.replace('_dailymax', '')
    df = pd.read_parquet(parquet_file)
    dailymax_df_dict[member_name] = df

if not dailymax_df_dict:
    print(f"ERROR: No daily max files found in {data_root}")
    sys.exit(1)

print(f"Loaded {len(dailymax_df_dict)} ensemble members")

# Export all products (upload=True to send to website)
results = export_all_products(
    dailymax_df_dict=dailymax_df_dict,
    init_dt=init_dt,
    output_dir="$EXPORT_DIR",
    upload=True  # Set to False for testing
)

total_files = len(results['possibility']) + len(results['exceedance']) + len(results['percentiles'])
print(f"Successfully exported {total_files} forecast files")
print(f"  Possibility heatmaps: {len(results['possibility'])}")
print(f"  Exceedance probabilities: {len(results['exceedance'])}")
print(f"  Percentile scenarios: {len(results['percentiles'])}")

# Export PNG figures and PDF outlooks to BasinWx
print("Exporting PNG figures and PDF outlooks to BasinWx...")
fig_results = export_figures_to_basinwx(
    fig_root="$FIG_ROOT",
    init_dt=init_dt,
    upload=True,
    json_tests_root="$DATA_ROOT/json_tests"
)
print(f"  Heatmap PNGs: {len(fig_results['heatmaps'])}")
print(f"  Meteogram PNGs: {len(fig_results['meteograms'])}")
print(f"  Outlook PDFs: {len(fig_results['outlooks'])}")
EOF

EXPORT_EXIT_CODE=$?

if [ $EXPORT_EXIT_CODE -ne 0 ]; then
    echo "WARNING: Export to BasinWx failed with exit code $EXPORT_EXIT_CODE"
    # Don't exit - forecast data is still saved locally
fi

# Generate LLM outlook (optional, non-blocking)
# This runs AFTER all Clyfar processing and exports are complete
echo "================================================================"
echo "Generating LLM outlook..."
echo "================================================================"

LLM_SUCCESS=false
if [ -f "$CLYFAR_DIR/LLM-GENERATE.sh" ]; then
    # Step 1: Sync CASE data from export directory
    echo "Syncing CASE data for LLM prompt generation..."
    python3 scripts/sync_case_from_local.py \
        --init "$INIT_TIME" \
        --source "$EXPORT_DIR" \
        --history 5 || {
        echo "WARNING: CASE sync failed, LLM may have incomplete context"
    }

    # Step 2: Enable Q&A context (solar bias warning)
    if [ -f "$CLYFAR_DIR/scripts/set_llm_qa.sh" ]; then
        source "$CLYFAR_DIR/scripts/set_llm_qa.sh" 2>/dev/null || true
    fi

    # Step 2.5: Load pandoc/texlive modules for PDF generation
    # These must be loaded in the SLURM job context (not just in outlook_to_pdf.sh)
    module load pandoc/2.19.2 texlive/2022 2>/dev/null || {
        echo "WARNING: Failed to load pandoc/texlive modules, PDF generation may fail"
    }

    # Step 3: Generate LLM outlook
    # Failures here don't block the pipeline - forecast data is already saved
    # IMPORTANT: Use default CLI path (unset custom commands to prevent meta-responses)
    unset LLM_CLI_COMMAND LLM_CLI_BIN LLM_CLI_ARGS 2>/dev/null || true

    echo "Running LLM-GENERATE.sh for init $INIT_TIME..."
    LLM_EXIT=0
    "$CLYFAR_DIR/LLM-GENERATE.sh" "$INIT_TIME" || LLM_EXIT=$?

    case $LLM_EXIT in
        0)
            LLM_SUCCESS=true
            ;;
        2)
            echo "WARNING: LLM output validation failed (meta-response detected)"
            echo "Manual regeneration required: ./LLM-GENERATE.sh $INIT_TIME"
            ;;
        *)
            echo "WARNING: LLM outlook generation failed (exit $LLM_EXIT)"
            echo "You can retry manually: ./LLM-GENERATE.sh $INIT_TIME"
            ;;
    esac

    if [ "$LLM_SUCCESS" = true ]; then
        OUTLOOK_FILE="$CLYFAR_DIR/data/json_tests/CASE_${INIT_TIME:0:8}_${INIT_TIME:8:2}00Z/llm_text/LLM-OUTLOOK-${INIT_TIME:0:8}_${INIT_TIME:8:2}00Z.md"
        if [ -f "$OUTLOOK_FILE" ]; then
            echo "LLM outlook generated: $OUTLOOK_FILE"
            # Extract and display AlertLevel
            grep -E "^AlertLevel:|^Confidence:" "$OUTLOOK_FILE" | head -2 || true
        fi
    fi
else
    echo "WARNING: LLM-GENERATE.sh not found, skipping outlook generation"
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
echo "  Logs: $LOG_DIR"
echo ""
echo "View job details: sacct -j $SLURM_JOB_ID --format=JobID,JobName,Elapsed,State,ExitCode"
