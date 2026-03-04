# Repository Guidelines
Date updated: 2026-03-04

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
- Canonical runtime versions:
  - Clyfar: repo-root `__init__.__version__`
  - Ffion: `utils/versioning.py` (`FFION_VERSION` + `get_ffion_version()`)
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

## External Repositories
- Technical report: `/Users/johnlawson/Documents/GitHub/preprint-clyfar-v0p9`
- Knowledge base: `/Users/johnlawson/Documents/GitHub/brc-knowledge`
- Operational sibling tools: `../brc-tools`
