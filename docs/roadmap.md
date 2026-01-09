# Clyfar Refactor & Versioning Plan
Date updated: 2026-01-09

> **Current version:** v0.9.4 (LLM outlook pipeline operational)
> **Session notes:** See `docs/SESSION_2026-01-09.md` for latest changes.

## Mission Snapshot
- Keep v0.9 frozen and traceable while paving the path to the v1.x family.
- Make every workflow (ingest → preprocess → FIS → viz) configurable, testable, and documented.
- Reduce repo noise so new collaborators and AI agents find facts fast.

## Milestone Track (Essentials + Microtasks)

### M1 · Freeze 0.9 Baseline ✓
- [x] Tag `v0.9.0` from the current mainline and cut `release/0.9`. → v0.9.0 through v0.9.4 tagged
- [x] Capture a `--testing` golden run + regression trio (see `docs/baseline_0_9.md` for commands, artefacts, SHA tracking).
- [ ] Snapshot representative figures into `figures_archive/v0_9/`.
- [x] Freeze dependency set in `constraints/baseline-0.9.txt`. → `requirements.txt` locked Nov 2025

### M2 · Package Layout
- [ ] Scaffold `clyfar/` package (`__init__`, `core`, `fis/versions`, `nwp`, etc.).
- [ ] Move one module family at a time; update imports + keep shims in legacy paths.
- [ ] Add `pyproject.toml` and editable install instructions.
- [ ] Create `tests/imports/test_package_layout.py` to guard new namespace.
- [ ] Update docs/README snippets that reference module paths.

### M3 · Public APIs
- [ ] Publish thin `api.py` modules for NWP, preprocessing, and FIS entry points.
- [ ] Define TypedDict/dataclasses describing inputs/outputs consumed across stages.
- [ ] Document each public function with runnable samples in `docs/api_samples/`.
- [ ] Add fast contract tests (shape/dtype/nullable checks) for each API.
- [ ] Emit deprecation warnings from legacy helpers slated for removal.

### M4 · Config & Registries
- [ ] Implement registry helpers (`VARIABLES.register`, `MF_REGISTRY.register`).
- [ ] Author `schemas/config.schema.json` and a loader that validates configs.
- [ ] Ship example configs under `configs/examples/` covering core workflows.
- [ ] Regression-test each example config resolves to concrete callables.
- [ ] Write decorator docs + usage in `docs/configuration.md`.

### M5 · CLI & Paths
- [ ] Wrap orchestration behind a `typer` or `click` CLI (`clyfar run`, `clyfar experiment`).
- [ ] Keep `run_gefs_clyfar.py` as a shim forwarding into the new CLI.
- [ ] Support global flags: `--dry-run`, `--verbose`, `--cache-root`.
- [ ] Document CLI usage and completions in `docs/cli.md` (+ completion scripts).
- [ ] Ensure path handling respects env vars and config overrides.

### M6 · Experiment Runner & Automation
- [ ] Design `experiments/baseline.yaml` describing member grids & MF sets.
- [ ] Build `clyfar.experiments` runner capable of local + batch execution.
- [ ] Persist `run.json` metadata (git SHA, config hash, timings) per run.
- [ ] Add checkpoint/resume logic to skip finished members on rerun.
- [ ] Integrate metrics logging (CSV + optional wandb hook).

### M7 · CI, QA & Governance
- [ ] Configure GitHub Actions (lint, `pytest -q`, smoke workflow).
- [ ] Cache conda/pip layers to keep CI <10 min.
- [ ] Require coverage thresholds; publish artefacts per run.
- [ ] Document release checklist in `docs/release_process.md`.
- [ ] Draft governance note for approving new FIS versions and experiment tags.

## Roadmap · 2025-09-25 Execution Plan

### 1) 0.9.x Hardening
- Tag baseline outputs and store under `data/baseline_0p9/`.
- Compare snow/ozone metrics between v0.9 and legacy to confirm parity.
- Review representative station coverage vs latest obs data; adjust lists.
- Silence Matplotlib cache warnings by exporting `MPLCONFIGDIR` in CLI entry.
- Draft `v0.9.1` notes (snow bias + timing hotfix scope).

### 2) Smoke & Regression Suite
- Script the `--testing` workflow (`scripts/run_smoke.sh`).
- Capture runtime logs into `performance_log.txt` and diff vs baseline.
- Validate parquet + figure outputs exist post-smoke run.
- Set up nightly cron/CI smoke execution using cached data.
- Record git SHA + config hash with each smoke artefact.

### 3) Packaging Prep
- Author `pyproject.toml` and `setup.cfg` (if needed) for editable installs.
- Expose `__version__ = "0.9.0"` in `clyfar/__init__.py`.
- Provide install instructions in README + AGENTS.
- Dry-run `pip install -e .` in a clean env.
- Verify `python -c "import clyfar"` works post-install.

### 4) Experiment Framework
- Draft `experiments/baseline.yaml` grid definitions.
- Implement `python -m clyfar.experiments run --config ...` CLI entry.
- Log metadata to `data/<run_id>/run.json` for each execution.
- Add resume-by-member chunking (skip completed outputs).
- Document experiment process in `docs/experiments.md`.

### 5) Data Ingest Abstraction
- Create `clyfar/nwp/interfaces.py` with `ForecastDataset` protocol.
- Wrap GEFS loader into `GEFSDataSource` implementing the protocol.
- Stub `HRRRDataSource` returning mocked data for API parity tests.
- Write tests ensuring both sources expose consistent fields/units.
- Update workflow to pull data via the abstraction layer.

### 6) FIS Optimization Hooks
- Externalise MF parameters into YAML/JSON definitions.
- Implement gradient-descent prototype adjusting one MF set.
- Log loss progression to `data/experiments/`.
- Add CLI flag `--optimize-mfs` toggling optimisation.
- Document workflow in `docs/fis_optimization.md`.

### 7) Documentation Refresh
- Add `Date updated: YYYY-MM-DD` to README, AGENTS, docs notebooks.
- Insert an architecture diagram (Mermaid or PNG) into README.
- Outline version naming (0.9, 1.0, 1.1-XYZ) in `docs/versioning.md`.
- Cross-link smoke instructions between README and AGENTS.
- Create `notebooks/archived/INDEX.md` cataloguing legacy notebooks.

### 8) Cleanup & Governance
- Review `bkup/` and delete or archive stale scripts.
- Reclassify notebooks by purpose (analysis/research/reference).
- Draft contributor guidelines covering branches, reviews, coding style.
- Establish "change proposal" template for new FIS versions.
- Schedule weekly checkpoint to triage experiment branches.

### 9) Tooling & CI Enhancements
- Add `pre-commit` with `ruff`, `black`, `isort` hooks.
- Create CI workflow for lint + smoke (with mocked downloads).
- Integrate coverage reporting and publish badge-ready data.
- Cache dependency environments (conda/pip) in CI runs.
- Update README with CI status badges once live.

### 10) Observability & Telemetry
- Decorate critical pipeline stages with timing logs → `performance_log.txt`.
- Optionally upload artefacts (figures/data) to S3/local archive via config flag.
- Format logs as JSON for easier parsing.
- Count per-variable success/failure after each run and report summary.
- Provide dashboard notebook summarising the latest runs.

## Targeted Refactor Recommendations (Top 20)
1. Collapse duplicate utility functions by centralising date/time helpers in `utils/datetime.py`.
2. Replace ad-hoc prints with `structlog` or standard `logging` configured for JSON output.
3. Convert `postprocesing/` typo directory into `postprocessing/` and merge relevant modules.
4. Introduce `attrs` or `pydantic` models for configuration validation to reduce manual checks.
5. Move large plotting defaults into a shared `viz/style.py` for consistent aesthetics.
6. Build a lightweight secrets loader (env or `.env`) to avoid hard-coded tokens in notebooks.
7. Add `make targets` or `noxfile.py` covering lint, smoke, docs, and experiment runs.
8. Split `run_gefs_clyfar.py` into orchestrator + reusable stage modules to simplify tests.
9. Replace manual file-tree notes (`filetree.txt`) with an automated generator (`python -m clyfar.tools.tree`).
10. ~~Introduce `docs/kb/` backed by a separate knowledge-base repo synced via git submodule for Codex context.~~ (Superseded by `CLAUDE.md`)
11. Enforce consistent pandas timezones by wrapping conversions in `utils/timezone.py` helpers.
12. Replace global `Lookup()` with dependency injection or `functools.lru_cache` to avoid repeated loads.
13. Create a minimal `clyfar.dataset` module standardising parquet schema metadata.
14. Extract multiprocessing pool management into `clyfar/core/parallel.py` with context managers.
15. Implement lazy import guards for heavy libs (cartopy, matplotlib) to speed CLI startup.
16. Provide an onboarding notebook (`notebooks/onboarding/intro.ipynb`) linking to docs and quick tasks.
17. Publish example config + output pairs in `examples/` for new contributors to sanity-check.
18. Add `tests/fixtures/` with small, synthetic GRIB/NetCDF slices for offline testing.
19. Use `ruff` (or similar) to auto-suppress unused imports generated by optional dependencies.
20. ~~Document Codex usage patterns and prompt tricks in `docs/codex_playbook.md`.~~ (Superseded by `CLAUDE.md`)
