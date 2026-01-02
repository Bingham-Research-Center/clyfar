#!/bin/bash
# Convert LLM outlook markdown to PDF
# Usage: ./scripts/outlook_to_pdf.sh <outlook.md> [output.pdf]

set -euo pipefail

# Load modern pandoc and texlive on CHPC
if command -v module &>/dev/null; then
  module load pandoc/2.19.2 texlive/2022 2>/dev/null || true
fi

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
