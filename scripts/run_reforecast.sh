#!/usr/bin/env bash
set -euo pipefail

# Usage: scripts/run_reforecast.sh inits.txt "-n 4 -m 10 --testing" ./data ./figures
#   inits.txt format: one init per line, e.g., 2024010100

INITS_FILE=${1:-}
ARGS=${2:-"-n 4 -m 10"}
DATA_ROOT=${3:-"./data"}
FIG_ROOT=${4:-"./figures"}

if [[ -z "$INITS_FILE" || ! -f "$INITS_FILE" ]]; then
  echo "Provide an inits file (one init per line)." >&2
  exit 1
fi

while IFS= read -r INIT; do
  [[ -z "$INIT" ]] && continue
  echo "Running init $INIT ..."
  python run_gefs_clyfar.py -i "$INIT" -d "$DATA_ROOT" -f "$FIG_ROOT" $ARGS || true
done < "$INITS_FILE"

