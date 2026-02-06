#!/bin/bash
#SBATCH --job-name=clyfar-llm-retry
#SBATCH --account=notchpeak-shared-short
#SBATCH --partition=notchpeak-shared-short
#SBATCH --time=04:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --output=/uufs/chpc.utah.edu/common/home/%u/logs/basinwx/llm_retry_%j.out
#SBATCH --error=/uufs/chpc.utah.edu/common/home/%u/logs/basinwx/llm_retry_%j.err
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=%u@utah.edu

#####################################################################
# Phase B retry: Sequential LLM generation for failed init times
#####################################################################

set -euo pipefail

echo "================================================================"
echo "Phase B Retry: LLM Outlook Generation for failed init times"
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

# Failed init times from first Phase B run, in chronological order
RETRY_INITS=(
  20260202_0000Z
  20260202_0600Z
  20260202_1800Z
  20260203_0000Z
  20260203_0600Z
)

SUCCESSES=0
FAILURES=0

for INIT in "${RETRY_INITS[@]}"; do
  INIT_SHORT="${INIT:0:8}${INIT:9:2}"

  echo ""
  echo "--- RETRY: ${INIT} (arg: ${INIT_SHORT}) ---"
  echo "    Started: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"

  set +e
  ./LLM-GENERATE.sh "${INIT_SHORT}"
  EXIT_CODE=$?
  set -e

  if [[ $EXIT_CODE -eq 0 ]]; then
    echo "    SUCCESS"
    SUCCESSES=$((SUCCESSES + 1))
    grep -E "^AlertLevel:|^Confidence:" \
      "data/json_tests/CASE_${INIT}/llm_text/LLM-OUTLOOK-${INIT}.md" 2>/dev/null || true
  elif [[ $EXIT_CODE -eq 2 ]]; then
    echo "    VALIDATION FAILED (meta-response) - retry manually: ./LLM-GENERATE.sh ${INIT_SHORT}"
    FAILURES=$((FAILURES + 1))
  else
    echo "    ERROR (exit code ${EXIT_CODE})"
    FAILURES=$((FAILURES + 1))
  fi
done

echo ""
echo "========================================="
echo "RETRY COMPLETE: ${SUCCESSES} succeeded, ${FAILURES} failed out of ${#RETRY_INITS[@]}"
echo "========================================="

echo ""
echo "=== Full 12-init verification ==="
ALL_INITS=(
  20260131_1200Z 20260131_1800Z
  20260201_0000Z 20260201_0600Z 20260201_1200Z 20260201_1800Z
  20260202_0000Z 20260202_0600Z 20260202_1200Z 20260202_1800Z
  20260203_0000Z 20260203_0600Z
)

for INIT in "${ALL_INITS[@]}"; do
  MD="data/json_tests/CASE_${INIT}/llm_text/LLM-OUTLOOK-${INIT}.md"
  PDF="data/json_tests/CASE_${INIT}/llm_text/LLM-OUTLOOK-${INIT}.pdf"
  MD_SIZE=$(stat -c%s "$MD" 2>/dev/null || echo 0)
  PDF_SIZE=$(stat -c%s "$PDF" 2>/dev/null || echo 0)
  if [[ "$MD_SIZE" -gt 10000 && "$PDF_SIZE" -gt 30000 ]]; then
    echo "  ${INIT}: OK (md=${MD_SIZE}B, pdf=${PDF_SIZE}B)"
  else
    echo "  ${INIT}: PROBLEM (md=${MD_SIZE}B, pdf=${PDF_SIZE}B)"
  fi
done

echo ""
echo "================================================================"
echo "Retry complete at $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo "================================================================"
