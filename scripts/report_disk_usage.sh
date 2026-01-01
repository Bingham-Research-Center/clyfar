#!/bin/bash
#####################################################################
# Clyfar Disk Usage Report
#####################################################################
# Identifies large files and directories for manual cleanup.
# Run periodically to monitor storage usage.
#
# Usage: ./scripts/report_disk_usage.sh
#####################################################################

set -euo pipefail

# Colors for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "================================================================"
echo -e "${BLUE}Clyfar Disk Usage Report${NC}"
echo "Generated: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo "================================================================"
echo ""

# Define paths
CLYFAR_DIR="${CLYFAR_DIR:-$HOME/gits/clyfar}"
DATA_ROOT="${DATA_ROOT:-$HOME/basinwx-data/clyfar}"
FIG_ROOT="${FIG_ROOT:-$HOME/basinwx-data/clyfar/figures}"

# Function to format size with color coding
format_size() {
    local size=$1
    local path=$2
    local size_num=$(echo "$size" | sed 's/[A-Za-z]//g')
    local size_unit=$(echo "$size" | sed 's/[0-9.]//g')

    # Color code based on size
    if [[ "$size_unit" == "G" ]]; then
        echo -e "${RED}$size${NC}\t$path"
    elif [[ "$size_unit" == "M" ]] && (( $(echo "$size_num > 100" | bc -l) )); then
        echo -e "${YELLOW}$size${NC}\t$path"
    else
        echo -e "${GREEN}$size${NC}\t$path"
    fi
}

echo -e "${BLUE}=== TOP-LEVEL DIRECTORY SIZES ===${NC}"
echo ""

echo "Production data root ($DATA_ROOT):"
if [ -d "$DATA_ROOT" ]; then
    du -sh "$DATA_ROOT" 2>/dev/null | while read size path; do
        format_size "$size" "$path"
    done
    echo ""
    echo "Subdirectory breakdown:"
    du -sh "$DATA_ROOT"/* 2>/dev/null | sort -hr | head -15 | while read size path; do
        format_size "$size" "$path"
    done
else
    echo "  (not found)"
fi
echo ""

echo "Local repo data ($CLYFAR_DIR/data):"
if [ -d "$CLYFAR_DIR/data" ]; then
    du -sh "$CLYFAR_DIR/data" 2>/dev/null | while read size path; do
        format_size "$size" "$path"
    done
    echo ""
    echo "Subdirectory breakdown:"
    du -sh "$CLYFAR_DIR/data"/* 2>/dev/null | sort -hr | head -10 | while read size path; do
        format_size "$size" "$path"
    done
else
    echo "  (not found)"
fi
echo ""

echo -e "${BLUE}=== FIGURES DIRECTORY (usually largest) ===${NC}"
echo ""
if [ -d "$FIG_ROOT" ]; then
    du -sh "$FIG_ROOT" 2>/dev/null | while read size path; do
        format_size "$size" "$path"
    done
    echo ""
    echo "Subdirectory breakdown:"
    du -sh "$FIG_ROOT"/* 2>/dev/null | sort -hr | head -10 | while read size path; do
        format_size "$size" "$path"
    done
else
    echo "  (not found)"
fi
echo ""

echo -e "${BLUE}=== ARCHIVED RUN DIRECTORIES ===${NC}"
echo ""
RUN_DIRS=$(find "$DATA_ROOT" -maxdepth 1 -type d -name "*_run" 2>/dev/null | wc -l)
echo "Number of archived _run directories: $RUN_DIRS"
if [ "$RUN_DIRS" -gt 0 ]; then
    echo "Total size of _run directories:"
    du -shc "$DATA_ROOT"/*_run 2>/dev/null | tail -1 | while read size path; do
        format_size "$size" "all _run directories combined"
    done
    echo ""
    echo "Oldest 5 _run directories (candidates for cleanup):"
    ls -1d "$DATA_ROOT"/*_run 2>/dev/null | sort | head -5 | while read dir; do
        size=$(du -sh "$dir" 2>/dev/null | cut -f1)
        format_size "$size" "$dir"
    done
fi
echo ""

echo -e "${BLUE}=== CASE DIRECTORIES (json_tests) ===${NC}"
echo ""
CASE_DIR="$CLYFAR_DIR/data/json_tests"
if [ -d "$CASE_DIR" ]; then
    CASE_COUNT=$(ls -1d "$CASE_DIR"/CASE_* 2>/dev/null | wc -l)
    echo "Number of CASE directories: $CASE_COUNT"
    du -sh "$CASE_DIR" 2>/dev/null | while read size path; do
        format_size "$size" "$path"
    done
    echo ""
    echo "Oldest 5 CASE directories (candidates for cleanup):"
    ls -1d "$CASE_DIR"/CASE_* 2>/dev/null | sort | head -5 | while read dir; do
        size=$(du -sh "$dir" 2>/dev/null | cut -f1)
        format_size "$size" "$dir"
    done
fi
echo ""

echo -e "${BLUE}=== LARGE FILES (>10MB) ===${NC}"
echo ""
echo "Searching for files >10MB (this may take a moment)..."
LARGE_FILES=$(find "$DATA_ROOT" "$CLYFAR_DIR/data" -type f -size +10M 2>/dev/null | wc -l)
echo "Found $LARGE_FILES files larger than 10MB"
if [ "$LARGE_FILES" -gt 0 ]; then
    echo ""
    echo "Top 15 largest files:"
    find "$DATA_ROOT" "$CLYFAR_DIR/data" -type f -size +10M -exec du -h {} \; 2>/dev/null | sort -hr | head -15 | while read size path; do
        format_size "$size" "$path"
    done
fi
echo ""

echo -e "${BLUE}=== LOG FILES ===${NC}"
echo ""
LOG_DIR="$HOME/logs/basinwx"
if [ -d "$LOG_DIR" ]; then
    du -sh "$LOG_DIR" 2>/dev/null | while read size path; do
        format_size "$size" "$path"
    done
    LOG_COUNT=$(ls -1 "$LOG_DIR"/*.{out,err} 2>/dev/null | wc -l)
    echo "Number of log files: $LOG_COUNT"
    echo ""
    echo "Largest log files:"
    ls -lhS "$LOG_DIR"/*.{out,err} 2>/dev/null | head -5 | awk '{print $5"\t"$9}' | while read size path; do
        format_size "$size" "$path"
    done
else
    echo "  (not found)"
fi
echo ""

echo -e "${BLUE}=== CLEANUP SUGGESTIONS ===${NC}"
echo ""
echo "To free up space, consider:"
echo ""
echo "1. Remove old figures (keeping last 7 days):"
echo -e "   ${YELLOW}find $FIG_ROOT -type f -mtime +7 -delete${NC}"
echo ""
echo "2. Remove old _run archives (keeping last 10):"
echo -e "   ${YELLOW}ls -1d $DATA_ROOT/*_run | sort | head -n -10 | xargs rm -rf${NC}"
echo ""
echo "3. Remove old CASE directories (keeping last 20):"
echo -e "   ${YELLOW}ls -1d $CASE_DIR/CASE_* | sort | head -n -20 | xargs rm -rf${NC}"
echo ""
echo "4. Compress old log files:"
echo -e "   ${YELLOW}gzip $LOG_DIR/*.{out,err}${NC}"
echo ""
echo "================================================================"
echo "Report complete."
echo "================================================================"
