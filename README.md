# clyfar

Clyfar is the Bingham Research Center wintertime ozone prediction workflow:
GEFS ingest, preprocessing, fuzzy inference, plots, BasinWx export, and Ffion
LLM outlook generation.

This fork is maintenance-frozen at the Clyfar `1.0.7` / Ffion `1.1.4` line.
It retains BRC source modifications, tests, operational wrappers, templates,
and Codex routing while excluding generated data, exploratory notebooks,
event-specific records, and historical planning clutter. See
[`HIBERNATION.md`](HIBERNATION.md) for the freeze and seasonal-ops boundary.

## Start here

- [`AGENTS.md`](AGENTS.md): concise agent/developer rules.
- [`HIBERNATION.md`](HIBERNATION.md): freeze policy and safe ops resume.
- [`docs/STORAGE-GUIDE.md`](docs/STORAGE-GUIDE.md): output/cache locations.
- [`docs/TESTING.md`](docs/TESTING.md): test conventions.
- [`docs/README.md`](docs/README.md): maintained deeper references.

## Environment

Python target: 3.11.9.

```bash
conda create -n clyfar python=3.11.9 -y
conda activate clyfar
pip install -r requirements.txt
```

On CHPC, use Miniforge and the maintained environment:

```bash
source ~/software/pkg/miniforge3/etc/profile.d/conda.sh
conda activate clyfar-nov2025
```

## Entry points

Smoke test, with outputs defaulting outside the checkout:

```bash
scripts/run_smoke.sh 2024010100
```

Ad hoc run:

```bash
RUN_ROOT=/scratch/general/vast/$USER/clyfar/ad_hoc
python run_gefs_clyfar.py -i 2024010100 -n 16 -m all \
  -d "$RUN_ROOT/data" -f "$RUN_ROOT/figures" --log-fis
```

Operational Slurm run:

```bash
sbatch scripts/submit_clyfar.sh 2024010100
```

Winter replay resume:

```bash
python scripts/run_winter_replay.py \
  --start 2026010412 --end 2026031518 --resume
```

Replay completion is durable only after a ledger `SUCCESS` row or the driver
message `validated, ledger updated, cache cleanup complete`.

## Ffion

The maintained wrapper is upload-safe by default and writes CASE data outside
the repository:

```bash
./scripts/run_llm_outlook.sh 2026022400 --force
./scripts/run_llm_outlook.sh --start 2026022000 --end 2026022400 --force
```

Set `CLYFAR_JSON_TESTS_ROOT` for replay/archive regeneration. Use `--upload`
only intentionally after loading the operational credentials.

## Data and outputs

Only the small static geography lookup tables under `data/geog/` are versioned.
Run output, replay/reforecast products, figures, CASE bundles, logs, Matplotlib
state, and Herbie caches belong on scratch, group storage, or the configured
external output root. See [`docs/STORAGE-GUIDE.md`](docs/STORAGE-GUIDE.md).

## Tests

```bash
env PYTHONPATH=. pytest -q
env PYTHONPATH=. pytest -q tests/test_storage_defaults.py tests/test_winter_replay.py
python -m py_compile run_gefs_clyfar.py scripts/run_winter_replay.py
```
