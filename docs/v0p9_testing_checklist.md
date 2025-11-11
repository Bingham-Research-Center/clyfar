# v0.9 Finalization Test Plan
Date: 2025-11-15

Use this before tagging any v0.9.x release (baseline, hotfix, or release candidate). The goal is to prove reproducibility, data integrity, and scientific parity with historical performance prior to freezing and running full retrospective evaluations.

## 1. Environment & Dependency Locks
- Create/refresh `conda` env (`python=3.11.9`) using `requirements.txt`.
- Freeze exact versions into `constraints/baseline-0.9.txt` (`pip freeze --local > constraints/baseline-0.9.txt`).
- Document env hash in `docs/baseline_0_9.md` (include `conda list --explicit`).
- Validate `pip install -e .` (or module path) works: `python -c "import clyfar"`.

## 2. Smoke Workflow (fast pass)
Command: `python run_gefs_clyfar.py -i 2024010100 -n 2 -m 2 -d ./data -f ./figures --testing --log-file performance_log.txt`.
Checklist:
- Runtime < 10 min on reference hardware.
- Expected parquet outputs present (`data/<timestamp>/nwp_features.parquet`, obs parquet, FIS summary).
- Figures exist under `figures/<timestamp>/harmonized/`.
- `performance_log.txt` appended with stage timings and git SHA.

## 3. Regression Workflow (full backfill sample)
- Select three historical init times spanning different regimes (e.g., inversion, snow, clear): `2024010100`, `2024021500`, `2024030500`.
- Run with `-n 8 -m 10` to hit representative ensemble and member coverage.
- Compare outputs to prior tagged baseline using `verif/compare_results.py` (add script if missing) and store stats in `docs/baseline_0_9.md`.

## 4. Data Integrity Checks
- GEFS/HRRR downloads: confirm no corrupted tiles (`nwp/download_funcs.py` logs). Hash sample files.
- Observation ingest: verify station list matches latest obs inventory (document path in `obs/README.md`).
- Ensure parquet schemas align with expectations (use `tests/schema/test_parquet_shapes.py`).

## 5. Scientific Validation
- FIS metrics: compute ozone classification accuracy, hit rate for exceedances, and MAE vs observations for the three regression runs. Capture tables in `docs/baseline_0_9.md`.
- Spatial sanity: verify representative plots over Uintah Basin stations; store PNGs under `figures_archive/v0_9/` with captions.
- Sensitivity spot-check: perturb key inputs (solar proxy, snow cover) ±10% and confirm outputs stay within expected tolerance; log findings.

## 6. Logging & Provenance
- Record git SHA, CLI args, env checksum, and data paths per run inside `data/<run_id>/run.json`.
- Ensure `performance_log.txt` contains start/end timestamps plus stage durations.
- Mirror summary into the LaTeX technical report appendix once the repo path is known (see docs/pre_v1_roadmap.md for sync expectations).

## 7. Sign-off Checklist
- [ ] `docs/baseline_0_9.md` updated with metrics + artefact pointers.
- [ ] `figures_archive/v0_9/` contains canonical plots.
- [ ] Constraints file committed.
- [ ] Smoke + regression logs attached to PR (or stored under `data/baseline_0_9/logs/`).
- [ ] Technical report cross-references the same CLI commands and metrics.

## Best Practices & Methods
- Automate commands via `scripts/run_smoke.sh` and `scripts/run_regression.sh` to avoid drift.
- Use deterministic seeds wherever randomness exists (e.g., future Random Forest experiments).
- Capture environment metadata with `python -m pip list --format=freeze` and `conda env export` for completeness.
- Treat any failing comparison vs legacy as a blocker; investigate before tagging.
