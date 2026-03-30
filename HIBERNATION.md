# Clyfar Hibernation Runbook (Ops Pause -> Dev Mode)
Date updated: 2026-03-30

This file is the durable handoff for seasonal operations pause. It explains what was changed, how to restore production cron behavior, how to test restarts safely, and what to prioritize in dev mode.

## What was changed today (plain language)

The user crontab was checked and it contained two active jobs:
- observation downloader every 5 minutes
- Clyfar 6-hourly forecast submit job

Only the Clyfar submit line was commented out. The observation job stayed active.

### Current intended state

```cron
# Observations - Every 5 minutes (ACTIVE)
*/5 * * * * /bin/bash -c 'source ~/.bashrc_basinwx && source ~/software/pkg/miniforge3/etc/profile.d/conda.sh && conda activate clyfar-nov2025 && python ~/gits/brc-tools/brc_tools/download/get_map_obs.py >> ~/logs/obs.log 2>&1'

# Clyfar 6-hourly submits (PAUSED)
# 15 3,9,15,21 * * * /bin/bash -c 'source ~/.bashrc_basinwx && export PATH=$PATH:/uufs/notchpeak.peaks/sys/installdir/slurm/std/bin && cd ~/gits/clyfar && sbatch scripts/submit_clyfar.sh >> ~/logs/clyfar_submit.log 2>&1'
```

## How to inspect and confirm (safe checks)

```bash
# Show crontab with line numbers
crontab -l | nl -ba

# Optional quick sanity checks
rg -n "Observations|submit_clyfar.sh" <(crontab -l)
```

Operational check interpretation:
- Observation line should be uncommented.
- Clyfar line should be present but commented out during hibernation.

## Return to normal (resume 6-hourly forecasts)

1. Edit crontab:
```bash
crontab -e
```

2. Remove the leading `#` from the Clyfar line.

3. Re-check:
```bash
crontab -l | nl -ba
```

4. Optional smoke submit before waiting for cron:
```bash
cd ~/gits/clyfar
sbatch scripts/submit_clyfar.sh
```

5. Verify first resumed cycle:
```bash
rg -n "Running Clyfar forecast for init time|STATUS_FORECAST_EXPORT|STATUS_LLM_STAGE" ~/logs/basinwx/clyfar_*.out ~/logs/basinwx/clyfar_*.err
```

## Tweak behavior without breaking commands

Keep command bodies unchanged whenever possible. Only edit cron schedule fields.

Examples:

```cron
# Every 6 hours at :15 local scheduler time (current operational style)
15 3,9,15,21 * * *

# Every 12 hours at :15
15 3,15 * * *

# Daily at 03:15
15 3 * * *
```

If you change cadence, keep `scripts/submit_clyfar.sh` as the invoked entrypoint so init anchoring and downstream behavior remain consistent.

## Backup/rollback pattern (recommended)

Before manual edits:
```bash
crontab -l > /tmp/clyfar_crontab.backup.$(date +%Y%m%d_%H%M%S)
```

Rollback:
```bash
crontab /tmp/clyfar_crontab.backup.YYYYMMDD_HHMMSS
```

## Repo state snapshot for milestone planning

Current repo version:
- `__init__.__version__`: `1.0.6`

Current label set (GitHub issues/PR labels):
- `bug`
- `documentation`
- `duplicate`
- `enhancement`
- `good first issue`
- `help wanted`
- `invalid`
- `question`
- `wontfix`
- `potential bug`

Current git tags include:
- Clyfar tags through `v1.0.6`
- Ffion tags through `ffion-v1.1.3`
- LLM/pipeline milestone tags (`ai-llm-v*`, `llm-v*`)

If you want to signal this hibernation milestone without changing Ffion:
- bump only `__init__.__version__` (Clyfar axis)
- create a matching git tag (`vX.Y.Z`) after merge
- keep `utils/versioning.py` unchanged unless Ffion bundle changes

## Dev-mode roadmap (prioritized micro-items)

Scoring word: **Leverage** (10 = highest leverage)

### Important / urgent
- **Leverage 10/10** — Freeze operational runtime into a pinned deployment path (non-mutable checkout) and run ops from that path only.
- **Leverage 10/10** — Split “ops” and “dev” trees (worktree or clone) so development cannot perturb live scheduling environments.
- **Leverage 9.5/10** — Create a one-command replay harness for historical cycles (download, run, export, validate markers) for deterministic retrospective evaluation.
- **Leverage 9.5/10** — Add automated scorecard generation (event-based precision/recall, calibration curves, regime slices) from archived forecasts/obs.
- **Leverage 9/10** — Build a baseline-vs-candidate comparison runner for `v0p9` versus `v1.1+` rule sets with standardized metrics and artifact paths.
- **Leverage 9/10** — Harden cache lifecycle controls (fresh-cache option, per-job cache isolation, corruption detection, and cleanup hooks).
- **Leverage 8.5/10** — Add a strict “no upload” dev profile and CI-like local gate checks for export/LLM paths to avoid accidental production side effects.
- **Leverage 8.5/10** — Create a reproducible data manifest per run (inputs, hashes, versions, run config) for exact reruns and science traceability.
- **Leverage 8/10** — Define and enforce objective promotion criteria for version bumps (`v1.0.x -> v1.1.0`) tied to measurable gains.
- **Leverage 8/10** — Consolidate operational triage commands into one script with clear pass/fail output and suggested remediations.

### Cool / useful / fruitful
- **Leverage 7.5/10** — Add lightweight dashboard notebooks/scripts that summarize seasonal skill by episode type (stagnation, frontal clearing, snowpack states).
- **Leverage 7.5/10** — Introduce parameter sweep tooling for membership-function/rule tuning with reproducible experiment manifests.
- **Leverage 7/10** — Build a “known-bad cases” benchmark suite to stress-test logic changes before merging.
- **Leverage 7/10** — Add changelog automation that groups operational, science, and LLM/Ffion impacts per release.
- **Leverage 6.5/10** — Standardize failure taxonomy and marker vocabulary so postmortems and trend analysis are machine-queryable.
- **Leverage 6.5/10** — Add synthetic dry-run fixtures for upstream outage simulation (GEFS missing files, upload auth failures, delayed scheduler starts).
- **Leverage 6/10** — Produce concise architecture diagrams for dataflow and failure domains to speed onboarding of new contributors/agents.
- **Leverage 6/10** — Create “season startup checklist” and “season shutdown checklist” scripts to reduce manual drift each year.

## Suggested milestone next step

If this hibernation handoff is accepted, consider:
- keep Clyfar at `1.0.6` as the hibernation baseline
- run 2025/2026 reforecast evaluation with this baseline for the preprint
- start a `v1.1` project board keyed to the top 10 leverage items above

## AI-agent note

For AI agents entering this repo:
- read `AGENTS.md` and `docs/README.md` first
- then read this file for current operational state before proposing schedule or deployment changes
