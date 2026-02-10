#!/bin/bash
#####################################################################
# Clyfar LLM Outlook Generator - Ad-hoc / Manual Run Script
#####################################################################
# Generates LLM outlooks for any init time, handling all prerequisites:
# - Syncs CASE data from export directory (or creates if missing)
# - Checks for required JSON files
# - Generates the LLM prompt and outlook
#
# Usage:
#   ./scripts/run_llm_outlook.sh YYYYMMDDHH [OPTIONS]
#
# Examples:
#   ./scripts/run_llm_outlook.sh 2025123100           # Standard run
#   ./scripts/run_llm_outlook.sh 2025123100 --check   # Check files only
#   ./scripts/run_llm_outlook.sh 2025123100 --force   # Regenerate even if exists
#   ./scripts/run_llm_outlook.sh 2025123100 --with-qa # Include operator Q&A notes
#
# For old case studies, ensure the export data exists in:
#   ~/basinwx-data/clyfar/basinwx_export/
#
# Created by: Claude Code
# Last updated: 2025-12-31
#####################################################################

set -euo pipefail

# Colors
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

# Paths
CLYFAR_DIR="${CLYFAR_DIR:-$HOME/gits/clyfar}"
EXPORT_DIR="${EXPORT_DIR:-$HOME/basinwx-data/clyfar/basinwx_export}"
DATA_ROOT="$CLYFAR_DIR/data/json_tests"

usage() {
    echo "Usage: $0 YYYYMMDDHH [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --check    Check prerequisites only, don't generate"
    echo "  --force    Regenerate even if outlook already exists"
    echo "  --with-qa  Include Q&A context from scripts/set_llm_qa.sh"
    echo "  --no-qa    Deprecated alias (default already omits Q&A)"
    echo "  --history N  Number of previous inits to sync (default: 5)"
    echo "  --help     Show this help"
    exit 1
}

# Parse arguments
INIT_TIME=""
CHECK_ONLY=false
FORCE=false
WITH_QA=false
HISTORY=5

while [[ $# -gt 0 ]]; do
    case $1 in
        --check)
            CHECK_ONLY=true
            shift
            ;;
        --force)
            FORCE=true
            shift
            ;;
        --with-qa)
            WITH_QA=true
            shift
            ;;
        --no-qa)
            WITH_QA=false
            shift
            ;;
        --history)
            HISTORY=$2
            shift 2
            ;;
        --help|-h)
            usage
            ;;
        *)
            if [[ -z "$INIT_TIME" ]]; then
                INIT_TIME=$1
            else
                echo "Unknown argument: $1"
                usage
            fi
            shift
            ;;
    esac
done

if [[ -z "$INIT_TIME" ]]; then
    echo -e "${RED}ERROR: Init time required${NC}"
    usage
fi

# Validate init time format
if ! [[ "$INIT_TIME" =~ ^[0-9]{10}$ ]]; then
    echo -e "${RED}ERROR: Invalid init time format. Expected YYYYMMDDHH, got: $INIT_TIME${NC}"
    exit 1
fi

# Convert to normalized format
NORM_INIT="${INIT_TIME:0:8}_${INIT_TIME:8:2}00Z"
CASE_DIR="$DATA_ROOT/CASE_$NORM_INIT"
OUTLOOK_FILE="$CASE_DIR/llm_text/LLM-OUTLOOK-$NORM_INIT.md"

echo "================================================================"
echo -e "${BLUE}Clyfar LLM Outlook Generator${NC}"
echo "================================================================"
echo "Init time: $INIT_TIME ($NORM_INIT)"
echo "CASE dir:  $CASE_DIR"
echo "Export:    $EXPORT_DIR"
echo "History:   $HISTORY previous runs"
echo "================================================================"
echo ""

# Check if outlook already exists
if [[ -f "$OUTLOOK_FILE" ]] && [[ "$FORCE" = false ]]; then
    echo -e "${YELLOW}Outlook already exists:${NC} $OUTLOOK_FILE"
    echo ""
    echo "Alert level from existing outlook:"
    grep -E "^AlertLevel:|^Confidence:" "$OUTLOOK_FILE" | head -2 || true
    echo ""
    echo "Use --force to regenerate."
    exit 0
fi

# Step 1: Check export data availability
echo -e "${BLUE}[1/5] Checking export data...${NC}"
EXPORT_COUNT=$(ls "$EXPORT_DIR"/*"$NORM_INIT"*.json 2>/dev/null | wc -l || echo 0)
if [[ "$EXPORT_COUNT" -eq 0 ]]; then
    echo -e "${RED}ERROR: No export files found for $NORM_INIT in $EXPORT_DIR${NC}"
    echo ""
    echo "Expected files like:"
    echo "  forecast_exceedance_probabilities_$NORM_INIT.json"
    echo "  forecast_possibility_heatmap_clyfar*_$NORM_INIT.json"
    echo ""
    echo "Options:"
    echo "  1. Run the full pipeline first: python run_gefs_clyfar.py -i $INIT_TIME ..."
    echo "  2. Check if data exists elsewhere and copy to $EXPORT_DIR"
    exit 1
fi
echo -e "${GREEN}Found $EXPORT_COUNT export files${NC}"

# Step 2: Sync CASE data
echo ""
echo -e "${BLUE}[2/5] Syncing CASE data...${NC}"
cd "$CLYFAR_DIR"
python3 scripts/sync_case_from_local.py \
    --init "$INIT_TIME" \
    --source "$EXPORT_DIR" \
    --history "$HISTORY"

# Step 3: Verify CASE directory structure
echo ""
echo -e "${BLUE}[3/5] Verifying CASE directory...${NC}"
MISSING=()
for subdir in percentiles possibilities probs weather; do
    dir="$CASE_DIR/$subdir"
    if [[ -d "$dir" ]]; then
        count=$(ls "$dir"/*.json 2>/dev/null | wc -l || echo 0)
        echo -e "  ${GREEN}✓${NC} $subdir: $count files"
    else
        echo -e "  ${RED}✗${NC} $subdir: missing"
        MISSING+=("$subdir")
    fi
done

if [[ ${#MISSING[@]} -gt 0 ]]; then
    echo ""
    echo -e "${YELLOW}WARNING: Missing subdirectories: ${MISSING[*]}${NC}"
    echo "LLM prompt will note these as missing."
fi

# Step 4: Check for previous outlooks (for comparison)
echo ""
echo -e "${BLUE}[4/5] Checking previous outlooks...${NC}"
PREV_OUTLOOKS=$(find "$DATA_ROOT" -name "LLM-OUTLOOK-*.md" -mmin -1080 2>/dev/null | wc -l || echo 0)
echo "Found $PREV_OUTLOOKS outlook files from past 18 hours"

if [[ "$CHECK_ONLY" = true ]]; then
    echo ""
    echo "================================================================"
    echo -e "${GREEN}Check complete. All prerequisites satisfied.${NC}"
    echo "Run without --check to generate the outlook."
    echo "================================================================"
    exit 0
fi

# Step 5: Generate LLM outlook
echo ""
echo -e "${BLUE}[5/5] Generating LLM outlook...${NC}"

# Enable Q&A context only when explicitly requested
if [[ "$WITH_QA" = true ]] && [[ -f "$CLYFAR_DIR/scripts/set_llm_qa.sh" ]]; then
    echo "Enabling Q&A context..."
    source "$CLYFAR_DIR/scripts/set_llm_qa.sh" 2>/dev/null || true
fi

# Run LLM generation
echo "Running LLM-GENERATE.sh..."
"$CLYFAR_DIR/LLM-GENERATE.sh" "$INIT_TIME"

# Verify output
echo ""
echo "================================================================"
if [[ -f "$OUTLOOK_FILE" ]]; then
    echo -e "${GREEN}SUCCESS: LLM outlook generated${NC}"
    echo ""
    echo "Output: $OUTLOOK_FILE"
    echo ""
    echo "Alert level:"
    grep -E "^AlertLevel:|^Confidence:" "$OUTLOOK_FILE" | head -2 || true
    echo ""

    # Show comparison with previous if available
    if [[ "$PREV_OUTLOOKS" -gt 0 ]]; then
        echo "Previous outlook comparison:"
        grep -i "previous outlook\|strengthened\|weakened" "$OUTLOOK_FILE" | head -3 || echo "  (no comparison text found)"
    fi
else
    echo -e "${RED}ERROR: Outlook file not created${NC}"
    echo "Check LLM-GENERATE.sh output above for errors."
    exit 1
fi
echo "================================================================"
