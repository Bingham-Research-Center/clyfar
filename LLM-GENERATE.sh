#!/bin/bash
# Wrapper to render the Clyfar LLM prompt and send it to an LLM CLI.
# Usage:
#   ./LLM-GENERATE.sh YYYYMMDDHH
#   ./LLM-GENERATE.sh YYYYMMDD_HHMMZ
#
# Environment variables:
#   LLM_RENDER_PROMPT   (default 1)  - if set to 1, re-render the prompt file first
#   LLM_QA_FILE         - optional Q&A markdown passed to demo_llm_forecast_template.py
#   LLM_PROMPT_TEMPLATE - optional path to override templates/llm/prompt_body.md
#   LLM_OUTPUT_BASENAME - prefix for the LLM output file (default LLM-OUTLOOK)
#   LLM_CLI_COMMAND     - full shell command to run (reads prompt from STDIN)
#   LLM_CLI_BIN         - CLI binary name if LLM_CLI_COMMAND is unset (default claude)
#   LLM_CLI_ARGS        - arguments for LLM_CLI_BIN (space-separated; for complex quoting use LLM_CLI_COMMAND)

set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 YYYYMMDDHH | YYYYMMDD_HHMMZ" >&2
  exit 1
fi

INIT="$1"
RENDER_PROMPT="${LLM_RENDER_PROMPT:-1}"
QA_FILE="${LLM_QA_FILE:-}"
PROMPT_TEMPLATE="${LLM_PROMPT_TEMPLATE:-}"
OUTPUT_BASENAME="${LLM_OUTPUT_BASENAME:-LLM-OUTLOOK}"
CLI_COMMAND="${LLM_CLI_COMMAND:-}"
CLI_BIN="${LLM_CLI_BIN:-claude}"
CLI_ARGS="${LLM_CLI_ARGS:-}"
PYTHON_BIN="${PYTHON:-python}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Auto-detect Q&A file if not set via environment variable
DEFAULT_QA_FILE="$SCRIPT_DIR/data/llm_qa_context.md"
if [[ -z "$QA_FILE" && -f "$DEFAULT_QA_FILE" ]]; then
  QA_FILE="$DEFAULT_QA_FILE"
  echo "Auto-detected Q&A context file: $QA_FILE"
fi

normalise_init() {
  local raw="$1"
  if [[ "$raw" == *_*Z ]]; then
    echo "$raw"
    return
  fi
  if [[ "${#raw}" -eq 10 && "$raw" =~ ^[0-9]+$ ]]; then
    local date="${raw:0:8}"
    local hour="${raw:8:2}"
    echo "${date}_${hour}00Z"
    return
  fi
  echo "Unrecognised init format: $raw" >&2
  exit 1
}

NORM_INIT="$(normalise_init "$INIT")"
DATE_PART="${NORM_INIT:0:8}"
HOUR_PART="${NORM_INIT:9:4}"
CASE_DIR="$SCRIPT_DIR/data/json_tests/CASE_${DATE_PART}_${HOUR_PART}Z"
PROMPT_PATH="$CASE_DIR/llm_text/forecast_prompt_${NORM_INIT}.md"
OUTPUT_PATH="$CASE_DIR/llm_text/${OUTPUT_BASENAME}-${NORM_INIT}.md"

if [[ ! -d "$CASE_DIR" ]]; then
  echo "Case directory not found: $CASE_DIR" >&2
  echo "Run scripts/run_case_pipeline.py or sync CASE folders first." >&2
  exit 1
fi

# Warn if Q&A context is active
if [[ -n "$QA_FILE" ]]; then
  echo ""
  echo ">>> Q&A CONTEXT ACTIVE: $QA_FILE"
  echo ">>> Warnings from this file will appear in the LLM output."
  echo ">>> To disable: source scripts/set_llm_qa.sh off"
  echo ""
fi

if [[ "$RENDER_PROMPT" == "1" ]]; then
  cmd=("$PYTHON_BIN" scripts/demo_llm_forecast_template.py "$NORM_INIT")
  if [[ -n "$QA_FILE" ]]; then
    cmd+=(--qa-file "$QA_FILE")
  fi
  if [[ -n "$PROMPT_TEMPLATE" ]]; then
    cmd+=(--prompt-template "$PROMPT_TEMPLATE")
  fi
  echo "Rendering prompt via: ${cmd[*]}"
  "${cmd[@]}"
fi

if [[ ! -f "$PROMPT_PATH" ]]; then
  echo "Prompt file not found: $PROMPT_PATH" >&2
  exit 1
fi

mkdir -p "$(dirname "$OUTPUT_PATH")"
echo "Writing LLM output to: $OUTPUT_PATH"

if [[ -n "$CLI_COMMAND" ]]; then
  echo "Running custom CLI command: $CLI_COMMAND"
  # Run from CASE_DIR so --add-dir . works for file access
  if ! bash -lc "cd '$CASE_DIR' && $CLI_COMMAND --add-dir ." < "$PROMPT_PATH" > "$OUTPUT_PATH"; then
    echo "LLM CLI command failed." >&2
    exit 1
  fi
else
  if ! command -v "$CLI_BIN" >/dev/null 2>&1; then
    echo "CLI binary not found: $CLI_BIN (set LLM_CLI_COMMAND or LLM_CLI_BIN)" >&2
    exit 1
  fi
  # shellcheck disable=SC2206
  CLI_EXTRA=($CLI_ARGS)
  echo "Running ${CLI_BIN} -p --model opus --allowedTools Read,Glob,Grep --permission-mode default --add-dir $CASE_DIR ${CLI_EXTRA[*]}"
  if ! "$CLI_BIN" -p --model opus \
      --allowedTools "Read,Glob,Grep" \
      --permission-mode default \
      --add-dir "$CASE_DIR" \
      "${CLI_EXTRA[@]}" < "$PROMPT_PATH" > "$OUTPUT_PATH"; then
    echo "LLM CLI invocation failed." >&2
    exit 1
  fi
fi

# Post-process: ensure output starts with "---" (strip any LLM preamble)
if [[ -f "$OUTPUT_PATH" && -s "$OUTPUT_PATH" ]]; then
  first_line=$(head -1 "$OUTPUT_PATH")
  if [[ "$first_line" != "---" ]]; then
    if grep -q "^---$" "$OUTPUT_PATH"; then
      # Strip everything before first "---"
      sed -i '1,/^---$/{/^---$/!d}' "$OUTPUT_PATH"
      echo "Post-processed: stripped preamble before first '---'"
    else
      # No "---" found at all - prepend it as safety net
      sed -i '1i---' "$OUTPUT_PATH"
      echo "Post-processed: prepended '---' (was missing)"
    fi
  fi
fi

# Generate PDF from the outlook markdown
if [[ -f "$OUTPUT_PATH" && -s "$OUTPUT_PATH" ]]; then
  PDF_PATH="${OUTPUT_PATH%.md}.pdf"
  if "$SCRIPT_DIR/scripts/outlook_to_pdf.sh" "$OUTPUT_PATH" "$PDF_PATH"; then
    echo "PDF generated: $PDF_PATH"
    # Upload PDF to BasinWx API
    if [[ -n "${DATA_UPLOAD_API_KEY:-}" ]]; then
      if "$PYTHON_BIN" -c "from export.to_basinwx import upload_pdf_to_basinwx; exit(0 if upload_pdf_to_basinwx('$PDF_PATH') else 1)"; then
        echo "PDF uploaded to BasinWx"
      else
        echo "Warning: PDF upload failed (non-fatal)" >&2
      fi
    else
      echo "Skipping PDF upload (DATA_UPLOAD_API_KEY not set)"
    fi
  else
    echo "Warning: PDF generation failed (non-fatal)" >&2
  fi
fi

echo "Done."
