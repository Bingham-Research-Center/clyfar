#!/usr/bin/env bash
# Generate, validate and upload the LLM outlook for one init time.
#
# Lifted out of submit_clyfar.sh, which used to run this inline after the model
# and the export. Standing alone it can be re-run against an init whose forecast
# data already exists -- the common case being a meta-response from the LLM,
# which used to mean either hand-running LLM-GENERATE.sh and remembering the
# validate-then-upload dance, or re-running the whole 2 h Slurm job.
#
# Usage:
#   scripts/run_llm_stage.sh YYYYMMDDHH
#   LLM_SKIP_UPLOAD=1 scripts/run_llm_stage.sh YYYYMMDDHH   # generate only
#
# Exit codes:
#   0  outlook generated, validated and (unless skipped) uploaded
#   2  generated but failed validation -- the outlook is NOT uploaded
#   1  generation itself failed
#
# John Lawson & Claude, August 2026
set -euo pipefail

INIT_TIME="${1:-}"
if ! [[ "$INIT_TIME" =~ ^[0-9]{10}$ ]]; then
    echo "Usage: $0 YYYYMMDDHH" >&2
    exit 1
fi

CLYFAR_DIR="${CLYFAR_DIR:-$HOME/gits/clyfar}"
DATA_ROOT="${DATA_ROOT:-$HOME/basinwx-data/clyfar}"
EXPORT_DIR="${EXPORT_DIR:-$DATA_ROOT/basinwx_export}"
JSON_TESTS_ROOT="${JSON_TESTS_ROOT:-${CLYFAR_JSON_TESTS_ROOT:-$DATA_ROOT/json_tests}}"
SKIP_UPLOAD="${LLM_SKIP_UPLOAD:-0}"

CASE_DIR="$JSON_TESTS_ROOT/CASE_${INIT_TIME:0:8}_${INIT_TIME:8:2}00Z"
OUTLOOK_MD="$CASE_DIR/llm_text/LLM-OUTLOOK-${INIT_TIME:0:8}_${INIT_TIME:8:2}00Z.md"
OUTLOOK_PDF="$CASE_DIR/llm_text/LLM-OUTLOOK-${INIT_TIME:0:8}_${INIT_TIME:8:2}00Z.pdf"

cd "$CLYFAR_DIR"

echo "STATUS_LLM_STAGE=START init=$INIT_TIME"

if [ ! -f "$CLYFAR_DIR/LLM-GENERATE.sh" ]; then
    echo "ALERT_LLM_STAGE_FAILED init=$INIT_TIME reason=generator_script_missing"
    echo "STATUS_LLM_STAGE=FAILED init=$INIT_TIME"
    exit 1
fi

# Step 1: assemble the CASE bundle the prompt reads from.
echo "Syncing CASE data for LLM prompt generation..."
python3 scripts/sync_case_from_local.py \
    --init "$INIT_TIME" \
    --source "$EXPORT_DIR" \
    --target-root "$JSON_TESTS_ROOT" \
    --history 5 \
    --overwrite || echo "WARNING: CASE sync failed; LLM context may be incomplete"

# Step 2: texlive for the PDF. CHPC's module system has a broken
# libreadline.so.6 after restarts, so put the bin dir on PATH directly.
TEXLIVE_BIN="/uufs/chpc.utah.edu/sys/installdir/texlive/2022/bin/x86_64-linux"
if [[ -d "$TEXLIVE_BIN" ]]; then
    export PATH="$TEXLIVE_BIN:$PATH"
else
    echo "WARNING: texlive not found at $TEXLIVE_BIN; PDF may not build" >&2
fi

# claude CLI lives in ~/.local/bin, which ~/.bashrc_basinwx does not add.
export PATH="$HOME/.local/bin:$PATH"

# A custom CLI command is what causes meta-response failures -- force the
# default path. See LLM-SOP.md.
unset LLM_CLI_COMMAND LLM_CLI_BIN LLM_CLI_ARGS 2>/dev/null || true

export LLM_MAX_RETRIES="${LLM_MAX_RETRIES:-3}"
export LLM_TIMEOUT="${LLM_TIMEOUT:-600}"
if [ "$SKIP_UPLOAD" = "1" ]; then
    export LLM_SKIP_UPLOAD=1
else
    unset LLM_SKIP_UPLOAD 2>/dev/null || true
fi

echo "Running LLM-GENERATE.sh for init $INIT_TIME..."
LLM_EXIT=0
"$CLYFAR_DIR/LLM-GENERATE.sh" "$INIT_TIME" || LLM_EXIT=$?

case $LLM_EXIT in
    0) ;;
    2)
        echo "WARNING: LLM output validation failed (meta-response detected)"
        echo "ALERT_LLM_STAGE_FAILED init=$INIT_TIME exit=$LLM_EXIT reason=validation_failed"
        echo "STATUS_LLM_STAGE=FAILED init=$INIT_TIME"
        exit 2
        ;;
    *)
        echo "ALERT_LLM_STAGE_FAILED init=$INIT_TIME exit=$LLM_EXIT reason=generator_failed"
        echo "STATUS_LLM_STAGE=FAILED init=$INIT_TIME"
        exit 1
        ;;
esac

# Step 3: the outlook must exist and pass content validation before it ships.
if [ ! -f "$OUTLOOK_MD" ]; then
    echo "ALERT_LLM_STAGE_FAILED init=$INIT_TIME reason=outlook_missing"
    echo "STATUS_LLM_STAGE=FAILED init=$INIT_TIME"
    exit 1
fi

VALIDATOR="$CLYFAR_DIR/scripts/validate_llm_outlook.py"
if [ ! -f "$VALIDATOR" ]; then
    echo "ALERT_LLM_STAGE_FAILED init=$INIT_TIME reason=validator_missing"
    echo "STATUS_LLM_STAGE=FAILED init=$INIT_TIME"
    exit 1
fi

echo "Validating outlook content integrity..."
if ! python3 "$VALIDATOR" "$OUTLOOK_MD"; then
    echo "ALERT_LLM_STAGE_FAILED init=$INIT_TIME reason=post_generation_validation_failed"
    echo "STATUS_LLM_STAGE=FAILED init=$INIT_TIME"
    exit 2
fi

echo "STATUS_LLM_STAGE=SUCCESS init=$INIT_TIME"

# LLM-GENERATE.sh already uploads the PDF and the markdown itself (via
# upload_outlook_to_basinwx). submit_clyfar.sh used to push the PDF a second
# time right here, so every cycle uploaded it twice -- visible in the logs as
# STATUS_LLM_UPLOAD_PDF followed by STATUS_SUBMIT_LLM_PDF_PUSH. That duplicate
# is deliberately not carried over; report what the generator did instead.
if [ "$SKIP_UPLOAD" = "1" ]; then
    echo "STATUS_LLM_PDF=SKIPPED init=$INIT_TIME reason=LLM_SKIP_UPLOAD"
elif [ -f "$OUTLOOK_PDF" ]; then
    echo "STATUS_LLM_PDF=PRESENT init=$INIT_TIME pdf=$OUTLOOK_PDF (uploaded by LLM-GENERATE.sh)"
else
    echo "STATUS_LLM_PDF=MISSING init=$INIT_TIME"
fi
