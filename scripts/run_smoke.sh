#!/usr/bin/env bash
set -euo pipefail

# Minimal smoke wrapper for the --testing CLI workflow.
# Usage: scripts/run_smoke.sh [YYYYMMDDHH]

default_run_root() {
  if [[ -n "${CLYFAR_RUN_ROOT:-}" ]]; then
    printf "%s\n" "${CLYFAR_RUN_ROOT}"
  elif [[ -n "${USER:-}" && -d "/scratch/general/vast/${USER}" ]]; then
    printf "/scratch/general/vast/%s/clyfar/smoke\n" "${USER}"
  else
    printf "%s/clyfar_%s/smoke\n" "${TMPDIR:-/tmp}" "${USER:-user}"
  fi
}

INIT_TIME="${1:-2025012506}"
NCPUS="${NCPUS:-2}"
NMEMBERS="${NMEMBERS:-2}"
RUN_ROOT="${RUN_ROOT:-$(default_run_root)}"
DATA_ROOT="${DATA_ROOT:-${RUN_ROOT}/data}"
FIG_ROOT="${FIG_ROOT:-${RUN_ROOT}/figures}"
LOG_DIR="${DATA_ROOT}/baseline_0_9/logs"
LOG_FILE="${LOG_DIR}/smoke_${INIT_TIME}.log"
PYTHON_BIN="${PYTHON_BIN:-python}"
OVERWRITE="${OVERWRITE:-0}"
PERFORMANCE_LOG="${PERFORMANCE_LOG:-${DATA_ROOT}/performance_log.txt}"

export CLYFAR_ENABLE_UPLOAD="${CLYFAR_ENABLE_UPLOAD:-0}"
export LLM_SKIP_UPLOAD="${LLM_SKIP_UPLOAD:-1}"
export CLYFAR_HERBIE_CACHE="${CLYFAR_HERBIE_CACHE:-${RUN_ROOT}/herbie_cache}"
export CLYFAR_PERFORMANCE_LOG="${CLYFAR_PERFORMANCE_LOG:-${PERFORMANCE_LOG}}"
export MPLCONFIGDIR="${MPLCONFIGDIR:-${RUN_ROOT}/mplconfig}"

mkdir -p "${LOG_DIR}" "${FIG_ROOT}" "${CLYFAR_HERBIE_CACHE}" "${MPLCONFIGDIR}"
echo "[run_smoke] $(date -Iseconds) init=${INIT_TIME} ncpus=${NCPUS} nmembers=${NMEMBERS}" | tee -a "${LOG_FILE}" >> "${CLYFAR_PERFORMANCE_LOG}"

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

echo "[run_smoke] $(date -Iseconds) completed init=${INIT_TIME}" | tee -a "${LOG_FILE}" >> "${CLYFAR_PERFORMANCE_LOG}"
echo "[run_smoke] outputs data=${DATA_ROOT} figures=${FIG_ROOT} log=${LOG_FILE}"
