#!/bin/bash
#####################################################################
# Clyfar Storage Inventory
#####################################################################
# Audits storage usage across all Clyfar-related locations on CHPC.
#
# Usage:
#   scripts/storage_inventory.sh          # Read-only audit
#   scripts/storage_inventory.sh --clean  # Interactive cleanup
#
# Locations checked:
#   - Herbie cache (GRIB downloads)
#   - Scratch outputs (60-day auto-purge!)
#   - Home directory usage
#   - Archive (Cottonwood)
#
# Sources:
#   - CHPC File Storage Policies: https://www.chpc.utah.edu/documentation/policies/3.1FileStoragePolicies.php
#   - brc-tools/docs/CHPC-REFERENCE.md
#####################################################################

set -euo pipefail

# Colors for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

CLEAN_MODE=false
if [[ "${1:-}" == "--clean" ]]; then
    CLEAN_MODE=true
fi

# Storage locations
# Quotas, mount paths, and CHPC-wide policy live in the team reference:
#   ~/gits/brc-knowledge/scholarium/reference-base/resources/chpc-team-resource-inventory.md
# lawson-group6 is the current active archive store (group5 has shown autofs
# faults on some notch* nodes). Override CLYFAR_ARCHIVE_BASE to retarget.
HERBIE_CACHE="${CLYFAR_HERBIE_CACHE:-$HOME/gits/clyfar/data/herbie_cache}"
SCRATCH_TEST="${CLYFAR_SCRATCH_TEST:-/scratch/general/vast/$USER/clyfar_test}"
SCRATCH_PROD="${CLYFAR_SCRATCH_PROD:-/scratch/general/vast/$USER/clyfar}"
HOME_DATA="$HOME/basinwx-data/clyfar"
TMP_CACHE="/tmp/clyfar_herbie"
ARCHIVE_BASE="${CLYFAR_ARCHIVE_BASE:-/uufs/chpc.utah.edu/common/home/lawson-group6/clyfar}"

# Helper: Get directory size (returns "0" if doesn't exist)
get_size() {
    local path="$1"
    if [[ -d "$path" ]]; then
        du -sh "$path" 2>/dev/null | cut -f1
    else
        echo "N/A"
    fi
}

# Helper: Count subdirectories (forecast runs)
count_runs() {
    local path="$1"
    if [[ -d "$path" ]]; then
        find "$path" -maxdepth 1 -type d -name "20*" 2>/dev/null | wc -l | tr -d ' '
    else
        echo "0"
    fi
}

# Helper: Get oldest directory date
oldest_run() {
    local path="$1"
    if [[ -d "$path" ]]; then
        local oldest=$(find "$path" -maxdepth 1 -type d -name "20*" 2>/dev/null | sort | head -1 | xargs basename 2>/dev/null)
        if [[ -n "$oldest" ]]; then
            echo "$oldest"
        else
            echo "none"
        fi
    else
        echo "N/A"
    fi
}

# Helper: Days since file was last accessed
days_since_access() {
    local path="$1"
    if [[ -d "$path" ]]; then
        local oldest_file=$(find "$path" -type f -printf '%A@\n' 2>/dev/null | sort -n | head -1)
        if [[ -n "$oldest_file" ]]; then
            local now=$(date +%s)
            local days=$(( (now - ${oldest_file%.*}) / 86400 ))
            echo "$days"
        else
            echo "0"
        fi
    else
        echo "N/A"
    fi
}

# Helper: warn (don't fail) if the archive base parent volume is not mounted on this node.
# Cottonwood lawson-group{4,5,6} are autofs-triggered and can silently fault per-node;
# a script hardcoding one of them would otherwise no-op invisibly.
check_archive_mount() {
    local base="$1"
    local volume
    # Extract /uufs/chpc.utah.edu/common/home/lawson-groupN from the archive base
    volume=$(echo "$base" | sed -E 's|(/uufs/chpc\.utah\.edu/common/home/lawson-group[0-9]+).*|\1|')
    if [[ "$volume" == "$base" || -z "$volume" ]]; then
        return 0  # Not a recognised group path; skip check.
    fi
    if ! df -hT "$volume" >/dev/null 2>&1; then
        echo -e "${YELLOW}[!] WARNING: archive volume $volume is not mounted on $(hostname).${NC}"
        echo -e "${YELLOW}    Autofs may have faulted; try a different node, or set CLYFAR_ARCHIVE_BASE${NC}"
        echo -e "${YELLOW}    to another lawson-group{4,5,6} path. Continuing with local inventory.${NC}"
        echo ""
    fi
}

# Print header
echo ""
echo -e "${BLUE}=== CLYFAR STORAGE INVENTORY ===${NC}"
echo "Date: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo "Archive base: $ARCHIVE_BASE"
echo ""

check_archive_mount "$ARCHIVE_BASE"

# EPHEMERAL
echo -e "${YELLOW}EPHEMERAL (auto-wiped on reboot):${NC}"
if [[ -d "$TMP_CACHE" ]]; then
    echo "  $TMP_CACHE    $(get_size "$TMP_CACHE")"
else
    echo "  $TMP_CACHE    (not present)"
fi
echo ""

# SCRATCH
echo -e "${YELLOW}SCRATCH (60-day atime-based auto-purge):${NC}"
echo "  Files not accessed for >60 days are deleted automatically."
echo ""

for scratch_dir in "$SCRATCH_TEST" "$SCRATCH_PROD"; do
    if [[ -d "$scratch_dir" ]]; then
        echo "  $scratch_dir/"
        size=$(get_size "$scratch_dir")
        echo "    Total: $size"

        # Check v0p9 subdirectory
        v0p9_dir="$scratch_dir/v0p9"
        if [[ -d "$v0p9_dir" ]]; then
            runs=$(count_runs "$v0p9_dir")
            oldest=$(oldest_run "$v0p9_dir")
            echo "    v0p9/: $(get_size "$v0p9_dir") ($runs runs, oldest: $oldest)"
        fi

        # Check figs subdirectory
        figs_dir="$scratch_dir/figs"
        if [[ -d "$figs_dir" ]]; then
            runs=$(count_runs "$figs_dir")
            oldest=$(oldest_run "$figs_dir")
            echo "    figs/: $(get_size "$figs_dir") ($runs runs, oldest: $oldest)"
        fi

        # Warning if old data
        days=$(days_since_access "$scratch_dir")
        if [[ "$days" != "N/A" && "$days" -gt 30 ]]; then
            echo -e "    ${RED}[!] Data older than 30 days - archive before 60-day purge!${NC}"
        fi
    else
        echo "  $scratch_dir/    (not present)"
    fi
    echo ""
done

# CACHE
echo -e "${YELLOW}CACHE (manual cleanup):${NC}"
if [[ -d "$HERBIE_CACHE" ]]; then
    size=$(get_size "$HERBIE_CACHE")
    echo "  $HERBIE_CACHE"
    echo "    Size: $size"

    # Check for cfgrib indexes
    idx_dir="$HERBIE_CACHE/cfgrib_indexes"
    if [[ -d "$idx_dir" ]]; then
        idx_size=$(get_size "$idx_dir")
        echo "    cfgrib_indexes/: $idx_size"
    fi

    # Warning if large
    size_bytes=$(du -sb "$HERBIE_CACHE" 2>/dev/null | cut -f1)
    if [[ -n "$size_bytes" && "$size_bytes" -gt 1073741824 ]]; then  # >1GB
        echo -e "    ${RED}[!] Cache >1GB - consider clearing after successful run${NC}"
    fi
else
    echo "  $HERBIE_CACHE    (not present)"
fi
echo ""

# HOME
echo -e "${YELLOW}HOME (permanent, no auto-purge):${NC}"
home_used=$(df -h ~ 2>/dev/null | tail -1 | awk '{print $3}')
home_avail=$(df -h ~ 2>/dev/null | tail -1 | awk '{print $4}')
home_pct=$(df -h ~ 2>/dev/null | tail -1 | awk '{print $5}')
echo "  Home usage: $home_used used, $home_avail available ($home_pct)"

if [[ -d "$HOME_DATA" ]]; then
    echo "  $HOME_DATA: $(get_size "$HOME_DATA")"
else
    echo "  $HOME_DATA: (not present)"
fi
echo ""

# ARCHIVE
echo -e "${YELLOW}ARCHIVE (Cottonwood lawson-group{4,5,6}, no auto-purge):${NC}"
if [[ -d "$ARCHIVE_BASE" ]]; then
    echo "  $ARCHIVE_BASE"
    echo "    Size: $(get_size "$ARCHIVE_BASE")"
    runs=$(count_runs "$ARCHIVE_BASE/archive" 2>/dev/null || echo "0")
    echo "    Archived runs: $runs"
else
    echo "  $ARCHIVE_BASE"
    echo -e "    ${YELLOW}(not yet configured)${NC}"
fi
echo ""

# RECOMMENDATIONS
echo -e "${BLUE}RECOMMENDATIONS:${NC}"
echo "  1. Archive valuable runs to Cottonwood before 60-day scratch purge"
echo "  2. Clear Herbie cache after successful runs: rm -rf $HERBIE_CACHE/*"
echo "  3. Check quota: df -h ~"
echo ""
echo -e "${YELLOW}[!] AUTOMATION NOT YET ENABLED - manual cleanup only${NC}"
echo ""

# CLEAN MODE
if [[ "$CLEAN_MODE" == true ]]; then
    echo -e "${RED}=== CLEANUP MODE ===${NC}"
    echo ""

    # Herbie cache cleanup
    if [[ -d "$HERBIE_CACHE" ]]; then
        size=$(get_size "$HERBIE_CACHE")
        read -p "Clear Herbie cache ($size)? [y/N] " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf "$HERBIE_CACHE"/*
            echo -e "${GREEN}Herbie cache cleared${NC}"
        fi
    fi

    # Scratch cleanup (interactive per-run)
    for scratch_dir in "$SCRATCH_TEST" "$SCRATCH_PROD"; do
        if [[ -d "$scratch_dir/v0p9" ]]; then
            echo ""
            echo "Runs in $scratch_dir/v0p9/:"
            for run_dir in "$scratch_dir/v0p9"/20*/; do
                if [[ -d "$run_dir" ]]; then
                    run_name=$(basename "$run_dir")
                    run_size=$(get_size "$run_dir")
                    read -p "  Delete $run_name ($run_size)? [y/N/q] " -n 1 -r
                    echo
                    if [[ $REPLY =~ ^[Qq]$ ]]; then
                        break
                    elif [[ $REPLY =~ ^[Yy]$ ]]; then
                        rm -rf "$run_dir"
                        echo -e "    ${GREEN}Deleted${NC}"
                    fi
                fi
            done
        fi
    done

    echo ""
    echo -e "${GREEN}Cleanup complete${NC}"
fi
