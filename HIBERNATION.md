# Clyfar Freeze and Hibernation Runbook
Date updated: 2026-11-19

This repository is the maintenance-frozen Clyfar implementation. It preserves
the accepted forecast, replay, export, and Ffion paths without serving as a home
for new experiments, event studies, generated artifacts, or broad roadmaps.

## Frozen baseline

- Clyfar source version: `1.0.7`.
- Current Ffion bundle/tag line: `ffion-v1.1.4`.
- The exact checked-out revision is always `git rev-parse HEAD`; do not copy a
  mutable SHA into operational data without also recording the working-tree
  state.
- Maintenance fixes should be narrow, tested, and behavior-preserving. Science
  or feature work requires explicit authorization and belongs on a separate
  branch or in the appropriate sibling repository.

## Seasonal operations state

The full winter ozone job and the plots-only GEFS job have separate cron
entries. They can share a schedule and write products for the same
initialization. Check both before changing either.

```bash
crontab -l | rg -n 'get_map_obs|submit_(clyfar|gefs_plots)\.sh|run_.*push\.sh'
```

A leading `#` disables an entry. Check the cron host and its time zone.
Observations, road forecasts and HRRR each have their own cadence.

## Safe resume

1. Verify the checked-out commit, local edits, environment and external product
   roots on the cron host. Back up the crontab before an approved change.
2. Run the upload-disabled compute-node smoke in [README.md](README.md).
   Check the member files and initialization. A smoke covers only part of a cycle.
3. Agree which job owns GEFS meteograms during winter. Review the plots-only
   entry alongside the seasonal entry to avoid duplicate work and writes.
   Activate the agreed cadence using the existing submit wrapper, then read
   back the live entries.
4. For the first cycle match the initialization across the job’s `.out` and
   `.err`, `STATUS_FORECAST_EXPORT`, `STATUS_LLM_STAGE`, and the per-host
   upload receipts. Retries and downstream warnings can accompany a clean
   Slurm exit.
5. On both www.basinwx.dev and www.basinwx.com inspect `/api/health`,
   `/api/monitoring/freshness`, and the corresponding files under
   `/api/filelist/forecasts`, `/api/filelist/images` and
   `/api/filelist/llm_outlooks`. Open the expected files for that init.
   Check the human Ozone Alert separately with the duty forecaster.

## Frozen-repo boundaries

- Runtime output and caches follow `docs/STORAGE-GUIDE.md`; none belong in this
  checkout.
- During checkout cleanup, separate derived outputs from regenerable caches.
  Move reviewed outputs to an explicit recovery/archive root, but do not copy a
  deep Herbie cache across filesystems merely to preserve it; use the bounded
  cleanup procedure in `docs/STORAGE-GUIDE.md`.
- Durable run reports and task cards belong in `../ceidwad`.
- Manuscript material belongs in `../preprint-clyfar-v0p9`.
- Research notes and event context belong in `../brc-knowledge`.
- Historical repository material remains recoverable from Git history and
  should not be reintroduced as an in-tree archive.

Approved evaluation, extraction, or tuning work starts in a separate branch
and worktree from one exact, annotated baseline tag. Keep one scientific
treatment per branch and keep its generated data outside the checkout. The
stable ownership, compatibility, and provenance contracts for those lanes are
summarised in `docs/project_overview.md`.
