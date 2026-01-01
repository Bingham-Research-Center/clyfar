# LLM Forecast SOP (Clyfar CASE Pipeline)

## Environment Setup

Set these variables in your shell. For persistent config, add to `~/.bashrc` or create a conda activation script:

```bash
# One-time setup for conda env (vars load automatically on activate)
mkdir -p $CONDA_PREFIX/etc/conda/activate.d
cat > $CONDA_PREFIX/etc/conda/activate.d/clyfar_llm.sh << 'EOF'
export LLM_CLI_COMMAND='claude -p "ultrathink. You are a professional meteorologist and air chemist. Generate the ozone outlook per the prompt."'
export LLM_SLURM_ACCOUNT=lawson-np
export LLM_SLURM_PARTITION=lawson-np
EOF
```

**LLM CLI examples** (pick one for `LLM_CLI_COMMAND`):
```bash
# Claude Code CLI with extended thinking (recommended)
export LLM_CLI_COMMAND='claude -p "ultrathink. You are a professional meteorologist and air chemist specialising in forecasting air quality, especially ozone."'

# Claude Code CLI without extended thinking (faster, less thorough)
export LLM_CLI_COMMAND='claude -p "You are a professional meteorologist and air chemist specialising in forecasting air quality, especially ozone."'

# Ollama (local)
export LLM_CLI_COMMAND='ollama run llama3.2'

# Skip LLM, just render prompt for review
unset LLM_CLI_COMMAND
```

**Note:** The script runs `bash -lc` which sources your profile. If your `~/.bash_profile` has echo statements, they'll appear in the output. Either remove those echos or filter the output afterward.

**Required env vars for CHPC:**
- `DATA_UPLOAD_API_KEY` - BasinWx upload (get from team lead)
- `SYNOPTIC_API_TOKEN` - Observation API ([register here](https://developers.synopticdata.com/))

---

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
3. Writes the prompt template to `CASE_<init>/llm_text/forecast_prompt_<init>.md`, embedding the CASE table and any Q&A file (rendered from `templates/llm/prompt_body.md` by default).

## Q&A Context (Special Guidance for LLM)

Use Q&A context to inject warnings or guidance into the LLM outlook (e.g., "GEFS members show unrealistic snow"). The LLM repeats these warnings in every section.

**Quick method - use the helper script:**
```bash
# 1. Edit the QA_CONTENT section in scripts/set_llm_qa.sh
nano scripts/set_llm_qa.sh

# 2. Enable Q&A context
source scripts/set_llm_qa.sh

# 3. Run your LLM generation
./LLM-GENERATE.sh 2025121200

# 4. Disable when no longer needed
source scripts/set_llm_qa.sh off
```

**Manual method:**
```bash
export LLM_QA_FILE=/path/to/your/warnings.md
./LLM-GENERATE.sh 2025121200
unset LLM_QA_FILE  # disable
```

**Notes:**
- Empty file = no Q&A (same as unset)
- Warnings persist until you disable or change the file
- Edit `templates/llm/prompt_body.md` for permanent prompt changes

## Generating the actual text

Use `LLM-GENERATE.sh` to render the prompt (optional) and feed it to an LLM CLI in one step.
Set either `LLM_CLI_COMMAND` (full shell command that reads stdin) or `LLM_CLI_BIN`/`LLM_CLI_ARGS`.

```bash
export LLM_CLI_COMMAND='claude -p "You are receiving a markdown prompt; write the forecast and save it verbatim."'
export LLM_QA_FILE=data/json_tests/CASE_20251212_0000Z/llm_text/QANDA.md   # optional
# re-render prompt + call CLI, output defaults to CASE_.../llm_text/LLM-OUTLOOK-<init>.md
./LLM-GENERATE.sh 2025121200
```

Flags:
- `LLM_RENDER_PROMPT=0` skips re-rendering if you already have a prompt file.
- `LLM_OUTPUT_BASENAME=CLAUDE-OUTLOOK` matches the example naming convention.
- `LLM_CLI_BIN=claude` and `LLM_CLI_ARGS='-p "message" -m opus'` can be used instead of `LLM_CLI_COMMAND`.

Always run the CLI from a compute node (salloc) rather than a login node.

## Tips / warnings

- `LLM_FROM_API=1` is useful on laptops; on CHPC prefer local CASE data (faster, no duplicate downloads).
- History > 5 can be set via `LLM_HISTORY=8` when you want a longer comparison; note this will fetch more CASE directories unless they already exist.
- The template always ends with `AlertLevel: LOW|MODERATE|HIGH|EXTREME`; scrape that line for website dashboards.
- If the Q&A block warns about bad data, manually verify before posting—those warnings are repeated everywhere by design.
- Prompt body lives in `templates/llm/prompt_body.md`; point `LLM_PROMPT_TEMPLATE` elsewhere if you need variants (e.g., stakeholder briefings).
- When copying JSON from other locations (e.g., CHPC export directories), ensure these subfolders exist under `CASE_<init>/`:
  - `possibilities/` - 31 ozone category heatmaps
  - `percentiles/` - 31 ozone percentile scenarios
  - `probs/` - 1 exceedance probability file
  - `weather/` - 32 GEFS weather files (31 members + 1 percentiles)
