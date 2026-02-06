#!/bin/bash
#####################################################################
# Regenerate ALL LLM outlooks for 20260131_1200Z – 20260203_0600Z
# Runs serially in chronological order for dRisk/dt continuity.
# Stops immediately on any failure.
#
# Usage:
#   ./scripts/phase_b_regen_all.sh                    # run all 12
#   ./scripts/phase_b_regen_all.sh --start 20260202_0000Z  # resume
#####################################################################

set -euo pipefail

echo "================================================================"
echo "LLM Outlook Regeneration: 20260131_1200Z – 20260203_0600Z"
echo "================================================================"
echo "Start time: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo "================================================================"

# Load environment
source ~/.bashrc_basinwx
source ~/software/pkg/miniforge3/etc/profile.d/conda.sh
conda activate clyfar-nov2025

cd ~/gits/clyfar

# Prevent meta-response failures
unset LLM_CLI_COMMAND LLM_CLI_BIN LLM_CLI_ARGS 2>/dev/null || true

# texlive for PDF generation
export PATH="/uufs/chpc.utah.edu/sys/installdir/texlive/2022/bin/x86_64-linux:$PATH"

# All 12 init times in strict chronological order
ALL_INITS=(
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

# Handle --start argument for resuming
START_INIT=""
if [[ "${1:-}" == "--start" && -n "${2:-}" ]]; then
  START_INIT="$2"
  echo "Resuming from: ${START_INIT}"
fi

# Build the list of inits to process
INITS=()
SKIP=true
if [[ -z "$START_INIT" ]]; then
  SKIP=false
fi
for INIT in "${ALL_INITS[@]}"; do
  if [[ "$SKIP" == "true" && "$INIT" == "$START_INIT" ]]; then
    SKIP=false
  fi
  if [[ "$SKIP" == "false" ]]; then
    INITS+=("$INIT")
  fi
done

if [[ ${#INITS[@]} -eq 0 ]]; then
  echo "ERROR: --start ${START_INIT} not found in init list"
  echo "Valid inits: ${ALL_INITS[*]}"
  exit 1
fi

echo "Will process ${#INITS[@]} init times: ${INITS[*]}"
echo ""

# Pre-flight: verify CASE directories for inits we'll process
echo "=== Pre-flight: verify CASE directories ==="
for INIT in "${INITS[@]}"; do
  DIR="data/json_tests/CASE_${INIT}"
  POSS=$(ls "${DIR}/possibilities/" 2>/dev/null | wc -l)
  PERC=$(ls "${DIR}/percentiles/" 2>/dev/null | wc -l)
  PROB=$(ls "${DIR}/probs/" 2>/dev/null | wc -l)
  WEAT=$(ls "${DIR}/weather/" 2>/dev/null | wc -l)
  if [[ "$POSS" -ge 31 && "$PERC" -ge 31 && "$PROB" -ge 1 && "$WEAT" -ge 32 ]]; then
    echo "  ${INIT}: OK (poss=${POSS} perc=${PERC} prob=${PROB} wx=${WEAT})"
  else
    echo "  ${INIT}: INCOMPLETE (poss=${POSS} perc=${PERC} prob=${PROB} wx=${WEAT})"
    echo "ABORT: Fix data before running."
    exit 1
  fi
done

echo ""
echo "=== Sequential LLM generation (fail-fast) ==="
COMPLETED=0

for i in "${!INITS[@]}"; do
  INIT="${INITS[$i]}"
  INIT_SHORT="${INIT:0:8}${INIT:9:2}"

  echo ""
  echo "--- [$(( COMPLETED + 1 ))/${#INITS[@]}] ${INIT} ---"
  echo "    Started: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"

  set +e
  ./LLM-GENERATE.sh "${INIT_SHORT}"
  EXIT_CODE=$?
  set -e

  if [[ $EXIT_CODE -eq 0 ]]; then
    echo "    SUCCESS"
    grep -E "^AlertLevel:|^Confidence:" \
      "data/json_tests/CASE_${INIT}/llm_text/LLM-OUTLOOK-${INIT}.md" 2>/dev/null || true
    COMPLETED=$((COMPLETED + 1))
  else
    echo ""
    echo "========================================="
    echo "FAILED: ${INIT} (exit code ${EXIT_CODE})"
    if [[ $EXIT_CODE -eq 2 ]]; then
      echo "  Cause: validation failed (meta-response)"
    fi
    echo "  Completed: ${COMPLETED}/${#INITS[@]}"
    echo ""
    # Print remaining inits for resume
    REMAINING=()
    for j in $(seq "$i" $(( ${#INITS[@]} - 1 ))); do
      REMAINING+=("${INITS[$j]}")
    done
    echo "  To resume:"
    echo "    ./scripts/phase_b_regen_all.sh --start ${INIT}"
    echo ""
    echo "  Remaining inits: ${REMAINING[*]}"
    echo "========================================="
    exit 1
  fi
done

echo ""
echo "========================================="
echo "ALL ${#INITS[@]} OUTLOOKS GENERATED SUCCESSFULLY"
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
PROBLEMS=0
for INIT in "${INITS[@]}"; do
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

if [[ $PROBLEMS -gt 0 ]]; then
  echo ""
  echo "WARNING: ${PROBLEMS} outlooks have size problems despite exit code 0"
fi

echo ""
echo "================================================================"
echo "Complete at $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo "================================================================"
