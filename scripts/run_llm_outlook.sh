#!/bin/bash
#####################################################################
# Clyfar / Ffion cron-parity LLM outlook runner
#####################################################################
# Purpose:
#   Repeatably test the same Ffion generation path used at the end of
#   scripts/submit_clyfar.sh, without rerunning the full GEFS pipeline.
#
# Cron-parity steps per init:
#   1) sync_case_from_local.py --history N
#   2) unset custom CLI overrides (unless --keep-cli-overrides)
#   3) set LLM_MAX_RETRIES (default 3, matching submit_clyfar.sh)
#   4) run LLM-GENERATE.sh locally on this node
#
# Usage:
#   Single init:
#     ./scripts/run_llm_outlook.sh 2026022400
#
#   Serial window (6-hourly, inclusive, chronological):
#     ./scripts/run_llm_outlook.sh --start 2026022000 --end 2026022400 --force
#
# Key defaults for test safety:
#   - Upload disabled (LLM_SKIP_UPLOAD=1). Use --upload to enable.
#   - Cron parity enabled by default.
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
    local exit_code="${1:-1}"
    cat <<'EOF'
Usage:
  scripts/run_llm_outlook.sh YYYYMMDDHH [OPTIONS]
  scripts/run_llm_outlook.sh --start YYYYMMDDHH --end YYYYMMDDHH [OPTIONS]

Options:
  --check                 Check prerequisites only, do not run LLM-GENERATE.sh
  --force                 Regenerate even if outlook markdown already exists
  --with-qa               Enable Q&A context via scripts/set_llm_qa.sh
  --history N             Number of previous inits to sync (default: 5)
  --retries N             LLM_MAX_RETRIES value (default: 3; cron parity)
  --upload                Enable outlook upload (default: disabled for testing)
  --keep-cli-overrides    Do not unset LLM_CLI_COMMAND/LLM_CLI_BIN/LLM_CLI_ARGS
  --start YYYYMMDDHH      First init in serial run (inclusive, 6-hour spacing)
  --end YYYYMMDDHH        Last init in serial run (inclusive, 6-hour spacing)
  --help                  Show this help
EOF
    exit "$exit_code"
}

validate_init() {
    local init="$1"
    [[ "$init" =~ ^[0-9]{10}$ ]]
}

normalise_init() {
    local init="$1"
    echo "${init:0:8}_${init:8:2}00Z"
}

build_init_list() {
    local start_init="$1"
    local end_init="$2"
    python3 - <<PY
from datetime import datetime, timedelta

start = datetime.strptime("${start_init}", "%Y%m%d%H")
end = datetime.strptime("${end_init}", "%Y%m%d%H")
if end < start:
    raise SystemExit("END_BEFORE_START")

cur = start
while cur <= end:
    print(cur.strftime("%Y%m%d%H"))
    cur += timedelta(hours=6)
PY
}

check_export_for_init() {
    local norm_init="$1"
    local count
    count=$(ls "$EXPORT_DIR"/*"$norm_init"*.json 2>/dev/null | wc -l || echo 0)
    if [[ "$count" -eq 0 ]]; then
        echo -e "${RED}ERROR:${NC} No export files found for $norm_init in $EXPORT_DIR"
        return 1
    fi
    echo -e "${GREEN}Found $count export files${NC} for $norm_init"
    return 0
}

verify_case_layout() {
    local case_dir="$1"
    local missing=()
    for subdir in percentiles possibilities probs weather; do
        local dir="$case_dir/$subdir"
        if [[ -d "$dir" ]]; then
            local count
            count=$(ls "$dir"/*.json 2>/dev/null | wc -l || echo 0)
            echo "  - $subdir: $count files"
        else
            echo "  - $subdir: missing"
            missing+=("$subdir")
        fi
    done
    if [[ ${#missing[@]} -gt 0 ]]; then
        echo -e "${YELLOW}WARNING:${NC} Missing CASE subdirs: ${missing[*]}"
    fi
}

add_texlive_to_path() {
    # Match submit_clyfar.sh behavior used by cron jobs.
    local texlive_bin="/uufs/chpc.utah.edu/sys/installdir/texlive/2022/bin/x86_64-linux"
    if [[ -d "$texlive_bin" ]]; then
        export PATH="$texlive_bin:$PATH"
        echo "Added texlive 2022 to PATH"
    else
        echo -e "${YELLOW}WARNING:${NC} texlive directory not found at $texlive_bin"
    fi
}

process_init() {
    local init_time="$1"
    local check_only="$2"
    local force="$3"
    local with_qa="$4"
    local history="$5"
    local retries="$6"
    local upload_enabled="$7"
    local keep_cli_overrides="$8"

    local norm_init
    norm_init="$(normalise_init "$init_time")"
    local case_dir="$DATA_ROOT/CASE_$norm_init"
    local outlook_file="$case_dir/llm_text/LLM-OUTLOOK-$norm_init.md"

    echo ""
    echo "================================================================"
    echo -e "${BLUE}Init ${init_time} (${norm_init})${NC}"
    echo "CASE dir: $case_dir"
    echo "================================================================"

    if [[ -f "$outlook_file" && "$force" == "false" && "$check_only" == "false" ]]; then
        echo -e "${YELLOW}Skipping:${NC} outlook already exists ($outlook_file)"
        return 0
    fi

    check_export_for_init "$norm_init" || return 1

    echo "Syncing CASE data (history=$history)..."
    python3 scripts/sync_case_from_local.py \
        --init "$init_time" \
        --source "$EXPORT_DIR" \
        --history "$history" \
        --overwrite

    echo "CASE layout:"
    verify_case_layout "$case_dir"

    if [[ "$check_only" == "true" ]]; then
        echo -e "${GREEN}Check-only mode:${NC} prerequisites look OK."
        return 0
    fi

    # Cron-parity defaults from submit_clyfar.sh
    if [[ "$keep_cli_overrides" == "false" ]]; then
        unset LLM_CLI_COMMAND LLM_CLI_BIN LLM_CLI_ARGS 2>/dev/null || true
    fi
    export PATH="$HOME/.local/bin:$PATH"
    add_texlive_to_path
    export LLM_MAX_RETRIES="$retries"

    if [[ "$upload_enabled" == "true" ]]; then
        unset LLM_SKIP_UPLOAD 2>/dev/null || true
    else
        export LLM_SKIP_UPLOAD=1
    fi

    if [[ "$with_qa" == "true" && -f "$CLYFAR_DIR/scripts/set_llm_qa.sh" ]]; then
        echo "Enabling Q&A context via scripts/set_llm_qa.sh"
        source "$CLYFAR_DIR/scripts/set_llm_qa.sh" 2>/dev/null || true
    fi

    echo "Running LLM-GENERATE.sh (LLM_MAX_RETRIES=$LLM_MAX_RETRIES, upload=$upload_enabled)..."
    "$CLYFAR_DIR/LLM-GENERATE.sh" "$init_time"

    if [[ ! -s "$outlook_file" ]]; then
        echo -e "${RED}ERROR:${NC} Outlook missing or empty after generation: $outlook_file"
        return 1
    fi

    local marker_count
    marker_count=$(rg -n "^AlertLevel_D1_5:|^Confidence_D1_5:|^AlertLevel_D6_10:|^Confidence_D6_10:|^AlertLevel_D11_15:|^Confidence_D11_15:" "$outlook_file" | wc -l || true)
    echo "Output markers found: $marker_count"
    return 0
}

main() {
    local init_time=""
    local start_init=""
    local end_init=""
    local check_only=false
    local force=false
    local with_qa=false
    local history=5
    local retries=3
    local upload_enabled=false
    local keep_cli_overrides=false

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --check)
                check_only=true
                shift
                ;;
            --force)
                force=true
                shift
                ;;
            --with-qa)
                with_qa=true
                shift
                ;;
            --history)
                history="$2"
                shift 2
                ;;
            --retries)
                retries="$2"
                shift 2
                ;;
            --upload)
                upload_enabled=true
                shift
                ;;
            --keep-cli-overrides)
                keep_cli_overrides=true
                shift
                ;;
            --start)
                start_init="$2"
                shift 2
                ;;
            --end)
                end_init="$2"
                shift 2
                ;;
            --help|-h)
                usage 0
                ;;
            *)
                if [[ -z "$init_time" ]]; then
                    init_time="$1"
                    shift
                else
                    echo -e "${RED}ERROR:${NC} Unknown argument: $1"
                    usage
                fi
                ;;
        esac
    done

    if [[ -n "$start_init" || -n "$end_init" ]]; then
        if [[ -z "$start_init" || -z "$end_init" ]]; then
            echo -e "${RED}ERROR:${NC} --start and --end must be provided together."
            usage
        fi
        if ! validate_init "$start_init" || ! validate_init "$end_init"; then
            echo -e "${RED}ERROR:${NC} --start/--end must be in YYYYMMDDHH format."
            usage
        fi
    elif [[ -n "$init_time" ]]; then
        if ! validate_init "$init_time"; then
            echo -e "${RED}ERROR:${NC} Invalid init format: $init_time (expected YYYYMMDDHH)"
            usage
        fi
    else
        echo -e "${RED}ERROR:${NC} Provide either one init or --start/--end."
        usage
    fi

    cd "$CLYFAR_DIR"

    local -a inits=()
    if [[ -n "$start_init" ]]; then
        if ! mapfile -t inits < <(build_init_list "$start_init" "$end_init"); then
            echo -e "${RED}ERROR:${NC} Could not build init list for range."
            exit 1
        fi
    else
        inits=("$init_time")
    fi

    echo "================================================================"
    echo -e "${BLUE}Clyfar/Ffion cron-parity test runner${NC}"
    echo "================================================================"
    echo "Inits: ${inits[*]}"
    echo "History: $history"
    echo "Retries (LLM_MAX_RETRIES): $retries"
    echo "Upload enabled: $upload_enabled"
    echo "Force regenerate: $force"
    echo "Check only: $check_only"
    echo "Keep CLI overrides: $keep_cli_overrides"
    echo "================================================================"

    local ok=0
    local fail=0
    for init in "${inits[@]}"; do
        if process_init "$init" "$check_only" "$force" "$with_qa" "$history" "$retries" "$upload_enabled" "$keep_cli_overrides"; then
            ok=$((ok + 1))
        else
            fail=$((fail + 1))
            echo -e "${RED}FAILED:${NC} $init"
        fi
    done

    echo ""
    echo "================================================================"
    echo "Summary: ok=$ok fail=$fail total=${#inits[@]}"
    echo "================================================================"

    if [[ "$fail" -gt 0 ]]; then
        exit 1
    fi
}

main "$@"
