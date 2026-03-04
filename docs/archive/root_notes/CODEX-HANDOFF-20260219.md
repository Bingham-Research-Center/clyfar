# CODEX-HANDOFF-20260219

## Mission
Continue clustering hardening for Ffion, then validate whether improvements are material for website-facing outputs (JSON -> markdown -> PDF).

## Repo/branch state
```yaml
repo: clyfar
active_branch: hotfix/ffion-1.1-clustering
last_feature_commit: 16ae4d8
base_main_commit: fc6fd49
```

## What changed (important)
- Unified demo clustering behavior with production summary path (CASE mode).
- Added richer diagnostics in clustering summary:
  - distance quantiles
  - nearest-neighbor outlier stats
  - min-size-guard metadata
- Added robustness test for outlier-tail behavior.
- Prompt assembly now includes clustering diagnostics snapshot.
- PDF conversion now retries with `pdflatex` if primary engine fails.

## Core files touched
- `utils/scenario_clustering.py`
- `scripts/demo_scenarios_clusters.py`
- `scripts/demo_scenarios_possibility.py`
- `scripts/demo_llm_forecast_template.py`
- `templates/llm/prompt_body.md`
- `scripts/outlook_to_pdf.sh`
- `tests/test_scenario_clustering.py`
- `LLM-SOP.md`

## What worked
- 12/12 real-run summary regenerations completed.
- Demo fixture (`CASE_20260208_1200Z`) aligned with production assignments.
- 4-run sample upload to BasinWx succeeded (384/384 JSON uploads).
- Remote verification passed for those 4 clustering summaries (`schema_version: 1.2`, diagnostics present).

## What did not yet meet target
- `min_size_guard_relaxed=true` in 11/12 runs.
- No strict null cluster in 3/12 runs.
- Repeated brittle `30+1` singleton-tail splits in high-spread cases.

## Latest practical recommendation
- Hold merge to `main` for one short tune pass.
- Priority tune ideas:
  1. near-null membership rule (not exact background-only)
  2. singleton control unless separation is materially large

## Data + evidence locations
```yaml
run_list: ~/.copilot/session-state/045698b6-26a8-4869-b048-ae030fed5d4c/files/real_run_list_12.txt
metrics_csv: ~/.copilot/session-state/045698b6-26a8-4869-b048-ae030fed5d4c/files/real_metrics_12.csv
flagged_runs: ~/.copilot/session-state/045698b6-26a8-4869-b048-ae030fed5d4c/files/flagged_runs_12.txt
visual_summary: ~/.copilot/session-state/045698b6-26a8-4869-b048-ae030fed5d4c/files/review_visual_summary_5.txt
findings_note: ~/.copilot/session-state/045698b6-26a8-4869-b048-ae030fed5d4c/files/clustering_findings_note.txt
merge_note: ~/.copilot/session-state/045698b6-26a8-4869-b048-ae030fed5d4c/files/merge_recommendation.txt
upload_verify: ~/.copilot/session-state/045698b6-26a8-4869-b048-ae030fed5d4c/files/upload_verify_4runs.json
```

## BasinWx compatibility notes
- Forecast upload route unchanged: `/api/upload/forecasts`.
- Clustering filename unchanged: `forecast_clustering_summary_YYYYMMDD_HHMMZ.json`.
- Website currently reads clustering by filename pattern and uses:
  - `clusters[]`
  - `fraction`
  - `members`
  - `medoid`
  - `clyfar_ozone.risk_level`
- New diagnostics fields are additive (no filename break).

## Next execution block (recommended)
1. Run strict A/B replay (`baseline_commit` vs `16ae4d8`) on same 12 inits.
2. Implement near-null + singleton control.
3. Re-run same matrix; compare deltas with previous metrics file.
4. Regenerate Ffion markdown/PDF for flagged inits and perform quick blind read.
5. Decide merge readiness to `main`.

## Quick commands
```bash
# one-init summary
python scripts/generate_clustering_summary.py YYYYMMDD_HHMMZ

# fixture demos
python scripts/demo_scenarios_clusters.py 20260208_1200Z
python scripts/demo_scenarios_possibility.py 20260208_1200Z

# figure diagnostic
python scripts/plot_cluster_fractions.py YYYYMMDD_HHMMZ
```
