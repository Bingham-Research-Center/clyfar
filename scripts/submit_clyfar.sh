#!/bin/bash
#SBATCH --job-name=clyfar-forecast
#SBATCH --account=notchpeak-shared-short
#SBATCH --partition=notchpeak-shared-short
#SBATCH --time=02:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=32G
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
# Schedule: Run 4× daily at 03:30, 09:30, 15:30, 21:30 UTC
#           (3.5 hours after GEFS runs at 00Z, 06Z, 12Z, 18Z)
#
# Usage:
#   Manual:   sbatch submit_clyfar.sh [YYYYMMDDHH]
#   Cron:     30 3,9,15,21 * * * sbatch ~/clyfar/scripts/submit_clyfar.sh
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
    # Auto-detect most recent GEFS run
    # GEFS runs at 00Z, 06Z, 12Z, 18Z
    # We run ~3.5hr later, so look back to find the appropriate cycle

    CURRENT_HOUR=$(date -u '+%H')
    CURRENT_DATE=$(date -u '+%Y%m%d')

    # Determine which GEFS cycle to use
    if [ "$CURRENT_HOUR" -ge 3 ] && [ "$CURRENT_HOUR" -lt 9 ]; then
        GEFS_HOUR="00"
    elif [ "$CURRENT_HOUR" -ge 9 ] && [ "$CURRENT_HOUR" -lt 15 ]; then
        GEFS_HOUR="06"
    elif [ "$CURRENT_HOUR" -ge 15 ] && [ "$CURRENT_HOUR" -lt 21 ]; then
        GEFS_HOUR="12"
    else
        # After 21Z or before 03Z - use 18Z (might be previous day)
        if [ "$CURRENT_HOUR" -lt 3 ]; then
            CURRENT_DATE=$(date -u -d "yesterday" '+%Y%m%d')
        fi
        GEFS_HOUR="18"
    fi

    INIT_TIME="${CURRENT_DATE}${GEFS_HOUR}"
    echo "Auto-detected init time: $INIT_TIME (GEFS ${GEFS_HOUR}Z run)"
fi

# Validate init time format
if ! [[ "$INIT_TIME" =~ ^[0-9]{10}$ ]]; then
    echo "ERROR: Invalid init time format. Expected YYYYMMDDHH, got: $INIT_TIME"
    exit 1
fi

# Check if GEFS data is available (optional pre-check)
echo "Checking for GEFS data availability..."
# TODO: Add Herbie check here to verify data exists before running
# herbie latest --model gefs --product pgrb2a --fxx 0

# Run Clyfar forecast
echo "================================================================"
echo "Running Clyfar forecast for init time: $INIT_TIME"
echo "================================================================"

python3 run_gefs_clyfar.py \
    -i "$INIT_TIME" \
    -d "$DATA_ROOT" \
    -f "$FIG_ROOT" \
    -n "$SLURM_CPUS_PER_TASK" \
    -m all \
    --log-fis

CLYFAR_EXIT_CODE=$?

if [ $CLYFAR_EXIT_CODE -ne 0 ]; then
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
