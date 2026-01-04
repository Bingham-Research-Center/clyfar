# LLM Outlook Regeneration: Failure Analysis

**Date:** 2026-01-03
**Context:** Attempted sequential regeneration of 8 LLM outlooks, 5 of 8 failed with truncated meta-responses.

---

## Current State

### The 8 Cases (Chronological Order)

| # | Case | clustering_summary | llm_text/ | archive/ |
|---|------|-------------------|-----------|----------|
| 1 | CASE_20260101_1800Z | yes | empty | 2 files |
| 2 | CASE_20260102_0000Z | yes | empty | 2 files |
| 3 | CASE_20260102_0600Z | yes | empty | 3 files |
| 4 | CASE_20260102_1200Z | yes | empty | 3 files |
| 5 | CASE_20260102_1800Z | yes | empty | 3 files |
| 6 | CASE_20260103_0000Z | yes | empty | 3 files |
| 7 | CASE_20260103_0600Z | yes | empty | 3 files |
| 8 | CASE_20260103_1200Z | yes | empty | 2 files |

### What's Preserved
- `archive/` folders with original outputs from previous pipeline runs
- `clustering_summary.json` for all 8 cases (generated this session)
- Raw JSON data: `possibilities/`, `percentiles/`, `probs/`, `weather/` (31+ files each)

### What Was Deleted
- Failed regeneration outputs (LLM-OUTLOOK-*.md, *.pdf, forecast_prompt_*.md)

---

## Root Cause Analysis

### The Problem

Some Claude CLI invocations produced **meta-responses** instead of actual outlook content:

**Good output (180+ lines):**
```markdown
---
> **EXPERIMENTAL AI-GENERATED FORECAST**
> AI Forecaster: Ffion (ffion@jrl.ac)
...actual 15-day outlook with dRisk/dt analysis, FAQs, Data Logger...
```

**Bad output (4-13 lines):**
```markdown
---
The Clyfar ozone outlook has been completed and is ready for your review...
```

### Regeneration Results

| Case | Lines | PDF Size | Status |
|------|-------|----------|--------|
| 20260101_1800Z | 180 | 43K | **Good** |
| 20260102_0000Z | 13 | 14K | Bad - meta-response |
| 20260102_0600Z | 10 | 15K | Bad - meta-response |
| 20260102_1200Z | 4 | 9K | Bad - meta-response |
| 20260102_1800Z | 204 | 50K | **Good** |
| 20260103_0000Z | 11 | 14K | Bad - meta-response |
| 20260103_0600Z | 11 | 13K | Bad - meta-response |
| 20260103_1200Z | 193 | 51K | **Good** |

**3 good, 5 bad - no clear pattern (stochastic)**

### The CLI Invocation

The `LLM_CLI_COMMAND` environment variable is set to:
```bash
claude -p --system-prompt "You are a professional meteorologist and air chemist specialising in forecasting air quality, especially ozone. Generate the ozone outlook per the prompt."
```

This is invoked in `LLM-GENERATE.sh` line 105:
```bash
bash -lc "cd '$JSON_TESTS_ROOT' && $CLI_COMMAND --add-dir ." < "$PROMPT_PATH" > "$OUTPUT_PATH"
```

### Why It Failed

1. **`-p` flag ambiguity**: Claude CLI with `-p` outputs to stdout, but sometimes interprets the task as "write to file and confirm" rather than "output raw content"

2. **System prompt interpretation**: "Generate the ozone outlook" can mean:
   - (A) Output the outlook content directly ← intended
   - (B) Acknowledge that you generated it ← what happened

3. **No explicit raw output instruction**: The prompt template defines what to write but doesn't say "output ONLY the markdown, no preamble"

4. **Stochastic behavior**: Same setup produces different results across runs

### The Default Alternative

If `LLM_CLI_COMMAND` is unset, `LLM-GENERATE.sh` uses lines 116-121:
```bash
"$CLI_BIN" -p --model opus \
    --allowedTools "Read,Glob,Grep" \
    --permission-mode default \
    --add-dir "$JSON_TESTS_ROOT" \
    "${CLI_EXTRA[@]}" < "$PROMPT_PATH" > "$OUTPUT_PATH"
```

This is more explicit and may be more reliable.

---

## Why Chronological Order Matters

### The dRisk/dt Chain

1. **`gather_previous_outlooks()`** in `demo_llm_forecast_template.py` reads AlertLevel/Confidence from previous `LLM-OUTLOOK-*.md` files (lines 96-160)

2. **Prompt includes "Previous Outlook Summaries"** section:
   ```markdown
   ### Previous: 20260103_0000Z (6h ago)
   - **Alert Level:** MODERATE
   - **Confidence:** MEDIUM
   ```

3. **dRisk/dt analysis** compares:
   - GEFS weather trends across runs (snowier? windier?)
   - Clyfar ozone probability trends (higher? lower?)
   - Signal consistency (strengthening, weakening, oscillating)

4. **Chain integrity**: Run N references Run N-1's AlertLevel. If N-1 is malformed, N gets garbage context.

5. **Standard builds over time**: Early runs may lack context, but later runs should show consistent format and proper dRisk/dt analysis.

---

## Options for Next Attempt

### Option A: Regenerate Last 4 Only

**Use archived outputs for first 4, regenerate last 4:**

1. Restore from archive: 20260101_1800Z, 20260102_0000Z, 20260102_0600Z, 20260102_1200Z
2. Regenerate in order: 20260102_1800Z → 20260103_0000Z → 20260103_0600Z → 20260103_1200Z

**Pros:**
- Faster (4 runs instead of 8)
- Archived outputs were from working pipeline
- Less chance of accumulated errors

**Cons:**
- Chain starts with potentially older format
- First 4 may lack clustering_summary.json integration

**Commands:**
```bash
# Restore first 4 from archive
for c in CASE_20260101_1800Z CASE_20260102_0000Z CASE_20260102_0600Z CASE_20260102_1200Z; do
  cp data/json_tests/$c/llm_text/archive/* data/json_tests/$c/llm_text/
done

# Regenerate last 4
for init in 20260102_1800Z 20260103_0000Z 20260103_0600Z 20260103_1200Z; do
  ./LLM-GENERATE.sh $init
done
```

---

### Option B: Fix CLI Invocation and Retry All 8

**Unset `LLM_CLI_COMMAND` to use default invocation path:**

```bash
unset LLM_CLI_COMMAND
```

The default path in `LLM-GENERATE.sh` (lines 116-121) uses:
- `--model opus` explicitly
- `--allowedTools "Read,Glob,Grep"`
- `--permission-mode default`

This may produce more consistent behavior.

**Pros:**
- Clean chain from start
- All 8 with identical invocation
- Tests the "standard" approach

**Cons:**
- Takes longer (~5 min per run × 8 = 40 min)
- May still have stochastic failures

**Commands:**
```bash
unset LLM_CLI_COMMAND
module load pandoc/2.19.2 texlive/2022

for init in 20260101_1800Z 20260102_0000Z 20260102_0600Z 20260102_1200Z 20260102_1800Z 20260103_0000Z 20260103_0600Z 20260103_1200Z; do
  ./LLM-GENERATE.sh $init
done
```

---

### Option C: Modify System Prompt for Explicit Raw Output

**Edit `~/.bashrc` or session to change `LLM_CLI_COMMAND`:**

```bash
export LLM_CLI_COMMAND='claude -p --system-prompt "You are Ffion, an AI meteorologist. Output ONLY the raw markdown outlook content. No preamble, no summary, no acknowledgment. Start with --- and end with the AlertLevel code block."'
```

**Pros:**
- Directly addresses the meta-response issue
- Keeps custom system prompt approach

**Cons:**
- May still have edge cases
- Harder to debug

---

### Option D: Hybrid - Restore Good Archived + Regenerate Bad

**Keep good archived outputs, only regenerate problematic ones:**

Looking at archive quality:
- Check which archived outputs are properly formatted
- Restore those directly
- Only regenerate the ones that need fixing

**Pros:**
- Minimal regeneration
- Uses known-good outputs

**Cons:**
- Mixed provenance
- May have format inconsistencies between old and new

---

## Recommendation

**Start with Option A (Last 4 only) with unset LLM_CLI_COMMAND:**

1. Restore first 4 from archive (provides context chain)
2. Unset `LLM_CLI_COMMAND` to use default invocation
3. Regenerate last 4 in order
4. Verify each output before proceeding to next

This balances speed with reliability and provides a proper dRisk/dt chain for the most recent (and most important) forecasts.

---

## Files Referenced

| File | Purpose |
|------|---------|
| `LLM-GENERATE.sh` | Main LLM generation wrapper |
| `scripts/demo_llm_forecast_template.py` | Renders prompt with previous outlook summaries |
| `templates/llm/prompt_body.md` | Prompt template defining output structure |
| `scripts/generate_clustering_summary.py` | Creates clustering_summary.json |

---

## Environment Variables

```bash
LLM_CLI_COMMAND  # Custom Claude CLI invocation (currently set, may be problematic)
LLM_CLI_BIN      # Default: claude
LLM_CLI_ARGS     # Additional args
PYTHON_BIN       # Default: python
```
