# Clyfar Hibernation Runbook
Last updated: 2026-05-13

Durable handoff for the seasonal Clyfar pause. v1.1 dev-mode roadmap moved to [`docs/v1.1-roadmap.md`](docs/v1.1-roadmap.md).

## Current intended cron state

The observation downloader stays active; the 6-hourly Clyfar submit is paused.

```cron
# Observations - every 5 minutes (ACTIVE)
*/5 * * * * /bin/bash -c 'source ~/.bashrc_basinwx && source ~/software/pkg/miniforge3/etc/profile.d/conda.sh && conda activate clyfar-nov2025 && python ~/gits/brc-tools/brc_tools/download/get_map_obs.py >> ~/logs/obs.log 2>&1'

# Clyfar 6-hourly submits (PAUSED)
# 15 3,9,15,21 * * * /bin/bash -c 'source ~/.bashrc_basinwx && export PATH=$PATH:/uufs/notchpeak.peaks/sys/installdir/slurm/std/bin && cd ~/gits/clyfar && sbatch scripts/submit_clyfar.sh >> ~/logs/clyfar_submit.log 2>&1'
```

## Inspect

```bash
crontab -l | nl -ba
rg -n "Observations|submit_clyfar.sh" <(crontab -l)
```

Observation line should be uncommented; Clyfar line should be present but commented.

## Resume forecasts

1. `crontab -e` and remove the leading `#` from the Clyfar line.
2. Re-check with `crontab -l | nl -ba`.
3. Optional smoke submit: `cd ~/gits/clyfar && sbatch scripts/submit_clyfar.sh`.
4. Verify first cycle: `rg -n "Running Clyfar forecast for init time|STATUS_FORECAST_EXPORT|STATUS_LLM_STAGE" ~/logs/basinwx/clyfar_*.out ~/logs/basinwx/clyfar_*.err`.

## Tweak schedule (cadence only — keep command body intact)

```cron
15 3,9,15,21 * * *   # every 6 hours at :15 (current operational)
15 3,15 * * *        # every 12 hours
15 3 * * *           # daily 03:15
```

Keep `scripts/submit_clyfar.sh` as the entrypoint so init anchoring and downstream behavior stay consistent.

## Backup / rollback

```bash
# Before manual edits
crontab -l > /tmp/clyfar_crontab.backup.$(date +%Y%m%d_%H%M%S)

# Rollback
crontab /tmp/clyfar_crontab.backup.YYYYMMDD_HHMMSS
```

## Entry points for agents

Read `AGENTS.md` and `docs/README.md` first, then this file for current operational state before proposing any schedule or deployment change. Storage policy lives in [`docs/STORAGE-GUIDE.md`](docs/STORAGE-GUIDE.md), which defers to the brc-knowledge CHPC team resource inventory.
