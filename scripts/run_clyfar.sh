#!/bin/bash
#####################################################################
# Clyfar Runner - Execute forecast with hardcoded test settings
#####################################################################
# Usage: scripts/run_clyfar.sh YYYYMMDDHH
# Example: scripts/run_clyfar.sh 2025112612
#
# Prerequisites:
#   1. source scripts/setup_env.sh
#   2. salloc -n 32 -N 1 -t 4:00:00 -A lawson-np -p lawson-np
#####################################################################

set -euo pipefail

# Validate argument
if [ $# -ne 1 ]; then
    echo "Usage: $0 YYYYMMDDHH"
    echo "Example: $0 2025112612"
    exit 1
fi

INIT_TIME="$1"

if ! [[ "$INIT_TIME" =~ ^[0-9]{10}$ ]]; then
    echo "ERROR: Invalid init time format. Expected YYYYMMDDHH, got: $INIT_TIME"
    exit 1
fi

# Hardcoded settings for testing/operations
NCPUS=20
NMEMBERS=31
DATA_ROOT="/scratch/general/vast/clyfar_test/v0p9"
FIG_ROOT="/scratch/general/vast/clyfar_test/figs"

echo "================================================================"
echo "Clyfar Forecast Run"
echo "================================================================"
echo "Init time:  $INIT_TIME"
echo "Members:    $NMEMBERS (c00 + p01-p30)"
echo "Workers:    $NCPUS"
echo "Data out:   $DATA_ROOT"
echo "Figs out:   $FIG_ROOT"
echo "Start:      $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo "================================================================"

python run_gefs_clyfar.py \
    -i "$INIT_TIME" \
    -n "$NCPUS" \
    -m "$NMEMBERS" \
    -d "$DATA_ROOT" \
    -f "$FIG_ROOT" \
    --visualise \
    --save

echo "================================================================"
echo "Complete: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo "================================================================"
