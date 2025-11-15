#!/usr/bin/env bash
set -euo pipefail

# Minimal smoke wrapper for the --testing CLI workflow.
# Usage: scripts/run_smoke.sh [YYYYMMDDHH]

INIT_TIME="${1:-2024010100}"
NCPUS="${NCPUS:-2}"
NMEMBERS="${NMEMBERS:-2}"
DATA_ROOT="${DATA_ROOT:-./data}"
FIG_ROOT="${FIG_ROOT:-./figures}"
LOG_DIR="${DATA_ROOT}/baseline_0_9/logs"
LOG_FILE="${LOG_DIR}/smoke_${INIT_TIME}.log"
PYTHON_BIN="${PYTHON_BIN:-python}"
OVERWRITE="${OVERWRITE:-0}"

mkdir -p "${LOG_DIR}"
echo "[run_smoke] $(date -Iseconds) init=${INIT_TIME} ncpus=${NCPUS} nmembers=${NMEMBERS}" | tee -a "${LOG_FILE}" >> performance_log.txt

if [[ "${OVERWRITE}" == "1" ]]; then
  rm -rf "${DATA_ROOT}/${INIT_TIME:0:8}_0000Z"
  rm -rf "${FIG_ROOT}/${INIT_TIME:0:8}_00Z"
fi

"${PYTHON_BIN}" run_gefs_clyfar.py \
  -i "${INIT_TIME}" \
  -n "${NCPUS}" \
  -m "${NMEMBERS}" \
  -d "${DATA_ROOT}" \
  -f "${FIG_ROOT}" \
  --testing \
  --log-fis \
  2>&1 | tee -a "${LOG_FILE}"

echo "[run_smoke] $(date -Iseconds) completed init=${INIT_TIME}" | tee -a "${LOG_FILE}" >> performance_log.txt
