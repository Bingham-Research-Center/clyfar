#!/bin/bash
# Convert LLM outlook markdown to PDF
# Usage: ./scripts/outlook_to_pdf.sh <outlook.md> [output.pdf]

set -euo pipefail

# NOTE: Module loading is now handled by submit_clyfar.sh before calling this script.
# The 'module' function isn't inherited by subprocesses anyway, so this was silently failing.
# Parent script exports PATH after module load, so pandoc/xelatex should be in PATH.

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <outlook.md> [output.pdf]" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

INPUT="$1"
OUTPUT="${2:-${INPUT%.md}.pdf}"
MAIN_FONT="${OUTLOOK_PDF_MAINFONT:-STIX}"
PDF_ENGINE="${OUTLOOK_PDF_ENGINE:-xelatex}"

if [[ ! -f "$INPUT" ]]; then
  echo "Input file not found: $INPUT" >&2
  exit 1
fi

run_pandoc_pdf() {
  local engine="$1"
  local font_args=()
  if [[ "$engine" == "xelatex" || "$engine" == "lualatex" ]]; then
    font_args=(-V "mainfont=$MAIN_FONT")
  fi

  pandoc "$INPUT" \
    --from markdown-yaml_metadata_block+lists_without_preceding_blankline \
    --standalone \
    --pdf-engine="$engine" \
    --wrap=preserve \
    -V geometry:margin=0.75in \
    -V papersize=letter \
    -V fontsize=11pt \
    -V documentclass=article \
    -V colorlinks=true \
    "${font_args[@]}" \
    -o "$OUTPUT"
}

if ! run_pandoc_pdf "$PDF_ENGINE"; then
  if [[ "$PDF_ENGINE" != "pdflatex" ]]; then
    echo "Primary PDF engine '$PDF_ENGINE' failed; retrying with pdflatex..." >&2
    run_pandoc_pdf "pdflatex"
  else
    exit 1
  fi
fi

echo "Created: $OUTPUT ($(du -h "$OUTPUT" | cut -f1))"
