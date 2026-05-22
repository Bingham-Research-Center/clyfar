# clyfar

Clyfar is the Bingham Research Center ozone prediction workflow: GEFS ingest, preprocessing, fuzzy inference, plots, BasinWx export, and Ffion LLM outlook generation.

Active repo guidance:
- [`AGENTS.md`](AGENTS.md) - agent/developer operating rules.
- [`HIBERNATION.md`](HIBERNATION.md) - current seasonal ops state, cron pause/resume, and dev priorities.
- [`docs/README.md`](docs/README.md) - documentation index.
- [`docs/setup_conda.md`](docs/setup_conda.md) - portable Miniforge/Conda setup.
- [`docs/TESTING.md`](docs/TESTING.md) - pytest conventions.
- [`docs/replay_resource_profiles.md`](docs/replay_resource_profiles.md) - winter replay Slurm resource profiles.
- [`docs/archive/root_notes/LLM-SOP.md`](docs/archive/root_notes/LLM-SOP.md) - Ffion/LLM operating notes.

`docs/ops_runbook.md` is still a template, not the current source of truth; use `HIBERNATION.md` and `AGENTS.md` for active operations.

## Environment

Python target: 3.11.9.

Local setup:
```bash
conda create -n clyfar python=3.11.9 -y
conda activate clyfar
pip install -r requirements.txt
```

CHPC operational setup uses Miniforge at `~/software/pkg/miniforge3` and the `clyfar-nov2025` environment. `scripts/submit_clyfar.sh` activates it automatically for Slurm jobs; interactive shells may inherit it, but check first:

```bash
echo "$CONDA_DEFAULT_ENV"
source ~/software/pkg/miniforge3/etc/profile.d/conda.sh
conda activate clyfar-nov2025
```

## Common Runs

Smoke test:
```bash
python run_gefs_clyfar.py -i 2024010100 -n 2 -m 2 -d ./data -f ./figures --testing
```

Full local/ad hoc run:
```bash
python run_gefs_clyfar.py -i 2024010100 -n 16 -m all -d ./data -f ./figures --log-fis
```

Operational Slurm entrypoint:
```bash
sbatch scripts/submit_clyfar.sh 2024010100
```

Winter replay resume on CHPC:
```bash
python scripts/run_winter_replay.py \
  --start 2026010412 \
  --end 2026031518 \
  --resume
```

Replay defaults currently include `lawson-np`, 16 CPUs, 48G, 2h walltime, and 30s polling. The launcher can run from a login node in `tmux` or `screen`; Slurm runs each compute job.

## Safety

For winter replay, the durable restart checkpoint is a ledger `SUCCESS` row or the driver message `validated, ledger updated, cache cleanup complete`. Killing before that may cause `--resume` to rerun the current init.

Use `squeue` for live state. If `sacct` fails, rely on logs, ledgers, manifests, quicklooks, and artifact trees before diagnosing a crash.

## Outputs

Operational outputs default under `~/basinwx-data/clyfar` and logs under `~/logs/basinwx/`.

Winter replay active root:
`/scratch/general/vast/u0737349/clyfar_replay/winter_2025_2026`

Winter replay durable archive:
`/uufs/chpc.utah.edu/common/home/lawson-group6/clyfar/replay/winter_2025_2026`

Important replay review paths under the archive root: `cases/`, `figures/heatmap/`, `figures/meteograms/`, `basinwx_export/`, `quicklooks/`, `manifests/`, and `ledger.csv`.

## Ffion

Ffion versioning is resolved through [`utils/versioning.py`](utils/versioning.py) and [`templates/llm/ffion_registry.json`](templates/llm/ffion_registry.json).

Preferred dev path:
```bash
./scripts/run_llm_outlook.sh 2026022400 --force
./scripts/run_llm_outlook.sh --start 2026022000 --end 2026022400 --force
```

Default is upload-safe (`LLM_SKIP_UPLOAD=1`); use `--upload` intentionally after sourcing `~/.bashrc_basinwx`.

## Tests

```bash
env PYTHONPATH=. pytest -q
env PYTHONPATH=. pytest -q tests/test_winter_replay.py
python -m py_compile run_gefs_clyfar.py scripts/run_winter_replay.py
```

Keep large generated artifacts out of GitHub.
