# COPILOT-20260219-PLAN

## Objective
- Determine if recent clustering changes create **material practical improvement** in:
  - cluster behavior (stability + interpretability)
  - Ffion markdown quality
  - Ffion PDF quality
- Make merge decision to `main` based on evidence, not intuition.

## Fixed comparison setup
```yaml
baseline_commit: f7b5f1a
candidate_commit: 16ae4d8
branch: hotfix/ffion-1.1-clustering
run_set_count: 12
run_set_file: ~/.copilot/session-state/045698b6-26a8-4869-b048-ae030fed5d4c/files/real_run_list_12.txt
demo_fixture: CASE_20260208_1200Z
```

## Current findings snapshot
- Pipeline stability: good (12/12 runs regenerated without crash).
- Main weakness: `min_size_guard_relaxed=true` in 11/12 runs.
- Null-bucket weakness: `strict_null_members=0` in 3/12 runs.
- Brittle pattern: repeated near `30+1` singleton tail splits.
- Recommendation from last pass: **hold merge for one short tuning cycle**.

## Microtasks (next cycle)
1. **A/B replay**
   - Run the same 12 inits on `baseline_commit` and `candidate_commit`.
   - Keep outputs separated (`baseline/` vs `candidate/`).

2. **Cluster delta table**
   - Per init compare:
     - `n_clusters`, `selected_k`
     - `strict_null_members`, `non_null_members`
     - `active_window_days`
     - `min_size_guard_relaxed`
     - distance spread (`median`, `max`)
   - Flag any large jumps.

3. **Singleton-tail control test**
   - Implement and test rule to suppress weak singleton splits.
   - Re-run full 12-init matrix.

4. **Near-null rule test**
   - Add near-null thresholding (not strict 1.0/0.0 only).
   - Re-run full 12-init matrix and compare null-bucket behavior.

5. **Ffion output delta review**
   - For flagged inits, regenerate markdown+PDF.
   - Human-blind compare:
     - clarity
     - confidence alignment with spread
     - overstatement/understatement risk

6. **Merge decision**
   - Merge if:
     - singleton brittleness is reduced
     - null bucket behaves consistently
     - markdown/PDF quality is not degraded

## Commands (reference)
```bash
# regenerate one init summary
python scripts/generate_clustering_summary.py YYYYMMDD_HHMMZ

# demo checks on fixture
python scripts/demo_scenarios_clusters.py 20260208_1200Z
python scripts/demo_scenarios_possibility.py 20260208_1200Z

# plot cluster fractions
python scripts/plot_cluster_fractions.py YYYYMMDD_HHMMZ
```

## Evidence files already available
- `~/.copilot/session-state/045698b6-26a8-4869-b048-ae030fed5d4c/files/real_metrics_12.csv`
- `~/.copilot/session-state/045698b6-26a8-4869-b048-ae030fed5d4c/files/clustering_findings_note.txt`
- `~/.copilot/session-state/045698b6-26a8-4869-b048-ae030fed5d4c/files/merge_recommendation.txt`
- `~/.copilot/session-state/045698b6-26a8-4869-b048-ae030fed5d4c/files/upload_verify_4runs.json`
