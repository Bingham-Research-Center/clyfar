# Operations Runbook (template)

## 1. Environment & Scheduling
- Host(s): `TODO_HOST`
- Scheduler: `cron/systemd/TODO`
- Activation:
  ```bash
  source ~/miniforge3/bin/activate clyfar-2025
  cd /path/to/clyfar
  ```
- Command template:
  ```bash
  MPLCONFIGDIR=/tmp python run_gefs_clyfar.py \
    -i <YYYYMMDDHH> \
    -n <CPUS> \
    -m <MEMBERS> \
    -d ./data \
    -f ./figures \
    --log-fis
  ```
- Frequency: `TODO_CRON_ENTRY`

## 2. Artefact & Log Locations
- Parquet: `data/<init>/*.parquet` plus `data/dailymax/*.parquet`.
- Figures: `figures/<init>/*.png` and archived copies under `figures_archive/v0_9/<init>/`.
- Logs: `data/baseline_0_9/logs/<init>.log` (stdout/stderr), `performance_log.txt` (timings), `run.json` (metadata).
- Guardrails:
  - MSLP parquet write now logs stats; failure here aborts the run. Investigate `data/baseline_0_9/logs/<init>.log` for guard messages.

## 3. Troubleshooting
- `scripts/check_mslp.py -i <init> -f 0 6 12 24 48 -m c00 -p atmos.25` to spot NaN pressure fields quickly.
- Clear caches (`rm -r data/herbie_cache/*`) if Herbie downloads go stale; re-run smoke command.
- Event routing: `TODO_SLACK/EMAIL` for guard failures or cron alerts.

## 4. Reporting
- API push / downstream integration: `TODO_API_DETAILS`.
- Manual review checklist: `TODO_REVIEW_STEPS`.
