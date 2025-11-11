# v0.9 Stabilization Microtasks
Date: 2025-11-15

Use this list to work in tight focus blocks. Tasks are grouped by expected effort assuming AI-assisted editing. Always run the `--testing` smoke when touching pipeline logic.

## Small (≤1 hour)
1. `run_gefs_clyfar.py`: add `MPLCONFIGDIR` environment export near the CLI entry to stop matplotlib cache warnings (docs/roadmap.md:66).
2. `README.md`: replace TODO list with the current env setup (conda + `pip install -r requirements.txt`) and link to `docs/setup_conda.md` for consistency.
3. `requirements.txt`: audit top-level libs vs pip freeze; drop unused deps noted in `docs/repo_review.md`.
4. `docs/README.md`: cross-link smoke instructions between README/AGENTS per roadmap item 7.
5. `utils/__init__.py`: ensure `__all__` only exposes actively-used helpers to cut import time.
6. `filetree.txt`: regenerate via `python -m clyfar.tools.tree` placeholder or remove stale entries; add date stamp.
7. `AGENTS.md`: add CLI example under Testing with the canonical paths (`-d ./data -f ./figures`).
8. `notebooks/README.md`: mark outdated notebooks for archival (prep for cleanup task below).
9. `docs/AI_AGENT_ONBOARDING.md`: append pointer to the LaTeX technical report location once determined (currently missing, see docs/bloat_reduction.md).
10. `pytest.ini`: ensure `testpaths = tests` so stray notebooks aren’t auto-collected.

## Medium (1–3 hours)
1. `bkup/`: review scripts, migrate any still-useful helper into `utils/` or delete; document outcomes in `docs/bloat_reduction.md`.
2. `postprocesing/`: rename directory to `postprocessing/`, fix imports, and leave a shim module to avoid breaking references.
3. `docs/baseline_0_9.md`: create file capturing `--testing` command, git SHA, dataset + figure archive locations, and dependency snapshot path.
4. `scripts/run_smoke.sh`: new script that wraps the `--testing` CLI, captures logs to `performance_log.txt`, and exits non-zero on failure.
5. `constraints/baseline-0.9.txt`: freeze dependencies via `pip freeze > constraints/baseline-0.9.txt` after running in clean env.
6. `docs/experiments/baseline.yaml`: define minimal experiment config (2 members, 2 stations) to seed the upcoming runner.
7. `clyfar/__init__.py`: scaffold package namespace, expose `__version__ = "0.9.0"`, and add editable-install instructions to README.
8. `tests/imports/test_package_layout.py`: assert new `clyfar` namespace imports without side effects.
9. `docs/versioning.md`: summarize version scheme (0.9 hotfixes vs 1.0 freeze) and tagging expectations.
10. `docs/experiments.md`: describe how experiment configs map to CLI runs and where outputs live.

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
