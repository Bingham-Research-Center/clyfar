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
#   Manual:   sbatch submit_clyfar.sh [YYYYMMDDHH]
#   Cron:     30 4,10,16,22 * * * sbatch ~/gits/clyfar/scripts/submit_clyfar.sh
#
# Arguments:
#   $1: Optional forecast initialization time (YYYYMMDDHH)
#       If not provided, auto-detects most recent GEFS run
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

# Determine forecast initialization time
if [ $# -eq 1 ]; then
    # User provided init time (YYYYMMDDHH format)
    INIT_TIME=$1
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
MAX_RETRIES=3
RETRY_DELAY_MINUTES=30
EXIT_CODE_RETRY=75  # Must match run_gefs_clyfar.py

echo "Retry status: attempt $((RETRY_COUNT + 1)) of $((MAX_RETRIES + 1))"

# Run Clyfar forecast
echo "================================================================"
echo "Running Clyfar forecast for init time: $INIT_TIME"
echo "================================================================"

# Disable pipefail temporarily so we can capture exit code
set +e
python3 run_gefs_clyfar.py \
    -i "$INIT_TIME" \
    -d "$DATA_ROOT" \
    -f "$FIG_ROOT" \
    -n "$SLURM_CPUS_PER_TASK" \
    -m all \
    --log-fis

CLYFAR_EXIT_CODE=$?
set -e

# Handle exit codes
if [ $CLYFAR_EXIT_CODE -eq $EXIT_CODE_RETRY ]; then
    # Data not available yet - schedule retry
    if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
        NEW_RETRY_COUNT=$((RETRY_COUNT + 1))
        echo "================================================================"
        echo "GEFS data not available yet."
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

# Export PNG figures to BasinWx
print("Exporting PNG figures to BasinWx...")
fig_results = export_figures_to_basinwx(
    fig_root="$FIG_ROOT",
    init_dt=init_dt,
    upload=True
)
print(f"  Heatmap PNGs: {len(fig_results['heatmaps'])}")
print(f"  Meteogram PNGs: {len(fig_results['meteograms'])}")
EOF

EXPORT_EXIT_CODE=$?

if [ $EXPORT_EXIT_CODE -ne 0 ]; then
    echo "WARNING: Export to BasinWx failed with exit code $EXPORT_EXIT_CODE"
    # Don't exit - forecast data is still saved locally
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
