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

if [[ ! -f "$INPUT" ]]; then
  echo "Input file not found: $INPUT" >&2
  exit 1
fi

pandoc "$INPUT" \
  --from markdown-yaml_metadata_block+lists_without_preceding_blankline \
  --pdf-engine=xelatex \
  --wrap=preserve \
  -V geometry:margin=0.75in \
  -V fontsize=11pt \
  -V mainfont="STIX" \
  -V documentclass=article \
  -V colorlinks=true \
  -o "$OUTPUT"
echo "Created: $OUTPUT ($(du -h "$OUTPUT" | cut -f1))"
