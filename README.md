# Clyfar

Clyfar forecasts winter ozone in Utah’s Uinta Basin. For each GEFS ensemble
member, it reduces snow, pressure, wind and sunlight to basin values, then
applies fuzzy rules to estimate which ozone categories are possible. The
frozen forecast system is Clyfar 1.0.7 with Ffion 1.1.4.

## Follow one forecast

| Step | Where to look | What comes out |
| --- | --- | --- |
| Forecast on CHPC | `scripts/submit_clyfar.sh` calls `run_gefs_clyfar.py` | Member-level parquet and figures for one initialization |
| Publish the forecast | `scripts/push_clyfar_products.py` | BasinWx JSON, images and local CASE inputs for Ffion |
| Generate the outlook | `scripts/run_llm_stage.sh` | Ffion text and PDF linked from BasinWx |

The plots-only job, `scripts/submit_gefs_plots.sh`, can run while winter
ozone forecasting is paused. Observations, HRRR and road feeds have their
own schedules. A fresh map on the website tells you about that feed only.

## First steps on CHPC

From this checkout, activate the maintained Python environment and run a
small offline test of the version and output-path configuration.

```bash
source ~/software/pkg/miniforge3/etc/profile.d/conda.sh
conda activate clyfar-nov2025
env PYTHONPATH=. pytest -q tests/test_versioning.py tests/test_storage_defaults.py
```

For a two-member forecast smoke test, use a compute allocation. This command
can fetch GEFS inputs and writes to an external run root.

```bash
CLYFAR_ENABLE_UPLOAD=0 LLM_SKIP_UPLOAD=1 scripts/run_smoke.sh 2024010100
```

For a new environment, start with [environment setup](docs/setup_conda.md).
For seasonal startup, follow the [operator runbook](HIBERNATION.md). It covers
cron, the Slurm logs and checking the same forecast on both website hosts.

## Find the right workflow

- **Historical replay** uses `scripts/run_winter_replay.py`. Resume from the
  validated ledger. Paths, retention and cache policy are in the
  [storage guide](docs/STORAGE-GUIDE.md).
- **Ffion for an existing case** uses `scripts/run_llm_outlook.sh YYYYMMDDHH`.
  Set `CLYFAR_JSON_TESTS_ROOT` to the CASE root. Upload is opt-in for this wrapper.
- **Forecast verification** starts with the [producer field map and scorecard handoff](verif/README.md).
- **Development** starts with [AGENTS.md](AGENTS.md), the [test guide](docs/TESTING.md)
  and the [maintained references](docs/README.md).
