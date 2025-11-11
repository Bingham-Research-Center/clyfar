# Repository Guidelines

## Project Structure & Module Organization
- Core script: `run_gefs_clyfar.py` orchestrates downloads, processing, and visualization.
- Modules:
- `fis/` fuzzy inference system (e.g., `v0p9.py`), Clyfar logic.
  - `nwp/` data acquisition/parsing for GEFS/HRRR (e.g., `download_funcs.py`).
  - `preprocessing/` feature engineering (e.g., `representative_nwp_values.py`).
  - `viz/` plotting utilities; `utils/` shared helpers; `verif/` evaluation tools.
  - `obs/` observation handling; `notebooks/` exploratory work.
  - Outputs: `data/` and `figures*/` are local artifacts, not source.

## Build, Test, and Development Commands
- Create env (Python 3.11): `conda create -n clyfar python=3.11.9 && conda activate clyfar`
- Install deps: `pip install -r requirements.txt`
- Quick smoke test (reduced workload):
  - `python run_gefs_clyfar.py -i 2024010100 -n 2 -m 2 -d ./data -f ./figures --testing`
  - Runs minimal parallel workflow, writes parquet + plots to dated subfolders.
- Full run example:
  - `python run_gefs_clyfar.py -i 2024010100 -n 8 -m 10 -d ./data -f ./figures`

## Coding Style & Naming Conventions
- Follow PEP 8, 4-space indentation, type hints where practical.
- Names: modules `snake_case.py`; classes `CamelCase`; functions/vars `snake_case`.
- Keep public functions documented with concise docstrings; prefer pure functions in `utils/`.
- Versioned modules use `vXrY` pattern (e.g., `v0p9.py`); keep API-compatible shims if refactoring.

## Testing Guidelines
- No formal test suite yet. Use the CLI `--testing` flag and small `-m`/`-n` values to validate changes quickly.
- Prefer deterministic paths: write outputs under a temporary dated folder via `-d` and `-f`.
- When adding tests, place them under `tests/` and use `pytest`; name files `test_*.py`.

## Commit & Pull Request Guidelines
- Commits: short, descriptive subjects in present tense (seen in history, e.g., 'Fix', 'Add', 'Move'). Include rationale in body when non-trivial.
- PRs: include scope, motivation, CLI example used for validation, and before/after artifacts (paths in `figures*/` helpful). Link related issues.
- Touch only relevant modules; keep changes minimal; update inline docs where behavior changes.

## Security & Configuration Tips
- I/O is parallelized; default start method is `spawn`. Avoid global state; guard CLI entry under `if __name__ == "__main__":`.
- External data downloads occur in `nwp/`; be mindful of locking/cache changes and long-running operations.

## External Repositories & Knowledge Base
- Technical report (LaTeX): `/Users/johnlawson/Documents/GitHub/preprint-clyfar-v0p9`
- Knowledge base: `/Users/johnlawson/Documents/GitHub/brc-knowledge`
- Operational tools (sibling repo): `../brc-tools`

Guidance for agents
- Discover paths on demand; read/write only when the task explicitly requires it.
- Prefer referencing these locations in docs and comments over in-code hard links.
- Keep the Clyfar code and the LaTeX technical report synchronized at release boundaries (see docs).
