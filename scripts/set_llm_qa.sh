#!/bin/bash
# set_llm_qa.sh - Set Q&A context for LLM outlooks
#
# Usage:
#   source scripts/set_llm_qa.sh        # Enable Q&A with content below
#   source scripts/set_llm_qa.sh off    # Disable Q&A
#
# Edit the QA_CONTENT section below to change the discussion points.
# These warnings will appear in EVERY outlook section until disabled.

# ============================================================================
# EDIT THIS SECTION - Your Q&A content for the LLM
# ============================================================================
QA_CONTENT="
The air chemistry human forecaster Lyman believes solar incoming energy to be
overestimated in importance for ozone generation, due to lack of memory in
Clyfar, hence bias towards higher possibilities in more severe categories.
This is likely true from the human view, but not proven.

Lawson (meteorology) forecaster has identified the highest snowfall uncertainty
in the current Clyfar version near accumulations around 2-3 inches, and near
the rain-snow line in the foothills around the Basin.
"

# Examples of real Q&A content you might use:
# QA_CONTENT="
# GEFS members 15-20 show unrealistic snow depth spikes on Days 8-10.
# Treat elevated-ozone signals after Day 7 with extra caution until verified.
# "
#
# QA_CONTENT="
# Basin observations show anomalously warm temps not captured by GEFS.
# Ozone forecasts may be biased high for Days 1-3.
# "
#
# QA_CONTENT="
# This is a high-impact forecast period - state air quality alert in effect.
# Emphasise uncertainty ranges and recommend checking back frequently.
# "
# ============================================================================

QA_FILE="$HOME/gits/clyfar/data/llm_qa_context.md"

if [[ "${1:-}" == "off" || "${1:-}" == "disable" || "${1:-}" == "clear" ]]; then
    unset LLM_QA_FILE
    rm -f "$QA_FILE"
    echo "Q&A context DISABLED - LLM will not include special guidance"
else
    echo "$QA_CONTENT" > "$QA_FILE"
    export LLM_QA_FILE="$QA_FILE"
    echo "Q&A context ENABLED - written to $QA_FILE"
    echo "Content:"
    echo "---"
    cat "$QA_FILE"
    echo "---"
    echo ""
    echo "To disable: source scripts/set_llm_qa.sh off"
fi
