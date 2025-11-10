# Clyfar Multi-Version Winter Experiment
Date updated: 2025-09-25

Goal: Compare multiple Clyfar versions (e.g., v0.9 baseline, v0.9.x hotfixes, v1.0 candidate, v1.1-PLR) using identical GEFS inputs for each winter day from 1 December through 15 March.

## Step-by-Step Plan

1. **Define Experiment Configs**
   - Create `experiments/winter_YYYY.yaml` listing:
     - Run range (`start: YYYY-12-01`, `end: YYYY-03-15`, frequency `1D`).
     - GEFS member subset (e.g., `p01`–`p30`, control, mean).
     - Version registry keys to test (`v0_9`, `v0_9_1`, `v1_0`, `v1_1_PLR`).
     - Output root directories for data (`data/experiments/<version>/<run_id>/`).
   - Store any version-specific overrides (variables enabled, MF set, rule tweaks).

2. **Materialise Input Data Once**
   - For each init time in the range, download GEFS slices only once.
   - Cache raw files under `data/gefs_cache/YYYYMMDDHH/`.
   - Record metadata (download timestamp, file hashes) in `data/gefs_cache/index.json`.

3. **Run Clyfar Versions Sequentially**
   - For each version entry:
     - Hydrate the appropriate configuration (variables, rules, membership set).
     - Launch pipeline pointing to cached GEFS data via abstraction layer.
     - Save outputs to `data/experiments/<version>/<YYYYMMDDHH>/` and figures to `figures/experiments/<version>/<YYYYMMDDHH>/`.
     - Write a `run.json` capturing git SHA, version tag, config hash, and success flags.

4. **Summarise & Compare**
   - After runs complete, aggregate key metrics (ozone percentile diffs, possibility category frequencies, ignorance score) into a comparison table.
   - Produce plots highlighting divergences (e.g., heatmaps of version deltas).
   - Log findings in `experiments/reports/winter_YYYY.md` with bullet summary + next actions.

5. **Archive & Reset**
   - Store experiment configs, `run.json`, and summary report in version control.
   - Optionally push artefacts to long-term storage (S3/Drive).
   - Tag repo (`experiment/winter-YYYY-vMULTI`) to capture experiment state.

## Operational Tips
- Automate with a driver script (`python -m clyfar.experiments run --config experiments/winter_YYYY.yaml`).
- Use parallelism cautiously: reuse cached data and limit concurrent versions to avoid I/O thrash.
- Maintain a spreadsheet or dashboard to track version readiness (exploratory vs candidate).
