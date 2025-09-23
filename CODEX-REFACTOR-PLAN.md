# Codex Refactor & Versioning Plan

## Goals
- Freeze current behavior as 0.9, then evolve safely (MFs, variables).
- Run experiments across tagged versions with repeatable outputs and metadata.

## Phase Plan
- Freeze 0.9 Baseline
- Introduce Package Layout
- Stabilize Public APIs
- Add Config + Registries
- Refactor CLI & Paths
- Add Experiment Runner
- CI + Release Workflow

## 1) Freeze 0.9 Baseline
- Branch: `git checkout -b release/0.9`
- Tag: `git tag -a v0.9.0 -m "Freeze current functionality" && git push --tags`
- Keep `release/0.9` frozen; hotfix via `v0.9.x` tags if needed.

## 2) Package Layout
- Create package:
  - `clyfar/__init__.py` (defines `__version__`)
  - `clyfar/core/` (orchestration from `run_gefs_clyfar.py`)
  - `clyfar/fis/versions/{v0_9,v1_0}/` (house versioned MF logic)
  - `clyfar/{nwp,preprocessing,viz,utils}/`
- Re-export for backward compat where useful; add `pyproject.toml` later.

## 3) Stabilize Public APIs
- NWP: `clyfar.nwp.api.get_timeseries(...)`
- Preproc: `clyfar.preprocessing.api.create_forecast_dataframe(...)`
- FIS: `clyfar.fis.api.compute_ozone(mf_set, inputs)->outputs`
- Default behavior maps to `v0_9` implementation.

## 4) Config + Registries
- Config (YAML/JSON): select variable set, percentile methods, `mf_set`.
- Registries:
  - `VARIABLES.register("wind", func)`
  - `MF_REGISTRY.register("v0_9", obj)` and new variants (e.g., `v1_0`).

## 5) CLI & Paths
- CLI `clyfar`:
  - `clyfar run --config config.yaml --inittime 2024010100 -n 8 -m 10 -d ./data -f ./figures`
  - `clyfar experiment run --suite suites/baseline.yaml`
- Centralize paths in config/env; make `run_gefs_clyfar.py` a thin wrapper.

## 6) Experiment Runner
- Iterate versions (e.g., `mf_set in [v0_9, v1_0]`) and member/CPU grids.
- Write under `data/<version>/<run_id>/` and `figures/<version>/<run_id>/`.
- Save `run.json` with git tag, config hash, start/end times, and params.

## 7) CI + Release Workflow
- GitHub Actions: lint + `pytest -q` on PR; build and release on tags `v*.*.*`.
- Keep `clyfar/__init__.py` version in sync with tags.

## Testing Strategy (now)
- Focus on pure helpers and API shape tests (no network by default).
- Guard heavy tests behind env flags/markers; use `pytest.importorskip`.

## Next Actions
- Create `clyfar/` skeleton, move modules with re-exports.
- Add minimal registry + config loader; default to `v0_9`.
- Add `pyproject.toml`; support editable install.
- Tag `v0.9.1` after package layout stabilizes; begin `v1_0` MF work behind config.
