# Repository Guidelines
Date updated: 2026-03-07

This is the canonical top-level guidance file for contributors and AI coding agents.

## Project Structure
- Entry point: `run_gefs_clyfar.py` orchestrates GEFS ingest, preprocessing, FIS inference, plots, and exports.
- Core modules:
  - `fis/` fuzzy inference logic (`v0p9.py` is operational baseline).
  - `nwp/` GEFS/HRRR data acquisition and parsing.
  - `preprocessing/` representative-value feature engineering.
  - `obs/` observation download/processing.
  - `viz/` plotting and figure utilities.
  - `utils/` shared helpers.
  - `export/` BasinWx product export/upload.
- Local artifacts (not source): `data/`, `figures/`, `figures_parallel/`.
- Archived root-level legacy notes/resources/drafts: `docs/archive/root_notes/`.

## Build and Run
- Environment: `conda create -n clyfar python=3.11.9 && conda activate clyfar`
- Install deps: `pip install -r requirements.txt`
- Canonical smoke command:
  - `python run_gefs_clyfar.py -i 2024010100 -n 2 -m 2 -d ./data -f ./figures --testing`
- Full run example:
  - `python run_gefs_clyfar.py -i 2024010100 -n 8 -m 10 -d ./data -f ./figures`

## Ffion / LLM Outlook
- Preferred dev path (cron-parity):
  - `./scripts/run_llm_outlook.sh 2026022400 --force`
  - `./scripts/run_llm_outlook.sh --start 2026022000 --end 2026022400 --force`
- Use `--check` for prerequisite checks.
- Default is upload-safe (`LLM_SKIP_UPLOAD=1`); opt in intentionally for upload.
- For interactive upload runs, first `source ~/.bashrc_basinwx` (or export `DATA_UPLOAD_API_KEY` and `BASINWX_API_URL`) before `--upload`; otherwise uploads may fail with HTTP 401 due to wrong/missing API key in the shell context.
- If upload auth looks wrong, reload the BasinWx env explicitly instead of trusting the inherited shell:
  - `unset DATA_UPLOAD_API_KEY BASINWX_API_URL; source ~/.bashrc_basinwx`
- Cold-start triage / rerun pattern:
  - Direct Ffion rerun with uploads: `unset DATA_UPLOAD_API_KEY BASINWX_API_URL; source ~/.bashrc_basinwx; ./scripts/run_llm_outlook.sh YYYYMMDDHH --force --upload`
  - Full cron-parity replay to Slurm: `unset DATA_UPLOAD_API_KEY BASINWX_API_URL; source ~/.bashrc_basinwx; sbatch scripts/submit_clyfar.sh YYYYMMDDHH`
  - Remember that `LLM-GENERATE.sh` auto-sources `~/.bashrc_basinwx` only when API vars are absent; it will not correct a stale but already-set wrong key.
- Canonical runtime versions:
  - Clyfar: repo-root `__init__.__version__`
  - Ffion: `utils/versioning.py` (`FFION_VERSION` + `get_ffion_version()`)
- Ffion versioning is a first-class concern for tech-report reproducibility and reforecasting.
  - Keep only two version axes: repo-wide Clyfar and Ffion.
  - Each `FFION_VERSION` resolves a versioned prompt/bias/QA file list via `templates/llm/ffion_registry.json`.
  - Record the exact manifest and file hashes in rendered prompts so fixed reforecasts and X-vs-Y Ffion comparisons can be rerun later.
- Post-generation validation:
  - `scripts/validate_llm_outlook.py` validates banner versions, required alert markers, and Data Logger local file links.
  - `LLM-GENERATE.sh` writes attempt output to temp files and only promotes to canonical `LLM-OUTLOOK-*.md` after validation.
- Language convention for outlook text:
  - Use `Uinta` for geographic/topographic/meteorological context.
  - Use `Uintah` only for civic/political/human entities (e.g., Uintah County).
- Non-overwrite test workflow:
  - For dry checks: `./scripts/run_llm_outlook.sh <INIT> --check`.
  - For isolated reruns, point to a separate repo clone via `CLYFAR_DIR` and separate export root via `EXPORT_DIR` when running `run_llm_outlook.sh`.
  - For full `submit_clyfar.sh` isolation, override roots:
    - `CLYFAR_DIR`, `DATA_ROOT`, `FIG_ROOT`, `EXPORT_DIR`, `LOG_DIR`
    - Set `CLYFAR_ENABLE_UPLOAD=0` for local-only runs (propagates through `run_gefs_clyfar.py`, export stage, and LLM upload stage).
  - To avoid duplicate API uploads when using `submit_clyfar.sh`, keep `CLYFAR_SKIP_INTERNAL_EXPORT=1` (default in submit script); submit performs the single export/upload pass.
- History-sensitive reruns:
  - If a missed cycle is backfilled (e.g., 12Z), regenerate the next cycle outlook (e.g., 18Z) with `--force` so previous-outlook comparison uses the repaired sequence.
- Generated-artifact bloat control:
  - Use `python scripts/prune_llm_case_artifacts.py --dry-run` to inspect old `llm_text/archive/` and temp attempt files.
  - Add `--apply` only when you intend to delete old generated artifacts.

## Coding Standards
- Follow PEP 8; 4-space indentation; type hints where practical.
- Naming: modules/functions/variables `snake_case`; classes `CamelCase`.
- Keep public functions documented with concise docstrings.
- Versioned modules use `vXrY` pattern and keep compatibility shims when refactoring.

## Testing and Validation
- Put tests in `tests/` as `test_*.py`.
- Prefer fast deterministic validation:
  - Smoke run with `--testing` and reduced members/CPUs.
  - Focused unit tests for changed logic.
- Concise operational/Ffion regression test:
  - `env PYTHONPATH=. pytest -q tests/test_ffion_bundle.py tests/test_llm_log_markers.py tests/test_validate_llm_outlook.py`
- Before committing major changes, run:
  - `python run_gefs_clyfar.py -i 2025010100 -n 2 -m 2 -t`

## Commit / PR Expectations
- Keep commits small and logical; present-tense subjects.
- Include rationale when behavior changes are non-trivial.
- PRs should include scope, motivation, validation command(s), and key artifact paths.

## Operational Safety Notes
- Multiprocessing uses `spawn`; avoid unsafe global state.
- Guard entry points with `if __name__ == "__main__":`.
- External download behavior lives in `nwp/`; treat cache/locking edits carefully.
- Production uploads are enabled when credentials are present; unset `DATA_UPLOAD_API_KEY` or use testing mode to avoid accidental uploads.
- CHPC/Slurm scheduler time is local Mountain time (MST/MDT). BasinWx-facing artifacts, GEFS cycle names, most product timestamps, and many remote services are UTC. Keep both clocks visible during incident work.
- Keep `scripts/submit_clyfar.sh` init auto-selection anchored to Slurm `SubmitTime` (not runtime `utcnow()` alone) so queue delays cannot skip expected 6-hour GEFS cycles.
- Slurm `SubmitTime` from `scontrol show job` is scheduler-local wall time (MST/MDT) without timezone suffix. Convert local time to epoch first, then derive UTC anchor; do not parse it as UTC directly.
- Expected post-fix cadence in this environment is submit at local `03:15`, `09:15`, `15:15`, `21:15` mapping to GEFS `00Z`, `06Z`, `12Z`, `18Z` respectively (DST can shift local clock labels; verify with `sacct` when unsure). Historical logs from before this fix may show wrong init mapping.
- Common environment gotchas:
  - Use `env PYTHONPATH=. pytest ...` for repo tests; bare `pytest` can fail on imports.
  - Slurm jobs need `~/.local/bin` in `PATH` for `claude`.
  - PDF generation on CHPC depends on direct texlive path injection; do not assume the module system is usable.
- Log-reading pattern:
  - `.out` is the orchestration/status stream.
  - `.err` often contains the actual Python traceback or library warnings.
  - A run can be `COMPLETED` in Slurm while the LLM stage still failed non-fatally; check the LLM markers explicitly.
- Fast incident triage (token/time saver):
  - Confirm run init quickly: `rg -n "Running Clyfar forecast for init time" ~/logs/basinwx/clyfar_<jobid>.out`
  - Confirm export + LLM stages: `rg -n "STATUS_FORECAST_EXPORT|STATUS_LLM_STAGE|STATUS_LLM_GENERATION|STATUS_LLM_UPLOAD_|STATUS_SUBMIT_LLM_PDF_PUSH|ALERT_" ~/logs/basinwx/clyfar_<jobid>.out ~/logs/basinwx/clyfar_<jobid>.err`
  - Confirm upload stages: `rg -n "Successfully exported|Generating LLM outlook|VALIDATION PASSED|PDF uploaded successfully|Markdown uploaded to BasinWx" ~/logs/basinwx/clyfar_<jobid>.out`
  - Confirm cycle artifacts exist: `ls ~/basinwx-data/clyfar/basinwx_export/*YYYYMMDD_HH00Z* | wc -l`
  - Confirm scheduler outcome separately: `sacct -j <jobid> --format=JobID,JobName,Elapsed,State,ExitCode`

## Future Ops Priorities
- When operations pause toward end of March, prioritize moving the operational install away from a mutable repo checkout:
  - install/package Clyfar as an operational versioned deployment
  - keep hot-path runtime data off home and out of the repo; prefer scratch for speed, then archive/promote to durable storage intentionally
- Put editing on a separate worktree-style path so `main` or an operational checkout is not modified during live runs.
- The packaging/install solution and the worktree solution may be combined; the key requirement is that live ops run from a pinned, non-edited tree.

## External Repositories
- Technical report: `/Users/johnlawson/Documents/GitHub/preprint-clyfar-v0p9`
- Knowledge base: `/Users/johnlawson/Documents/GitHub/brc-knowledge`
- Operational sibling tools: `../brc-tools`
