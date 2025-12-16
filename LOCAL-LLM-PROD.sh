#!/bin/bash
# Local helper to generate Clyfar CASE plots + LLM prompt from BasinWx API.
#
# Usage:
#   ./LOCAL-LLM-PROD.sh YYYYMMDDHH
# Example:
#   ./LOCAL-LLM-PROD.sh 2025121200
#
# Assumptions:
# - You are running on your laptop / workstation.
# - This script lives in the clyfar repo root.
# - Conda env (e.g. clyfar-2025) is already activated.

set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 YYYYMMDDHH"
  exit 1
fi

INIT="$1"  # e.g. 2025121200
BASE_URL="${BASINWX_API_URL:-https://basinwx.com}"
HISTORY="${LLM_HISTORY:-5}"
QA_FILE="${LLM_QA_FILE:-}"

# Resolve repo root relative to this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Ensure Matplotlib config dir is local and writable
export MPLCONFIGDIR="${MPLCONFIGDIR:-.mplconfig}"

echo "=== LOCAL LLM PIPELINE ==="
echo "Repo root: $SCRIPT_DIR"
echo "Init:      $INIT"
echo "Base URL:  $BASE_URL"
echo "History:  $HISTORY"
if [[ -n "$QA_FILE" ]]; then
  echo "QA File: $QA_FILE"
fi
echo

cmd=(python scripts/run_case_pipeline.py --init "$INIT" --history "$HISTORY" --from-api --base-url "$BASE_URL")
if [[ -n "$QA_FILE" ]]; then
  cmd+=(--qa-file "$QA_FILE")
fi
"${cmd[@]}"

echo "Done. Check data/json_tests/CASE_* for outputs."
