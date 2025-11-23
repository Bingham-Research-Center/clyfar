# clyfar
Bingham Research Center's (Utah State University) Ozone Prediction Model Clyfar

> **Multi-Agent Development Environment:**
> This codebase supports collaboration between multiple RAs and AI assistants (Claude, Codex, Cursor, etc.). We use clean package boundaries and shared documentation to coordinate across repos (clyfar, brc-tools, ubair-website). Each agent/human should respect existing code structure and use the integration guides provided.

Written for Python 3.11.9. Using anaconda with conda-forge. Package requirements information should be updated in `requirements.txt`.

Lawson, Lyman, Davies, 2024 

## Environment setup
1. Install/initialize Miniforge or Conda (see [docs/setup_conda.md](docs/setup_conda.md) for platform specifics).
2. Create the env: `conda create -n clyfar python=3.11.9 -y` then `conda activate clyfar`.
3. Install packages: `pip install -r requirements.txt`.
4. Run the smoke test to validate: `python run_gefs_clyfar.py -i 2024010100 -n 2 -m 2 -d ./data -f ./figures --testing`.

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

**Integration Status:** IN DEVELOPMENT (as of 2025-11-22)
- Model execution: ✓ Working (run_gefs_clyfar.py)
- Output generation: ✓ Working (local ./data/clyfar_output/)
- Website upload: ❌ Not yet implemented
- Cron scheduling: ❌ Pending upload completion

**For integration documentation, see:**
- **Master Guide:** `ubair-website/CHPC-IMPLEMENTATION.md` (section 7: Clyfar Integration Status)
- **Implementation plan:** Included in above guide
- **Schema definition:** To be added to `ubair-website/DATA_MANIFEST.json`

**Next steps:**
1. Define forecast output schema for website consumption
2. Implement upload function using `brc-tools/download/push_data.py` as template
3. Configure cron to run twice daily (6am and 6pm Mountain Time)

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
