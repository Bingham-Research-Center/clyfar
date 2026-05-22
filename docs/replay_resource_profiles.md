# Winter Replay Resource Profiles

Use these as examples for `scripts/run_winter_replay.py`.

## Default Owner-Node Profile

The replay driver defaults to the owner-node profile used for the winter replay:
`--account lawson-np --partition lawson-np --cpus 16 --mem 48G --time 02:00:00 --poll-seconds 30`.

```bash
python scripts/run_winter_replay.py \
  --start 2025120100 \
  --end 2025120118 \
  --resume
```

Override the account or partition with `--account ... --partition ...`, or set
`CLYFAR_REPLAY_ACCOUNT` and `CLYFAR_REPLAY_PARTITION` before launching.

## Conservative Shared Profile

Use only when preserving owner-node capacity matters more than queue stability.

```bash
python scripts/run_winter_replay.py \
  --start 2025120100 \
  --end 2025120118 \
  --resume \
  --account notchpeak-shared-short \
  --partition notchpeak-shared-short \
  --time 01:00:00
```

## Profiling Profile

Use this after timing instrumentation lands to compare phase costs before changing default resources or parallelism.

```bash
python scripts/run_winter_replay.py \
  --start 2025120100 \
  --end 2025120100 \
  --max-inits 1 \
  --resume
```

Review `ledger.csv`, per-init manifests, quicklooks, and `run_gefs_clyfar.py` run summaries for `driver_wait_seconds`, `postprocess_seconds`, and `phase_seconds` before tuning Slurm requests.
