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
#
# PRODUCTION: Use DEFAULT path (do not set LLM_CLI_COMMAND)
#   Default uses: claude -p --model opus --allowedTools Read,Glob,Grep
#   WARNING: LLM_CLI_COMMAND is for debugging only; it causes meta-response failures

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
SKIP_BASHRC="${LLM_SKIP_BASHRC:-0}"
SKIP_UPLOAD="${LLM_SKIP_UPLOAD:-0}"
PYTHON_BIN="${PYTHON:-python}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Auto-source ~/.bashrc_basinwx for API key if not already set (ad-hoc runs)
if [[ "$SKIP_BASHRC" != "1" && -z "${DATA_UPLOAD_API_KEY:-}" && -f ~/.bashrc_basinwx ]]; then
  echo "Sourcing ~/.bashrc_basinwx for API credentials..."
  source ~/.bashrc_basinwx
fi

# Ensure ~/.local/bin is in PATH (claude CLI location)
export PATH="$HOME/.local/bin:$PATH"

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
JSON_TESTS_ROOT="$SCRIPT_DIR/data/json_tests"
CASE_DIR="$JSON_TESTS_ROOT/CASE_${DATE_PART}_${HOUR_PART}Z"
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
  echo ">>> Notes from this file will be used only where relevant."
  echo ""
fi

# Generate clustering summary if not present (for ensemble structure context)
CLUSTERING_FILE="$CASE_DIR/forecast_clustering_summary_${NORM_INIT}.json"
if [[ ! -f "$CLUSTERING_FILE" ]]; then
  echo "Generating clustering summary for $NORM_INIT..."
  if "$PYTHON_BIN" scripts/generate_clustering_summary.py "$NORM_INIT" 2>/dev/null; then
    echo "  Created: $CLUSTERING_FILE"
  else
    echo "  Warning: Could not generate clustering summary (non-fatal)"
  fi
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

# Retry configuration (override with LLM_MAX_RETRIES env var)
# Default 1 (no retry) to keep SLURM jobs predictable; set higher for ad-hoc runs
MAX_RETRIES="${LLM_MAX_RETRIES:-1}"
RETRY_DELAY=30  # seconds between retries

# Check CLI availability once before the retry loop
if [[ -z "$CLI_COMMAND" ]]; then
  if ! command -v "$CLI_BIN" >/dev/null 2>&1; then
    echo "CLI binary not found: $CLI_BIN (set LLM_CLI_COMMAND or LLM_CLI_BIN)" >&2
    echo "Hint: ensure ~/.local/bin is in PATH" >&2
    exit 1
  fi
fi

# Validation: detect meta-responses and incomplete output
validate_llm_output() {
  local file="$1"
  local errors=()

  [[ ! -f "$file" || ! -s "$file" ]] && errors+=("Empty/missing output")

  local lines
  lines=$(wc -l < "$file")
  [[ "$lines" -lt 50 ]] && errors+=("Too short: $lines lines (expected 50+)")

  local block_alerts=0
  for key in AlertLevel_D1_5 AlertLevel_D6_10 AlertLevel_D11_15; do
    if grep -q "^${key}:" "$file"; then
      block_alerts=$((block_alerts + 1))
    fi
  done
  if [[ "$block_alerts" -eq 0 ]]; then
    grep -q "^AlertLevel:" "$file" || errors+=("Missing AlertLevel:")
  elif [[ "$block_alerts" -ne 3 ]]; then
    errors+=("Missing block AlertLevel(s)")
  fi

  local block_conf=0
  for key in Confidence_D1_5 Confidence_D6_10 Confidence_D11_15; do
    if grep -q "^${key}:" "$file"; then
      block_conf=$((block_conf + 1))
    fi
  done
  if [[ "$block_conf" -eq 0 ]]; then
    grep -q "^Confidence:" "$file" || errors+=("Missing Confidence:")
  elif [[ "$block_conf" -ne 3 ]]; then
    errors+=("Missing block Confidence(s)")
  fi
  grep -q "## Days 1" "$file" || errors+=("Missing 'Days 1-5' section")

  # Meta-response detection
  if grep -qiE "I've completed|Would you like me|The key findings|ready for publication|save this to a file" "$file"; then
    errors+=("META-RESPONSE detected (LLM described task instead of completing it)")
  fi

  if [[ ${#errors[@]} -gt 0 ]]; then
    echo "----------------------------------------" >&2
    echo "LLM OUTPUT VALIDATION FAILED" >&2
    echo "----------------------------------------" >&2
    printf "  - %s\n" "${errors[@]}" >&2
    echo "----------------------------------------" >&2
    return 1
  fi
  echo "Validation passed: $lines lines, all markers present"
  return 0
}

# Retry loop: invoke LLM, post-process, validate
LLM_SUCCEEDED=false
for attempt in $(seq 1 "$MAX_RETRIES"); do
  echo ""
  echo "=== LLM attempt $attempt of $MAX_RETRIES ==="

  # Invoke LLM CLI
  CLI_OK=true
  if [[ -n "$CLI_COMMAND" ]]; then
    echo "Running custom CLI command: $CLI_COMMAND"
    if ! bash -lc "cd '$JSON_TESTS_ROOT' && $CLI_COMMAND --add-dir ." < "$PROMPT_PATH" > "$OUTPUT_PATH"; then
      echo "LLM CLI command failed (attempt $attempt)." >&2
      CLI_OK=false
    fi
  else
    # shellcheck disable=SC2206
    CLI_EXTRA=($CLI_ARGS)
    # Timeout prevents hangs in batch environments (10 min should be plenty)
    LLM_TIMEOUT="${LLM_TIMEOUT:-600}"
    echo "Running ${CLI_BIN} -p --model opus --allowedTools Read,Glob,Grep --permission-mode default --add-dir $JSON_TESTS_ROOT ${CLI_EXTRA[*]} (timeout ${LLM_TIMEOUT}s)"
    if ! timeout "$LLM_TIMEOUT" "$CLI_BIN" -p --model opus \
        --allowedTools "Read,Glob,Grep" \
        --permission-mode default \
        --add-dir "$JSON_TESTS_ROOT" \
        "${CLI_EXTRA[@]}" < "$PROMPT_PATH" > "$OUTPUT_PATH"; then
      echo "LLM CLI invocation failed (attempt $attempt)." >&2
      CLI_OK=false
    fi
  fi

  if [[ "$CLI_OK" == false ]]; then
    if [[ $attempt -lt $MAX_RETRIES ]]; then
      echo "Retrying in ${RETRY_DELAY}s..."
      sleep "$RETRY_DELAY"
      continue
    fi
    echo "All $MAX_RETRIES LLM attempts failed (CLI error)." >&2
    exit 1
  fi

  # Post-process: ensure output starts with "---" (strip any LLM preamble)
  if [[ -f "$OUTPUT_PATH" && -s "$OUTPUT_PATH" ]]; then
    first_line=$(head -1 "$OUTPUT_PATH")
    if [[ "$first_line" != "---" ]]; then
      if grep -q "^---$" "$OUTPUT_PATH"; then
        sed -i '1,/^---$/{/^---$/!d}' "$OUTPUT_PATH"
        echo "Post-processed: stripped preamble before first '---'"
      else
        sed -i '1i---' "$OUTPUT_PATH"
        echo "Post-processed: prepended '---' (was missing)"
      fi
    fi
  fi

  # Validate
  if [[ -f "$OUTPUT_PATH" ]] && validate_llm_output "$OUTPUT_PATH"; then
    LLM_SUCCEEDED=true
    break
  fi

  # Archive failed output
  ARCHIVE_DIR="$(dirname "$OUTPUT_PATH")/archive"
  mkdir -p "$ARCHIVE_DIR"
  ARCHIVE_FILE="$ARCHIVE_DIR/$(basename "$OUTPUT_PATH" .md)_failed_$(date +%s).md"
  cp "$OUTPUT_PATH" "$ARCHIVE_FILE"
  echo "Failed output archived to: $ARCHIVE_FILE"

  if [[ $attempt -lt $MAX_RETRIES ]]; then
    echo "Retrying in ${RETRY_DELAY}s..."
    sleep "$RETRY_DELAY"
  fi
done

if [[ "$LLM_SUCCEEDED" == false ]]; then
  echo "========================================" >&2
  echo "All $MAX_RETRIES LLM attempts failed validation." >&2
  echo "Manual retry: ./LLM-GENERATE.sh $INIT" >&2
  echo "========================================" >&2
  exit 2
fi

# Add texlive to PATH for PDF generation
# Note: CHPC module system has broken libreadline.so.6 dependency,
# so we add texlive bin directory directly to PATH.
# Pandoc 3.8+ is installed via conda in clyfar-nov2025 environment.
TEXLIVE_BIN="/uufs/chpc.utah.edu/sys/installdir/texlive/2022/bin/x86_64-linux"
if [[ -d "$TEXLIVE_BIN" ]]; then
  export PATH="$TEXLIVE_BIN:$PATH"
fi

# Generate PDF from the outlook markdown
if [[ -f "$OUTPUT_PATH" && -s "$OUTPUT_PATH" ]]; then
  PDF_PATH="${OUTPUT_PATH%.md}.pdf"
  if "$SCRIPT_DIR/scripts/outlook_to_pdf.sh" "$OUTPUT_PATH" "$PDF_PATH"; then
    echo "PDF generated: $PDF_PATH"
    # Upload PDF and markdown to BasinWx API
    if [[ "$SKIP_UPLOAD" == "1" ]]; then
      echo "Skipping outlook upload (LLM_SKIP_UPLOAD=1)"
    elif [[ -n "${DATA_UPLOAD_API_KEY:-}" ]]; then
      if "$PYTHON_BIN" -c "from export.to_basinwx import upload_outlook_to_basinwx; exit(0 if upload_outlook_to_basinwx('$PDF_PATH') else 1)"; then
        echo "PDF uploaded to BasinWx"
      else
        echo "Warning: PDF upload failed (non-fatal)" >&2
      fi
      if "$PYTHON_BIN" -c "from export.to_basinwx import upload_outlook_to_basinwx; exit(0 if upload_outlook_to_basinwx('$OUTPUT_PATH') else 1)"; then
        echo "Markdown uploaded to BasinWx"
      else
        echo "Warning: Markdown upload failed (non-fatal)" >&2
      fi
    else
      echo "Skipping outlook upload (DATA_UPLOAD_API_KEY not set)"
    fi
  else
    echo "Warning: PDF generation failed (non-fatal)" >&2
  fi
fi

echo "Done."
