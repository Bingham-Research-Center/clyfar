#!/bin/bash
# CHPC helper to generate Clyfar CASE plots + LLM prompt.
#
# This script is designed to be generic:
# - It uses environment variables for paths instead of hard-coding.
# - It can either fetch JSON from BasinWx API or operate on local CASE data.
#
# Usage:
#   ./CHPC-LLM-PROD.sh YYYYMMDDHH
# Example:
#   ./CHPC-LLM-PROD.sh 2025121200
#
# Recommended environment variables (set in ~/.bashrc_basinwx or job script):
#   CLYFAR_ROOT    - path to clyfar repo (e.g. ~/gits/clyfar)
#   BASINWX_API_URL - BasinWx base URL (e.g. https://basinwx.com)
#   LLM_FROM_API   - if set to 1, fetch JSON from website; otherwise use local CASE_*.
#
# Note: this script does NOT activate a conda env; do that in your job or shell first.
#       It can optionally request an interactive Slurm allocation for testing.

set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 YYYYMMDDHH"
  exit 1
fi

INIT="$1"  # e.g. 2025121200

CLYFAR_ROOT="${CLYFAR_ROOT:-$HOME/gits/clyfar}"
BASE_URL="${BASINWX_API_URL:-https://basinwx.com}"
FROM_API="${LLM_FROM_API:-1}"  # default: fetch from API

# Optional Slurm settings for auto-interactive mode
ACCOUNT="${LLM_SLURM_ACCOUNT:-}"
PARTITION="${LLM_SLURM_PARTITION:-}"
WALLTIME="${LLM_SLURM_WALLTIME:-00:30:00}"
CPUS="${LLM_SLURM_CPUS:-4}"
MEM="${LLM_SLURM_MEM:-8G}"

cd "$CLYFAR_ROOT"

export MPLCONFIGDIR="${MPLCONFIGDIR:-.mplconfig}"

echo "=== CHPC LLM PIPELINE ==="
echo "Repo root: $CLYFAR_ROOT"
echo "Init:      $INIT"
echo "Base URL:  $BASE_URL"
echo "From API:  $FROM_API"
echo

# If not already inside a Slurm job, optionally start an interactive allocation.
if [[ -z "${SLURM_JOB_ID:-}" ]]; then
  if [[ -n "$ACCOUNT" && -n "$PARTITION" ]]; then
    echo "No SLURM_JOB_ID detected. Requesting interactive Slurm session..."
    echo "Account:   $ACCOUNT"
    echo "Partition: $PARTITION"
    echo "Walltime:  $WALLTIME"
    echo "CPUs:      $CPUS"
    echo "Mem:       $MEM"
    echo
    salloc -A "$ACCOUNT" -p "$PARTITION" -t "$WALLTIME" --cpus-per-task="$CPUS" --mem="$MEM" --job-name="clyfar-llm-${INIT}" <<EOF
cd "$CLYFAR_ROOT"
export MPLCONFIGDIR="${MPLCONFIGDIR:-.mplconfig}"

if [[ "$FROM_API" == "1" ]]; then
  python scripts/run_case_pipeline.py --init "$INIT" --from-api --base-url "$BASE_URL"
else
  python scripts/run_case_pipeline.py --init "$INIT"
fi
EOF
    echo "Interactive Slurm session complete."
    exit 0
  else
    echo "No SLURM_JOB_ID and no LLM_SLURM_ACCOUNT/LLM_SLURM_PARTITION set."
    echo "Either:"
    echo "  1) Run this inside an existing interactive job (salloc/srun), or"
    echo "  2) Export LLM_SLURM_ACCOUNT and LLM_SLURM_PARTITION, then rerun."
    exit 1
  fi
fi

if [[ "$FROM_API" == "1" ]]; then
  python scripts/run_case_pipeline.py \
    --init "$INIT" \
    --from-api \
    --base-url "$BASE_URL"
else
  python scripts/run_case_pipeline.py \
    --init "$INIT"
fi

echo "Done. Check data/json_tests/CASE_* for outputs."
