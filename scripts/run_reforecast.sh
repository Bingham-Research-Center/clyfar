#!/usr/bin/env bash
set -euo pipefail

# Usage: scripts/run_reforecast.sh inits.txt "-n 4 -m 10 --testing" [DATA_ROOT] [FIG_ROOT]
#   inits.txt format: one init per line, e.g., 2024010100

default_run_root() {
  if [[ -n "${CLYFAR_RUN_ROOT:-}" ]]; then
    printf "%s\n" "${CLYFAR_RUN_ROOT}"
  elif [[ -n "${USER:-}" && -d "/scratch/general/vast/${USER}" ]]; then
    printf "/scratch/general/vast/%s/clyfar/reforecast\n" "${USER}"
  else
    printf "%s/clyfar_%s/reforecast\n" "${TMPDIR:-/tmp}" "${USER:-user}"
  fi
}

INITS_FILE=${1:-}
ARGS=${2:-"-n 4 -m 10"}
RUN_ROOT="${RUN_ROOT:-$(default_run_root)}"
DATA_ROOT=${3:-${DATA_ROOT:-"${RUN_ROOT}/data"}}
FIG_ROOT=${4:-${FIG_ROOT:-"${RUN_ROOT}/figures"}}
PYTHON_BIN="${PYTHON_BIN:-python}"

export CLYFAR_ENABLE_UPLOAD="${CLYFAR_ENABLE_UPLOAD:-0}"
export LLM_SKIP_UPLOAD="${LLM_SKIP_UPLOAD:-1}"
export CLYFAR_HERBIE_CACHE="${CLYFAR_HERBIE_CACHE:-${RUN_ROOT}/herbie_cache}"
export CLYFAR_PERFORMANCE_LOG="${CLYFAR_PERFORMANCE_LOG:-${DATA_ROOT}/performance_log.txt}"
export MPLCONFIGDIR="${MPLCONFIGDIR:-${RUN_ROOT}/mplconfig}"

if [[ -z "$INITS_FILE" || ! -f "$INITS_FILE" ]]; then
  echo "Provide an inits file (one init per line)." >&2
  exit 1
fi

mkdir -p "$DATA_ROOT" "$FIG_ROOT" "$CLYFAR_HERBIE_CACHE" "$MPLCONFIGDIR"

while IFS= read -r INIT; do
  [[ -z "$INIT" || "$INIT" =~ ^# ]] && continue
  echo "Running init $INIT ..."
  "${PYTHON_BIN}" run_gefs_clyfar.py -i "$INIT" -d "$DATA_ROOT" -f "$FIG_ROOT" $ARGS || true
done < "$INITS_FILE"
