#!/bin/bash
# set_llm_qa.sh - Enable or disable versioned QA/operator notes for Ffion.
#
# Usage:
#   source scripts/set_llm_qa.sh
#   source scripts/set_llm_qa.sh off
#   source scripts/set_llm_qa.sh --science-version 1.0.0
#   source scripts/set_llm_qa.sh --science-manifest templates/llm/science/ffion_science_v1.0.0.json
#   source scripts/set_llm_qa.sh --qa-file /path/to/notes.md
#
# This no longer stores editable science inside the shell script. The default QA
# content lives in versioned files under templates/llm/qa/ and is resolved
# through the prompt-science bundle.

show_usage() {
    cat <<'EOF'
Usage:
  source scripts/set_llm_qa.sh
  source scripts/set_llm_qa.sh off
  source scripts/set_llm_qa.sh --science-version VERSION
  source scripts/set_llm_qa.sh --science-manifest PATH
  source scripts/set_llm_qa.sh --qa-file PATH
EOF
}

disable_qa() {
    unset LLM_QA_FILE
    echo "Q&A context DISABLED - LLM will not include special guidance"
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

SCIENCE_VERSION=""
SCIENCE_MANIFEST=""
QA_FILE_OVERRIDE=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        off|disable|clear)
            disable_qa
            return 0 2>/dev/null || exit 0
            ;;
        --science-version)
            SCIENCE_VERSION="${2:-}"
            shift 2
            ;;
        --science-manifest)
            SCIENCE_MANIFEST="${2:-}"
            shift 2
            ;;
        --qa-file)
            QA_FILE_OVERRIDE="${2:-}"
            shift 2
            ;;
        --help|-h)
            show_usage
            return 0 2>/dev/null || exit 0
            ;;
        *)
            echo "Unknown argument: $1" >&2
            show_usage >&2
            return 1 2>/dev/null || exit 1
            ;;
    esac
done

if [[ -n "$QA_FILE_OVERRIDE" ]]; then
    QA_FILE="$QA_FILE_OVERRIDE"
else
    resolve_cmd=(python3 "$REPO_ROOT/scripts/resolve_ffion_science.py" --field qa_file)
    if [[ -n "$SCIENCE_VERSION" ]]; then
        resolve_cmd+=(--science-version "$SCIENCE_VERSION")
    fi
    if [[ -n "$SCIENCE_MANIFEST" ]]; then
        resolve_cmd+=(--science-manifest "$SCIENCE_MANIFEST")
    fi
    QA_FILE="$("${resolve_cmd[@]}")"
fi

if [[ -z "$QA_FILE" ]]; then
    echo "Q&A context NOT enabled - resolved bundle does not define a QA file" >&2
    return 1 2>/dev/null || exit 1
fi

if [[ ! -f "$QA_FILE" ]]; then
    echo "Q&A file not found: $QA_FILE" >&2
    return 1 2>/dev/null || exit 1
fi

export LLM_QA_FILE="$QA_FILE"
echo "Q&A context ENABLED - using $QA_FILE"
echo "Content:"
echo "---"
cat "$QA_FILE"
echo "---"
echo ""
echo "To disable: source scripts/set_llm_qa.sh off"
