#!/bin/bash
#SBATCH --job-name=clyfar-llm-retry2
#SBATCH --account=notchpeak-shared-short
#SBATCH --partition=notchpeak-shared-short
#SBATCH --time=04:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --output=/uufs/chpc.utah.edu/common/home/%u/logs/basinwx/llm_retry2_%j.out
#SBATCH --error=/uufs/chpc.utah.edu/common/home/%u/logs/basinwx/llm_retry2_%j.err
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=%u@utah.edu

#####################################################################
# Phase B retry 2: LLM generation for remaining failed init times
# Each init is retried up to 3 times before giving up
#####################################################################

set -euo pipefail

echo "================================================================"
echo "Phase B Retry 2: LLM Outlook Generation"
echo "================================================================"
echo "Job ID: $SLURM_JOB_ID"
echo "Start time: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo "================================================================"

source ~/.bashrc_basinwx
source ~/software/pkg/miniforge3/etc/profile.d/conda.sh
conda activate clyfar-nov2025

cd ~/gits/clyfar

unset LLM_CLI_COMMAND LLM_CLI_BIN LLM_CLI_ARGS 2>/dev/null || true
export PATH="/uufs/chpc.utah.edu/sys/installdir/texlive/2022/bin/x86_64-linux:$PATH"

# Remaining failed init times in chronological order
RETRY_INITS=(
  20260202_0000Z
  20260202_0600Z
  20260202_1800Z
  20260203_0000Z
)

MAX_ATTEMPTS=3
TOTAL_SUCCESSES=0
TOTAL_FAILURES=0

for INIT in "${RETRY_INITS[@]}"; do
  INIT_SHORT="${INIT:0:8}${INIT:9:2}"
  ATTEMPT=0
  SUCCESS=false

  while [[ $ATTEMPT -lt $MAX_ATTEMPTS && "$SUCCESS" == "false" ]]; do
    ATTEMPT=$((ATTEMPT + 1))
    echo ""
    echo "--- ${INIT} attempt ${ATTEMPT}/${MAX_ATTEMPTS} (arg: ${INIT_SHORT}) ---"
    echo "    Started: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"

    set +e
    ./LLM-GENERATE.sh "${INIT_SHORT}"
    EXIT_CODE=$?
    set -e

    if [[ $EXIT_CODE -eq 0 ]]; then
      echo "    SUCCESS on attempt ${ATTEMPT}"
      SUCCESS=true
      grep -E "^AlertLevel:|^Confidence:" \
        "data/json_tests/CASE_${INIT}/llm_text/LLM-OUTLOOK-${INIT}.md" 2>/dev/null || true
    elif [[ $EXIT_CODE -eq 2 ]]; then
      echo "    VALIDATION FAILED on attempt ${ATTEMPT}"
      if [[ $ATTEMPT -lt $MAX_ATTEMPTS ]]; then
        echo "    Retrying in 10 seconds..."
        sleep 10
      fi
    else
      echo "    ERROR (exit code ${EXIT_CODE}) on attempt ${ATTEMPT}"
      if [[ $ATTEMPT -lt $MAX_ATTEMPTS ]]; then
        echo "    Retrying in 10 seconds..."
        sleep 10
      fi
    fi
  done

  if [[ "$SUCCESS" == "true" ]]; then
    TOTAL_SUCCESSES=$((TOTAL_SUCCESSES + 1))
  else
    echo "    GAVE UP on ${INIT} after ${MAX_ATTEMPTS} attempts"
    TOTAL_FAILURES=$((TOTAL_FAILURES + 1))
  fi
done

echo ""
echo "========================================="
echo "RETRY 2 COMPLETE: ${TOTAL_SUCCESSES} succeeded, ${TOTAL_FAILURES} failed out of ${#RETRY_INITS[@]}"
echo "========================================="

echo ""
echo "=== Full 12-init verification ==="
ALL_INITS=(
  20260131_1200Z 20260131_1800Z
  20260201_0000Z 20260201_0600Z 20260201_1200Z 20260201_1800Z
  20260202_0000Z 20260202_0600Z 20260202_1200Z 20260202_1800Z
  20260203_0000Z 20260203_0600Z
)

PROBLEMS=0
for INIT in "${ALL_INITS[@]}"; do
  MD="data/json_tests/CASE_${INIT}/llm_text/LLM-OUTLOOK-${INIT}.md"
  PDF="data/json_tests/CASE_${INIT}/llm_text/LLM-OUTLOOK-${INIT}.pdf"
  MD_SIZE=$(stat -c%s "$MD" 2>/dev/null || echo 0)
  PDF_SIZE=$(stat -c%s "$PDF" 2>/dev/null || echo 0)
  if [[ "$MD_SIZE" -gt 10000 && "$PDF_SIZE" -gt 30000 ]]; then
    echo "  ${INIT}: OK (md=${MD_SIZE}B, pdf=${PDF_SIZE}B)"
  else
    echo "  ${INIT}: PROBLEM (md=${MD_SIZE}B, pdf=${PDF_SIZE}B)"
    PROBLEMS=$((PROBLEMS + 1))
  fi
done

if [[ $PROBLEMS -eq 0 ]]; then
  echo ""
  echo "ALL 12 OUTLOOKS COMPLETE"
else
  echo ""
  echo "${PROBLEMS} outlooks still have problems"
fi

echo ""
echo "================================================================"
echo "Retry 2 complete at $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo "================================================================"
