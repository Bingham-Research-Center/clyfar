# clyfar
Bingham Research Center's (Utah State University) Ozone Prediction Model Clyfar

> **AI-Assisted Development:** See `CLAUDE.md` for Claude Code context. This repo uses clean package boundaries across clyfar, brc-tools, and ubair-website.

Written for Python 3.11.9. Using anaconda with conda-forge. Package requirements information should be updated in `requirements.txt`.

Lawson, Lyman, Davies, 2024 

## Environment setup
1. Install/initialize Miniforge or Conda (see [docs/setup_conda.md](docs/setup_conda.md) for platform specifics).
2. Create the env: `conda create -n clyfar python=3.11.9 -y` then `conda activate clyfar`.
3. Install packages: `pip install -r requirements.txt`.
4. Run the smoke test to validate: `python run_gefs_clyfar.py -i 2024010100 -n 2 -m 2 -d ./data -f ./figures -t`.

## CLI Usage

```bash
python run_gefs_clyfar.py -i YYYYMMDDHH -n NCPUS -m NMEMBERS -d DATA_ROOT -f FIG_ROOT [options]
```

**Required arguments:**
| Flag | Description |
|------|-------------|
| `-i`, `--inittime` | Initialization time (YYYYMMDDHH format) |
| `-n`, `--ncpus` | Number of CPUs for parallel processing |
| `-m`, `--nmembers` | Number of ensemble members (1-31) or `all` for full GEFS ensemble |
| `-d`, `--data-root` | Root directory for data output |
| `-f`, `--fig-root` | Root directory for figure output |

**Optional flags:**
| Flag | Description |
|------|-------------|
| `-v`, `--verbose` | Enable verbose logging |
| `-t`, `--testing` | Enable testing/smoke mode |
| `-nc`, `--no-clyfar` | Skip Clyfar processing |
| `-ng`, `--no-gefs` | Skip GEFS download |
| `--log-fis` | Log fuzzy inference system diagnostics |
| `--serial-debug` | Disable multiprocessing for debugging |

**Examples:**
```bash
# Smoke test (2 members, testing mode)
python run_gefs_clyfar.py -i 2025112806 -n 4 -m 2 -d ./data -f ./figures -t

# Full operational run (all 31 GEFS members)
python run_gefs_clyfar.py -i 2025112806 -n 16 -m all -d ~/basinwx-data/clyfar -f ~/basinwx-data/clyfar/figures --log-fis

# SLURM submission (uses submit_clyfar.sh)
sbatch scripts/submit_clyfar.sh 2025112806
```

For example scenario/cluster visualisations from existing JSON (quantities, probabilities, possibilities), see `docs/CODEX-SCENARIO-POSSIBILITIES.md` and the demo scripts under `scripts/demo_*.py`.

## Debugging guardrails

- Avoid stacking silent workarounds. If a Herbie download fails, revisit the `Lookup` entry and cfgrib `filter_by_keys` using the official inventories (see `docs/external_data_references.md`) before dropping more coordinates or mutating datasets ad hoc.
- Keep canonical working examples: each variable’s loader should reference a single helper/function so humans and AI agents know where to look. Make lookup tables explicit so adding future inventory entries is transparent.
- Run with verbose logging/prints: helpers should log GRIB paths, filters, fallback usage, and NaN counts so a single smoke run surfaces issues.
- Prune caches and sanity-check artifacts regularly: delete stale `data/herbie_cache/*` or old parquet files before reruns, verify outputs, and surface questions early rather than letting errors propagate between repos.
- Document the high-value references (Herbie gallery, GEFS inventory) in AI agent lookup files and intro guides so token budgets aren’t burned rediscovering them.
- Long-term goal: refine `Lookup` + Herbie `filter_by_keys` so every variable uses the structured loader (cfgrib/xarray) without the legacy fallback. Once those filter definitions are stable, we can upstream the helpers into `brc-tools` for reuse across repos.

### Scope of Clyfar
Clyfar is the name of the prediction system itself - at least the point-of-access label of information. The fuzzy inference system, coupled with the pre-processing of observation and numerical weather prediction (NWP) data, and some post-processing (TBD!) will be part of the Clyfar system. Future work, such as a larger-scale modular approach within which Clyfar is a part, will be put in a separate package and repository.

## BasinWx Website Integration

Clyfar predictions are intended to be pushed to the BasinWx website (`basinwx.com`).

**Integration Status:** OPERATIONAL (as of 2025-11-28)
- Model execution: ✓ Working (run_gefs_clyfar.py)
- Output generation: ✓ Working (parquet + PNG figures)
- Website upload: ✓ Working (JSON + PNG via export/to_basinwx.py)
- Cron scheduling: ✓ Configured (4× daily: 03:30, 09:30, 15:30, 21:30 UTC)

**CHPC paths:**
- Conda env: `clyfar-nov2025` via `~/software/pkg/miniforge3`
- Clyfar repo: `~/gits/clyfar`
- Data output: `~/basinwx-data/clyfar`
- Logs: `~/logs/basinwx/clyfar_*.out`

**Environment requirements (set in ~/.bashrc_basinwx):**
- `DATA_UPLOAD_API_KEY`: 32-char hex key for BasinWx uploads
- `BASINWX_API_URL`: https://basinwx.com (optional, defaults to this)

> **TODO (Operations):** Herbie cache management needs improvement. Currently cached GRIB/idx files can become stale or corrupted, causing failures on retry. Options to implement:
> 1. Add `--fresh-cache` CLI flag to clear cache before run
> 2. Use per-job temp cache: `export CLYFAR_HERBIE_CACHE="/tmp/herbie_${SLURM_JOB_ID}"`
> 3. Add cache validation/cleanup to `submit_clyfar.sh`
>
> For now, manually clear before ad-hoc runs: `rm -rf ~/basinwx-data/clyfar/herbie_cache/*`

## Related Repositories and Knowledge Base
- Technical report (LaTeX, local path): `/Users/johnlawson/Documents/GitHub/preprint-clyfar-v0p9`
- Knowledge base (local path): `/Users/johnlawson/Documents/GitHub/brc-knowledge`
- BRC operational tools (local path): `../brc-tools` (sibling to this repo)
- Website deployment: `../ubair-website` (Node.js website receiving predictions)

Notes
- These are referenced for documentation and operations; clone or mount as needed.
- Keep them out of the token working set unless required for a task.

## Live session logging
- Append notes with `scripts/livelog` or `echo` to `docs/session_log.md`; PyCharm (or any editor) will follow that file as it changes.
- Capture full terminal output (AI agents or CLI apps) with standard tools:
  - Linux: `script -f docs/session_log.md`; macOS uses `script -F docs/session_log.md` because `/usr/bin/script` lacks `-f`.
  - In tmux: `tmux pipe-pane -o 'cat >> docs/session_log.md'` (enable where you want streaming, disable afterward).
  - Per-command: `yourcmd 2>&1 | tee -a docs/session_log.md` keeps the transcript on screen while persisting it.
- For Vim tailing, install the dotfiles (`~/dotfiles/install.sh`) so `vim-dispatch` is available; then run `:Dispatch tail -f docs/session_log.md` or `<leader>tl` while editing to keep a live tail inside the editor (see `~/dotfiles/README.md` for more detail).

## AI-Generated Outlook PDFs (Alpha)

> **Status:** Operational, January 2026

Clyfar generates AI-assisted ozone outlooks using the "Ffion" forecaster (Claude LLM). Each outlook is available as a professionally formatted PDF.

**Public access URL:**
```
https://basinwx.com/api/static/llm_text/llm_outlooks/LLM-OUTLOOK-YYYYMMDD_HHMMZ.pdf
```

**Example (replace with current date/time):**
```
https://basinwx.com/api/static/llm_text/llm_outlooks/LLM-OUTLOOK-20260109_0600Z.pdf
```

**Local generation + upload:**
```bash
./LLM-GENERATE.sh 20260102_0600Z
# Generates: forecast_prompt .md, LLM-OUTLOOK .md and .pdf
# Uploads PDF to BasinWx if DATA_UPLOAD_API_KEY is set
```

**Preferred development test path (cron parity, repeatable):**
```bash
# Prerequisite check only (no generation)
./scripts/run_llm_outlook.sh --start 2026022000 --end 2026022400 --check

# Single init regeneration
./scripts/run_llm_outlook.sh 2026022400 --force

# Serial 6-hourly regeneration window
./scripts/run_llm_outlook.sh --start 2026022000 --end 2026022400 --force
```
- This mirrors the production post-forecast Ffion flow in `scripts/submit_clyfar.sh`.
- Default is test-safe (`LLM_SKIP_UPLOAD=1`); add `--upload` only when intentional.

**Local path (CHPC):**
```
~/gits/clyfar/data/json_tests/CASE_YYYYMMDD_HHMMZ/llm_text/LLM-OUTLOOK-YYYYMMDD_HHMMZ.pdf
```

See `LLM-SOP.md` for operational procedures and `templates/llm/prompt_body.md` for prompt configuration.
