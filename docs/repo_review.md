# Clyfar Repository Review

## Repo Snapshot
- `run_gefs_clyfar.py` coordinates GEFS retrieval, preprocessing, Clyfar inference, and plotting, leaning on `multiprocessing` with spawn context for ensemble parallelism.
- Feature engineering lives in `preprocessing/representative_nwp_values.py`, which reduces GEFS grids to basin-representative quantiles using elevation masks built in `initialize_geography`.
- The fuzzy system (`fis/v0p9.py`) supplies membership functions and rules for ozone inference; `nwp/` wraps Herbie downloads, and `viz/` provides ensemble and ozone visualizations.

## Concept & Math Interpretation
- Clyfar v0.9 models ozone from four antecedents (snow depth, MSLP, 10 m wind, downwelling SW radiation) and defuzzifies to percentile estimates plus categorical possibilities.
- Snow, wind, and temperature series come from masked quantiles across low-elevation grid cells (0.75, 0.5, 0.5 respectively); solar uses a 0.9 quantile with a heuristic persistence fill beyond 240 h; MSLP is sampled at a single point (`Ouray`).
- Elevation smoothing (`weighted_average`) attempts to broaden the lowland mask before refiltering at 1850 m, biasing the analysis toward inversion-prone basin cells.

## Math & Science Risks
- MSLP "high" membership (`fis/v0p9.py:178`) activates only above ≈1035 hPa, while rule 2–4 require this state; climatology suggests this threshold is rarely achieved, starving the extreme/elevated ozone pathways.
- Solar "high" membership starts at 700 W m⁻² (`fis/v0p9.py:171`); winter basins seldom reach this, so even strongly stagnant days may never trigger the intended high-solar rules.
- Snow sufficiency hinges on ≥90 mm liquid-equivalent depth (`fis/v0p9.py:166`), yet the upstream quantile aggregates over the entire mask; single drifted cells can flip the regime, masking spatial uncertainty.
- The 0.9 solar quantile fill beyond 240 h (`preprocessing/representative_nwp_values.py:274`) reuses historical hourly samples without regard to synoptic evolution, so late-horizon ozone guidance will largely decouple from the actual forecast.
- Point-sampled MSLP (`preprocessing/representative_nwp_values.py:338`) ignores spatial spread; if the selected grid point is noisy relative to basin mean pressure, the fuzzy inputs will be erratic.

## Implementation Findings
- **High – FIS MSLP scaling bug** (`run_gefs_clyfar.py:492`): multiplying GEFS `prmsl` by 100 pushes values two orders of magnitude above the defined universe (99 500–105 010 Pa), forcing the MSLP antecedent to saturate and collapsing rule discrimination.
- **High – File locking crash path** (`nwp/gefsdata.py:24`): `GEFSData.LOCK_DIR` defaults to `None`; `os.path.join(None, ...)` in `safe_get_CONUS` will raise immediately unless `CLYFAR_TMPDIR` is pre-set, so parallel downloads fail in a clean environment.
- **Medium – Percentile defuzzification divide-by-zero** (`fis/fis.py:225`): when no rules fire (all memberships zero), `total_area` becomes zero and the normalization produces NaNs; outputs silently fall back to the lower bound instead of surfacing the missing-signal condition.
- **Medium – Invalid defaults for `main`** (`run_gefs_clyfar.py:529`): the signature advertises `nmembers="all"` / `ncpus="auto"`, but the body immediately uses them as integers (`range(1, nmembers + 1)`); calling `main` programmatically with defaults raises before argument parsing.
- **Medium – Elevation smoothing ignores safe divisor** (`run_gefs_clyfar.py:135`): `avg_neighbors = np.divide(sum_neighbors, neighbor_counts)` bypasses the precomputed `safe_neighbor_counts`, yielding runtime warnings and potential NaNs on isolated cells.
- **Medium – Clyfar reload inefficiency** (`run_gefs_clyfar.py:470`): each member rereads parquet outputs for every variable, so the workflow writes to disk only to rehydrate immediately; this dominates runtime and complicates iteration when GEFS download is skipped.
- **Low – Unit documentation drift** (`fis/v0p9.py:189`): docstrings still claim snow (cm) and MSLP (hPa) even though the code now expects mm and Pa, making scientific validation harder.

## Iteration Opportunities
- Correct the MSLP scaling and revisit membership breakpoints using local climatology (percentile analysis on historical GEFS/obs) to align fuzzy rules with realistic ranges.
- Provide a default writable lock directory (e.g., `tempfile.gettempdir()`) and guard the defuzzification path so zero-support cases emit NaNs with logging.
- Cache GEFS preprocessing outputs in-memory for the subsequent Clyfar step, enabling report iteration without forced downloads (`--no-gefs`) and easing unit-testing of the fuzzy layer.
- Replace the solar and snow heuristics with daily aggregates (noon-average, SWE percentiles) that better match the conceptual drivers in the rules; consider integrating observation assimilation hooks already sketched in `do_nwpval_snow`.
