# v0.9 Stabilization Microtasks
Date: 2025-11-15

Use this list to work in tight focus blocks. Tasks are grouped by expected effort assuming AI-assisted editing. Always run the `--testing` smoke when touching pipeline logic.

## Small (≤1 hour)
- [ ] `run_gefs_clyfar.py`: add `MPLCONFIGDIR` export near the CLI entry to stop matplotlib cache warnings (docs/roadmap.md:66).
- [ ] `README.md`: replace TODO list with the current env setup (conda + `pip install -r requirements.txt`) and link to `docs/setup_conda.md`.
- [ ] `requirements.txt`: audit vs `pip freeze`; drop unused deps noted in `docs/repo_review.md`.
- [ ] `docs/README.md`: cross-link smoke instructions between README/AGENTS per roadmap item 7.
- [ ] `utils/__init__.py`: ensure `__all__` only exposes actively-used helpers to cut import time.
- [ ] `filetree.txt`: regenerate via `python -m clyfar.tools.tree` (placeholder) or remove stale entries; add date stamp.
- [ ] `AGENTS.md`: add CLI example under Testing with canonical paths (`-d ./data -f ./figures`).
- [ ] `notebooks/README.md`: flag outdated notebooks for archival (feeds notebook triage).
- [ ] `docs/AI_AGENT_ONBOARDING.md`: append LaTeX technical-report pointer (see docs/bloat_reduction.md).
- [ ] `pytest.ini`: enforce `testpaths = tests` so stray notebooks aren’t auto-collected.

## Medium (1–3 hours)
- [ ] `bkup/`: review scripts, migrate useful helpers into `utils/` or delete; document outcomes in `docs/bloat_reduction.md`.
- [ ] `postprocesing/`: rename directory to `postprocessing/`, fix imports, add shim module.
- [ ] `constraints/baseline-0.9.txt`: freeze dependencies via `pip freeze > constraints/baseline-0.9.txt` in clean env.
- [ ] `docs/experiments/baseline.yaml`: define minimal experiment config (2 members, 2 stations) to seed the runner.
- [ ] `clyfar/__init__.py`: scaffold package namespace, expose `__version__ = "0.9.0"`, and add editable-install instructions to README.
- [ ] `tests/imports/test_package_layout.py`: assert new `clyfar` namespace imports without side effects.
- [ ] `docs/versioning.md`: summarize version scheme (0.9 hotfixes vs 1.0 freeze) and tagging expectations.
- [ ] `docs/experiments.md`: describe how experiment configs map to CLI runs and where outputs live.
- [ ] (post-0.9.5) Re-evaluate the Uintah Basin snow mask smoothing/buffer once the baseline is frozen and document the tuned approach.

## Completed references
- [x] Populated `docs/baseline_0_9.md` with CLI commands, SHA placeholders, artefact map, and regression notes (2025-11-15).
- [x] Added `scripts/run_smoke.sh` wrapper with logging + provenance (2025-11-15).
- [x] Documented Uintah Basin mask diagnostics in `docs/LOGBOOK.md` and ensured snow preprocessing reflects the intended v0.9.5 behaviour (2025-11-15).
- [x] Implemented Uintah Basin daily-max ozone aggregation + parquet outputs, enabling the `plot_dailymax_heatmap` path (2025-11-15).

## Large (3–6 hours)
1. Packaging migration: move one module family (e.g., `preprocessing/`) under `clyfar/` with shims + updated imports; document in `docs/roadmap.md`.
2. `clyfar/experiments/__main__.py`: implement `python -m clyfar.experiments run --config ...` that logs `run.json` metadata per execution.
3. Data abstraction: create `clyfar/nwp/interfaces.py` (`ForecastDataset` protocol), wrap GEFS loader, and adjust pipeline entry points to use it.
4. MF configuration externalization: move membership parameters into YAML (e.g., `configs/mf/default.yaml`), load them in `fis/v0p9.py`, and add CLI flag `--mf-config`.
5. Observability: decorate pipeline stages with timing logs stored in `performance_log.txt` plus summary JSON per run.
6. CI scaffolding: add `.github/workflows/smoke.yml` running lint + smoke with cached data; document env secrets if required.
7. Notebook triage: move inactive notebooks into `notebooks/archived/`, add `INDEX.md`, and note token-heavy files we should avoid by default.
8. Contributor guide: author `docs/contributing.md` covering branch strategy, review expectations, and change proposal template for new FIS rules.
9. Pre-commit tooling: configure `.pre-commit-config.yaml` with `ruff`, `black`, `isort`, and hook instructions in README.
10. Metrics parity check: compare snow/ozone metrics between v0.9 outputs and legacy results; write summary in `docs/baseline_0_9.md` and attach figures under `figures_archive/v0_9/`.

## Milestone Plan · Baseline Freeze (target: v0.9.5)
- Smoke validation
  - [x] Freeze dependency snapshot: `pip freeze > constraints/baseline-0.9.txt`.
  - [x] Run `scripts/run_smoke.sh 2024010100` and capture git SHA + log pointers for the baseline doc (add `run.json` provenance once writer exists).
  - [x] Populate `docs/baseline_0_9.md` SHA fields + smoke artefact pointers.
- Regression triad
  - [ ] Execute `run_gefs_clyfar.py` for `{2024010100, 2024021500, 2024030500}` with `-n 8 -m 10 --log-fis`.
  - [ ] Store outputs under `data/baseline_0_9/<init>/` and `figures_archive/v0_9/<init>/`.
  - [ ] Summarize metrics (MAE, hit rate, exceedance accuracy) in `docs/baseline_0_9.md`; mirror highlights into the LaTeX report.
- Documentation & report sync
  - [ ] Update `docs/baseline_0_9.md` Logging section with run.json samples and links.
  - [ ] Add matching methodology paragraphs + references in the LaTeX repo (appendix baseline section).
  - [ ] Tag `v0.9.5` once smoke + regression checklists pass (`docs/v0p9_testing_checklist.md`).
