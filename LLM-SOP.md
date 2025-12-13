# LLM Forecast SOP (Clyfar CASE Pipeline)

## Commands (default history = 5 runs)

Local laptop:
```bash
cd ~/PycharmProjects/clyfar
./LOCAL-LLM-PROD.sh 2025121200
```

CHPC (interactive job or cron):
```bash
export CLYFAR_ROOT=~/gits/clyfar
export LLM_FROM_API=0          # use local CASE data by default
export LLM_HISTORY=5           # number of recent inits to keep synced
export LLM_QA_FILE=/path/to/QANDA.md  # optional, omit if not needed
# optional auto-salloc
export LLM_SLURM_ACCOUNT=lawson-np
export LLM_SLURM_PARTITION=lawson-np

./CHPC-LLM-PROD.sh 2025121200
```

Flags are passed straight to `scripts/run_case_pipeline.py`, which:
1. Ensures CASE_YYYYMMDD_HHMMZ directories exist for the last `history` inits (skipping any already populated).
2. Runs all demo plots + heatmaps for the current init.
3. Writes the prompt template to `CASE_<init>/llm_text/forecast_prompt_<init>.md`, embedding the CASE table and any Q&A file.

## Optional Q&A / overrides

1. Create a markdown file, e.g. `data/json_tests/CASE_20251212_0000Z/llm_text/QANDA.md`.
2. Mention any cautions (“GEFS members 10–15 have bogus snow”, “treat tail scenarios carefully”).
3. Set `LLM_QA_FILE` to that path before running the pipeline.
4. The prompt template instructs the LLM to repeat those warnings in every section.

## Generating the actual text

The pipeline only creates the prompt template. To produce prose, pipe the template into your LLM CLI (Claude example):
```bash
CASE_DIR=data/json_tests/CASE_20251212_0000Z
PROMPT=$CASE_DIR/llm_text/forecast_prompt_20251212_0000Z.md
OUTPUT=$CASE_DIR/llm_text/CLAUDE-OUTLOOK-2025121200.md

cat "$PROMPT" | claude \
  -p "You are receiving a markdown prompt; write the forecast and save as CLAUDE-OUTLOOK-2025121200.md." \
  > "$OUTPUT"
```
Always run the CLI from a compute node (salloc) rather than a login node.

## Tips / warnings

- `LLM_FROM_API=1` is useful on laptops; on CHPC prefer local CASE data (faster, no duplicate downloads).
- History > 5 can be set via `LLM_HISTORY=8` when you want a longer comparison; note this will fetch more CASE directories unless they already exist.
- The template always ends with `AlertLevel: LOW|MODERATE|HIGH|EXTREME`; scrape that line for website dashboards.
- If the Q&A block warns about bad data, manually verify before posting—those warnings are repeated everywhere by design.
- When copying JSON from other locations (e.g., CHPC export directories), ensure all three subfolders exist under `CASE_<init>/`:
  - `possibilities/forecast_possibility_heatmap_*_<init>.json`
  - `percentiles/forecast_percentile_scenarios_*_<init>.json`
  - `probs/forecast_exceedance_probabilities_<init>.json`
- Dendrogram, scenario, and heatmap PNGs live under `CASE_<init>/figs/...` for quick reference or website upload.

