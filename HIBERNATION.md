# Clyfar Freeze and Hibernation Runbook
Date updated: 2026-08-07

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

The last verified snapshot, on 2026-03-30, had the observation downloader
active and the six-hourly Clyfar submit cron commented out. This is historical
evidence, not proof of current crontab state.

Check live state before any operations decision:

```bash
crontab -l | nl -ba
rg -n "Observations|submit_clyfar.sh" <(crontab -l)
```

Expected hibernation pattern:

```cron
# Observations remain active.
# The line invoking sbatch scripts/submit_clyfar.sh remains present but commented.
```

Do not rewrite command bodies when changing cadence. Keep
`scripts/submit_clyfar.sh` as the operational entrypoint so init anchoring and
downstream markers remain consistent.

## Safe resume

1. Verify the checkout, environment, storage roots, and live crontab.
2. Run the smoke command in `README.md` with upload disabled.
3. Uncomment the existing Clyfar cron line with `crontab -e`.
4. Re-check `crontab -l | nl -ba`.
5. Verify the first cycle using Slurm state, `.out`/`.err`, forecast-export
   markers, and explicit LLM-stage markers.

Before editing cron, a recoverable local backup can be written under `/tmp`:

```bash
crontab -l > /tmp/clyfar_crontab.backup.$(date +%Y%m%d_%H%M%S)
```

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
