#!/bin/bash
#SBATCH --job-name=clyfar-llm-batch
#SBATCH --account=notchpeak-shared-short
#SBATCH --partition=notchpeak-shared-short
#SBATCH --time=04:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --output=/uufs/chpc.utah.edu/common/home/%u/logs/basinwx/llm_batch_%j.out
#SBATCH --error=/uufs/chpc.utah.edu/common/home/%u/logs/basinwx/llm_batch_%j.err
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=%u@utah.edu

#####################################################################
# Phase B: Sequential LLM Outlook Generation for 12 init times
# One-time recovery script for 20260131_1200Z through 20260203_0600Z
#####################################################################

set -euo pipefail

echo "================================================================"
echo "Phase B: Sequential LLM Outlook Generation"
echo "================================================================"
echo "Job ID: $SLURM_JOB_ID"
echo "Node: $SLURM_NODELIST"
echo "Start time: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo "================================================================"

# Load environment
source ~/.bashrc_basinwx
source ~/software/pkg/miniforge3/etc/profile.d/conda.sh
conda activate clyfar-nov2025

cd ~/gits/clyfar

# CRITICAL: Use default CLI path to prevent meta-response failures
unset LLM_CLI_COMMAND LLM_CLI_BIN LLM_CLI_ARGS 2>/dev/null || true

# Add texlive for PDF generation
export PATH="/uufs/chpc.utah.edu/sys/installdir/texlive/2022/bin/x86_64-linux:$PATH"

# All 12 init times in strict chronological order for dRisk/dt continuity
INITS=(
  20260131_1200Z
  20260131_1800Z
  20260201_0000Z
  20260201_0600Z
  20260201_1200Z
  20260201_1800Z
  20260202_0000Z
  20260202_0600Z
  20260202_1200Z
  20260202_1800Z
  20260203_0000Z
  20260203_0600Z
)

echo ""
echo "=== Pre-flight: verify ALL 12 CASE directories ==="
ALL_OK=true
for INIT in "${INITS[@]}"; do
  DIR="data/json_tests/CASE_${INIT}"
  POSS=$(ls "${DIR}/possibilities/" 2>/dev/null | wc -l)
  PERC=$(ls "${DIR}/percentiles/" 2>/dev/null | wc -l)
  PROB=$(ls "${DIR}/probs/" 2>/dev/null | wc -l)
  WEAT=$(ls "${DIR}/weather/" 2>/dev/null | wc -l)
  if [[ "$POSS" -ge 31 && "$PERC" -ge 31 && "$PROB" -ge 1 && "$WEAT" -ge 32 ]]; then
    echo "  ${INIT}: OK"
  else
    echo "  ${INIT}: INCOMPLETE (${POSS}/${PERC}/${PROB}/${WEAT}) <<<< BLOCKING"
    ALL_OK=false
  fi
done

if [[ "$ALL_OK" != "true" ]]; then
  echo ""
  echo "ABORT: Some CASE directories are incomplete. Run Phase A first."
  exit 1
fi

echo ""
echo "=== Sequential LLM generation (12 init times) ==="
echo "=== dRisk/dt chain: each outlook sees the previous one ==="
SUCCESSES=0
FAILURES=0

for INIT in "${INITS[@]}"; do
  # Convert YYYYMMDD_HHMMZ -> YYYYMMDDHH for LLM-GENERATE.sh
  INIT_SHORT="${INIT:0:8}${INIT:9:2}"

  echo ""
  echo "--- ${INIT} (arg: ${INIT_SHORT}) ---"
  echo "    Started: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"

  set +e
  ./LLM-GENERATE.sh "${INIT_SHORT}"
  EXIT_CODE=$?
  set -e

  if [[ $EXIT_CODE -eq 0 ]]; then
    echo "    SUCCESS"
    SUCCESSES=$((SUCCESSES + 1))
    # Show AlertLevel for quick sanity check
    grep -E "^AlertLevel:|^Confidence:" \
      "data/json_tests/CASE_${INIT}/llm_text/LLM-OUTLOOK-${INIT}.md" 2>/dev/null || true
  elif [[ $EXIT_CODE -eq 2 ]]; then
    echo "    VALIDATION FAILED (meta-response) - retry: ./LLM-GENERATE.sh ${INIT_SHORT}"
    FAILURES=$((FAILURES + 1))
  else
    echo "    ERROR (exit code ${EXIT_CODE})"
    FAILURES=$((FAILURES + 1))
  fi
done

echo ""
echo "========================================="
echo "COMPLETE: ${SUCCESSES} succeeded, ${FAILURES} failed out of 12"
echo "========================================="
echo ""
echo "=== PDF inventory ==="
for INIT in "${INITS[@]}"; do
  PDF="data/json_tests/CASE_${INIT}/llm_text/LLM-OUTLOOK-${INIT}.pdf"
  if [[ -f "$PDF" ]]; then
    SIZE=$(du -h "$PDF" | cut -f1)
    echo "  ${INIT}: ${SIZE}"
  else
    echo "  ${INIT}: MISSING"
  fi
done

echo ""
echo "=== Final verification ==="
for INIT in "${INITS[@]}"; do
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
echo "Phase B complete at $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo "================================================================"
