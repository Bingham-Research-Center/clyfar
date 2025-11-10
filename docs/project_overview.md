# Clyfar Project Overview
Date updated: 2025-10-05

## What Clyfar Does
Clyfar is an ozone-forecasting system built for the Uinta Basin. It ingests GEFS ensemble weather forecasts, engineers representative features (wind, snow, solar, pressure, temperature), feeds them into a fuzzy inference system (FIS), and outputs:
- Possibility distributions for ozone categories (background → extreme).
- Percentile curves (10th/50th/90th) for expected ozone concentration.
- Visual artefacts such as meteograms and heatmaps.
The codebase targets reproducible daily runs and controlled experiments across multiple FIS versions (v0.9 baseline, hotfixes, future 1.x releases).

## High-Level Architecture
1. **Entry Point** (`run_gefs_clyfar.py`)
   - Parses CLI arguments (init time, CPU count, member count, data/figure dirs, testing flags).
   - Forces the multiprocessing `spawn` context for macOS/Linux compatibility.
   - Sets up a `Lookup` helper, instantiates the active FIS version (`fis.v0p9.Clyfar`).
   - Orchestrates the full workflow (download → preprocess → save → visualise → FIS inference).

2. **Data Acquisition** (`nwp/`)
   - `download_funcs.py` handles GEFS downloads using `Herbie`/`GEFSData` wrappers.
   - Lat/lon grids are cached as parquet with helper `check_and_create_latlon_files`.

3. **Preprocessing** (`preprocessing/representative_nwp_values.py`)
   - Functions like `do_nwpval_wind`, `do_nwpval_snow`, etc., compute representative values (quantiles, masks) across spatial domains for each ensemble member.
   - Temperature currently outputs a median as a placeholder; roadmap points toward pseudo-lapse-rate support.

4. **Utilities & Shared Logic** (`utils/`)
   - `utils.py` handles filenames, forecast-init calculations, timing decorators, system info.
   - `lookups.py` maps variable aliases across GEFS, observations, and plotting labels.
   - `geog_funcs.py` fetches elevation information used for masking low/high terrain.

5. **Fuzzy Inference System** (`fis/`)
   - `fis/fis.py` defines the base `FIS` class (control system + shared machinery).
   - `fis/v0p9.py` stores the current configuration: universes of discourse, membership functions for snow/mslp/wind/solar/ozone, fuzzy rules, and `compute_ozone` method.
   - `compute_ozone` fuzzifies inputs, runs the rule base, aggregates category curves, and defuzzifies percentiles.

6. **Post-processing & Visualisation** (`postprocessing/`, `viz/`)
   - `viz/plotting.py` and `viz/possibility_funcs.py` render meteograms, percentile plots, possibility heatmaps.
   - `postprocessing/possibility_funcs.ipynb` (now under `notebooks/postprocessing`) explores additional ideas.

7. **Testing** (`tests/`)
   - Focused unit tests cover utilities, lookups, and preprocessing behaviours to guard edge cases (nearest-neighbour selection, tick spacing, etc.).

8. **Notebooks** (`notebooks/`)
   - Reorganised into domain folders (FIS, NWP, obs, preprocessing, postprocessing, operations, viz, sandbox, reference) with `notebooks/README.md` giving per-notebook context and maturity.

## Typical Execution Flow
```
python run_gefs_clyfar.py \
    -i 2024010100 \
    -n 8 \
    -m 10 \
    -d ./data \
    -f ./figures
```
Steps internally:
1. Determine valid forecast init (can backtrack if GEFS data lag behind real time).
2. Download/cached GEFS grids for each required resolution (0.25°/0.5°) and member.
3. Compute representative time series per variable and member (parallelised across CPUs).
4. Save parquet outputs under date-stamped directories and generate quicklook figures.
5. Run Clyfar FIS member by member to obtain ozone possibility distributions and percentile estimates.
6. Save FIS outputs and heatmaps per ensemble member and relevant views.

## Possibility Theory in Clyfar
- Each ozone category (background, moderate, elevated, extreme) is represented by a fuzzy set (membership function) defined in `fis/v0p9.py`.
- When the FIS fires, rule activations clip these membership functions; the system aggregates them with the max operator, producing a possibility distribution across ozone categories.
- Percentiles (10/50/90) are derived by defuzzifying the aggregated curve (`defuzzify_percentiles`).
- If all category peaks fall below 1, the distribution is *subnormal*; the missing mass (`1 - max(π)`) indicates ignorance—aligning with Dubois & Prade’s interpretation where possibility measures express plausibility and the complement to 1 captures lack of knowledge.
- Visualisations layer category bars/heatmaps so analysts can see which ozone category is most plausible and how confident the system is.

## Interpretation & Fit to Dubois & Prade
- Clyfar follows the classic possibility framework: rules map meteorological situations to plausibility levels rather than probabilities.
- The max-based aggregation and optional normalisation mirror Dubois & Prade’s treatment of possibility distributions derived from fuzzy rules.
- Current plots show raw membership heights; planned enhancements (see `docs/ml_ideas.md`) include highlighting ignorance explicitly and supporting subnormal outputs in dashboards.

## Key Concepts to Know (Junior Undergraduate Level)
- **Fuzzy sets:** Instead of yes/no categories, membership functions assign grades (0–1) indicating how well a condition is met.
- **Fuzzy rules:** IF (snow is sufficient AND wind is calm AND solar is high) THEN ozone is extreme.
- **Possibility vs probability:** Possibility tells us what is plausible; multiple categories can be highly possible at once. Lack of information is expressed by subnormal distributions.
- **Preprocessing masks:** Elevation masks and temporal smoothing ensure the FIS receives representative local inputs.
- **Parallel processing:** Python’s `multiprocessing.Pool` speeds up member-variable extraction but requires cautious setup (spawn start method).

## Current Gaps & Roadmap Hooks
- Temperature remains a placeholder; pseudo-lapse-rate integration is pending (see notebooks + roadmap).
- Possibility heatmaps exist but daily max aggregation is incomplete (`plot_dailymax_heatmap` TODO).
- Experiment automation, registries, and CLI refactors are planned in `docs/roadmap.md`.

Use this overview alongside `docs/README.md`, `AGENTS.md`, and `docs/ml_ideas.md` for a fuller orientation.
