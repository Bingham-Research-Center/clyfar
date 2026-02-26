# Clyfar Repository Review

## Repo Snapshot
-- `run_gefs_clyfar.py` coordinates GEFS retrieval, preprocessing, Clyfar inference, and plotting, leaning on `multiprocessing` with spawn context for ensemble parallelism.
  - Clarify CLI flags and defaults (init time, CPUs, members) and record them in a run manifest for reproducibility in methods sections.
  - Note `spawn` start method implications (copy-on-write, start-up overhead) and how it impacts memory/latency on macOS/Linux nodes used for experiments.
  - Add structured logging/timing hooks so figures/tables in papers can cite end-to-end runtimes and stage timings with confidence intervals.
- Feature engineering lives in `preprocessing/representative_nwp_values.py`, which reduces GEFS grids to basin-representative quantiles using elevation masks built in `initialize_geography`.
  - Document the statistical rationale for chosen quantiles (robustness vs bias) and outline a sensitivity study design (alternate quantiles, masks) for a supplemental appendix.
  - Specify spatial resolution, interpolation, and mask construction so results are replicable across machines and GEFS grid versions.
  - Enumerate missing-data and edge-case behaviors (lead gaps, zero-division protections) with unit-tested examples to support peer review.
- The fuzzy system (`fis/v0p9.py`) supplies membership functions and rules for ozone inference; `nwp/` wraps Herbie downloads, and `viz/` provides ensemble and ozone visualizations.
  - Describe universes and membership parameterization (triangular/trapezoidal) and how expert elicitation informed rule design; include a compact parameter table for methods.
  - Track FIS versioning (e.g., `v0.9`, `v0.9.1`) so figures and data exports carry a clear provenance tag for publication artifacts.
  - Standardize plot styles and export resolutions to produce publication-ready meteograms/heatmaps with consistent legends and units.

## Concept & Math Interpretation
- Clyfar v0.9 models ozone from four antecedents (snow depth, MSLP, 10 m wind, downwelling SW radiation) and defuzzifies to percentile estimates plus categorical possibilities.
  - Justify variable selection with references on wintertime ozone formation in basins (stagnation, snow albedo, insolation) and map each to a fuzzy antecedent.
  - Summarize membership function shapes and breakpoints; show how linguistic labels (e.g., calm/breezy) map to physical ranges used in analysis.
  - Detail the defuzzification approach that yields 10/50/90 “percentiles” from possibility distributions and clarify interpretation in the text.
- Snow, wind, and temperature series come from masked quantiles across low-elevation grid cells (0.75, 0.5, 0.5 respectively); solar uses a 0.9 quantile with deterministic local-hour persistence beyond 240 h (median by `America/Denver` local hour from `<=240h` anchors); MSLP is sampled at a single point (`Ouray`).
  - Discuss trade-offs of spatial quantiles (robust to outliers vs potential loss of spatial gradients) and propose alternatives for ablation studies.
  - Explain the local-hour persistence method beyond 240 h, quantify expected error growth, and suggest climatology- or model-based extrapolation as comparators.
  - Motivate the point-sampled MSLP choice, and flag how a basin-mean pressure might alter rule activation frequencies.
- Elevation smoothing (`weighted_average`) attempts to broaden the lowland mask before refiltering at 1850 m, biasing the analysis toward inversion-prone basin cells.
  - Specify the kernel and boundary handling; provide before/after mask diagnostics to show intended inclusion of basin fringes.
  - Justify the 1850 m cutoff with local topography and inversion climatology; consider uncertainty bands around this threshold.
  - Evaluate how the mask affects each antecedent’s time series, especially wind and temperature, and include comparative plots.

## Math & Science Risks
- MSLP "high" membership (`fis/v0p9.py:178`) activates only above ≈1035 hPa, while rule 2–4 require this state; climatology suggests this threshold is rarely achieved, starving the extreme/elevated ozone pathways.
  - Compute the empirical distribution of MSLP over winters of interest and report the fraction of hours above candidate thresholds (e.g., 1025/1030/1035 hPa).
  - Quantify rule-activation starvation by counting firings pre/post breakpoint adjustments; report impacts on possibility mass for elevated/extreme.
  - Propose updated breakpoints anchored to local percentiles (e.g., 80th–95th) and validate against observed high-ozone days.
- Solar "high" membership starts at 700 W m⁻² (`fis/v0p9.py:171`); winter basins seldom reach this, so even strongly stagnant days may never trigger the intended high-solar rules.
  - Compare GEFS shortwave maxima in DJF to the 700 W m⁻² threshold; present distributions and clear-sky estimates for context.
  - Explore a lower “high” onset (e.g., 400–500 W m⁻²) and/or a clear-sky index to normalize for solar geometry and cloud cover.
  - Reassess rule consequents if solar ceases to be a strong discriminator after normalization.
- Snow sufficiency hinges on ≥90 mm snow depth (depth, not SWE) (`fis/v0p9.py:166`), yet the upstream quantile aggregates over the entire mask; single drifted cells can flip the regime, masking spatial uncertainty.
  - Replace a hard snow‑depth threshold with a coverage fraction (e.g., ≥X% of mask above Y mm) to reduce sensitivity to outliers.
  - Validate snow‑depth thresholds against station observations; if SWE is referenced for comparison, treat it as optional context and document any conversion assumptions separately.
  - Analyze how snow‑depth regime classification correlates with observed ozone exceedances across years.
- The 0.9 solar quantile extension beyond 240 h (`preprocessing/representative_nwp_values.py`) uses deterministic local-hour persistence from the `<=240h` anchor window; despite DST-safe behavior, late-horizon ozone guidance can still decouple from evolving synoptics.
  - Benchmark persistence vs a diurnal climatology conditioned on day-of-year and cloud cover proxies for 240–384 h leads.
  - Surface uncertainty by tapering confidence/opacity in plots at extended leads; note limitations explicitly in narrative.
  - Consider truncating published guidance at a lead where verification skill remains defensible.
- Point-sampled MSLP (`preprocessing/representative_nwp_values.py:338`) ignores spatial spread; if the selected grid point is noisy relative to basin mean pressure, the fuzzy inputs will be erratic.
  - Evaluate alternatives: basin mean/median over the mask, robust estimators, or a multi-point composite centered on key sub-basins.
  - Quantify variance reduction and rule firing stability when switching from a point to an areal metric.
  - Document coordinate provenance to ensure reproducible sampling across GEFS grid updates.

## Implementation Findings
- **High – FIS MSLP scaling bug** (`run_gefs_clyfar.py:492`): multiplying GEFS `prmsl` by 100 pushes values two orders of magnitude above the defined universe (99 500–105 010 Pa), forcing the MSLP antecedent to saturate and collapsing rule discrimination.
  - Verify GEFS `prmsl` units (Pa vs hPa) in loaders and add assertions; include a unit test that fails on mis-scaled inputs.
  - Re-run a smoke test and regenerate baseline figures to assess visual and metric changes post-fix.
  - Add a conversion utility centralizing unit handling to prevent regressions across modules.
- **High – File locking crash path** (`nwp/gefsdata.py:24`): `GEFSData.LOCK_DIR` defaults to `None`; `os.path.join(None, ...)` in `safe_get_CONUS` will raise immediately unless `CLYFAR_TMPDIR` is pre-set, so parallel downloads fail in a clean environment.
  - Default to `tempfile.gettempdir()` when `CLYFAR_TMPDIR` is unset; create the directory with safe permissions.
  - Log the resolved lock directory and expose an override via CLI/env for HPC environments.
  - Add a parallel-download smoke test to catch lock-path regressions.
- **Medium – Percentile defuzzification divide-by-zero** (`fis/fis.py:225`): when no rules fire (all memberships zero), `total_area` becomes zero and the normalization produces NaNs; outputs silently fall back to the lower bound instead of surfacing the missing-signal condition.
  - Return NaNs with a clear log message and propagate an “ignorance” metric (`1 - max(π)`) to downstream plots.
  - Add a unit test for zero-support cases and ensure plots degrade gracefully (e.g., hatch or transparency).
  - Track frequency of zero-support events in `performance_log.txt` for monitoring.
- **Medium – Invalid defaults for `main`** (`run_gefs_clyfar.py:529`): the signature advertises `nmembers="all"` / `ncpus="auto"`, but the body immediately uses them as integers (`range(1, nmembers + 1)`); calling `main` programmatically with defaults raises before argument parsing.
  - Normalize defaults at the very beginning of `main` (resolve `'auto'`/`'all'`), and document accepted values in the CLI help.
  - Add a lightweight test calling `main` programmatically with defaults to guard behavior.
  - Consider making `main` a thin wrapper around a typed orchestrator function for easier testing.
- **Medium – Elevation smoothing ignores safe divisor** (`run_gefs_clyfar.py:135`): `avg_neighbors = np.divide(sum_neighbors, neighbor_counts)` bypasses the precomputed `safe_neighbor_counts`, yielding runtime warnings and potential NaNs on isolated cells.
  - Use the safe divisor and add `where=`/`out=` parameters to avoid NaNs; assert no invalids remain post-smoothing.
  - Document kernel size/weights and justify them with topographic context; include a quick visual QA in a notebook.
  - Add a regression test covering the no-neighbor edge case.
- **Medium – Clyfar reload inefficiency** (`run_gefs_clyfar.py:470`): each member rereads parquet outputs for every variable, so the workflow writes to disk only to rehydrate immediately; this dominates runtime and complicates iteration when GEFS download is skipped.
  - Introduce an in-memory pass-through from preprocessing to FIS when running in a single process or coordinated pool.
  - Add a `--cache-policy` flag (disk|memory|auto) and measure performance deltas, logging timings per stage.
  - Keep parquet writes as an optional artifact for auditability and offline analysis.
- **Low – Unit documentation drift** (`fis/v0p9.py:189`): docstrings still claim snow (cm) and MSLP (hPa) even though the code now expects mm and Pa, making scientific validation harder.
  - Audit and correct units across docstrings, plot labels, and data exports; add a style check if feasible.
  - Consider lightweight unit tagging (e.g., comments or a `pint`-style convention) on DataFrames passed between stages.
  - Include a units table in the documentation for reviewers/users.

## Iteration Opportunities
- Correct the MSLP scaling and revisit membership breakpoints using local climatology (percentile analysis on historical GEFS/obs) to align fuzzy rules with realistic ranges.
  - Compute seasonal percentile tables for key variables and align MF breakpoints accordingly; version and document the changes.
  - Validate against a small set of well-documented high-ozone events and report rule activation deltas.
  - Archive before/after figures and metrics to support changelog entries and manuscript supplements.
- Provide a default writable lock directory (e.g., `tempfile.gettempdir()`) and guard the defuzzification path so zero-support cases emit NaNs with logging.
  - Implement cross-platform path resolution and ensure sandbox/HPC environments can override defaults cleanly.
  - Emit structured logs for zero-support cases and track occurrence rates over runs.
  - Add targeted tests to keep these safeguards from regressing during refactors.
- Cache GEFS preprocessing outputs in-memory for the subsequent Clyfar step, enabling report iteration without forced downloads (`--no-gefs`) and easing unit-testing of the fuzzy layer.
  - Define an internal data object (TypedDict/dataclass) to pass preprocessed series to the FIS stage.
  - Provide a developer flag to bypass disk I/O during rapid iteration and unit tests.
  - Measure and document the speedup; fold into the performance log for transparency.
- Replace the solar and snow heuristics with daily aggregates (noon-average, snow-depth percentiles) that better match the conceptual drivers in the rules; consider integrating observation assimilation hooks already sketched in `do_nwpval_snow`.
  - Compute midday SW averages and daily snow-depth percentiles with explicit units and lead-time awareness.
  - Pilot obs-assimilation for snow depth with a small, local dataset and quantify downstream changes in possibility outputs.
  - Update rule text or MF shapes if daily aggregates materially shift input distributions.

## Refactor & Modularity Plan
- Package skeleton
  - Promote `run_gefs_clyfar.py` internals into a `clyfar/` package with submodules (`io`, `preprocessing`, `fis`, `viz`, `experiments`); keep thin shims under legacy paths for backward compatibility.
  - Surface version metadata (`clyfar.__version__`) and expose entry points in `pyproject.toml` for CLI + experiments.
- Configuration + parameter registries
  - Store FIS membership parameters, masks, and processing options in versioned YAML/JSON (e.g., `configs/fis/v0_9.yaml`) and load via validated dataclasses; support overrides per experiment.
  - Implement registries for FIS versions and preprocessing recipes so `clyfar.fis.load("v0_9")` returns a fully configured object while preserving scientific provenance.
- Pipeline API boundaries
  - Define typed contracts for each stage (download → preprocess → inference → viz) with explicit inputs/outputs; build lightweight facades for batch vs interactive use.
  - Decouple multiprocessing orchestration from business logic so unit tests can exercise pure functions without pools/spawn context.
- Experiment orchestration
  - Centralize run metadata (`run.json`) and cache handling in `clyfar.experiments`; ensure reproducible seeds, config hashes, and artifact paths for each experiment.
  - Provide CLI/SDK helpers to toggle versions, parameter sets, and output targets without editing code; useful for comparative science runs.
- Documentation + guardrails
  - Mirror the new structure in `docs/README.md` and `docs/roadmap.md`; add short HOWTOs for adding a new FIS version or swapping preprocessing parameters.
  - Maintain change logs capturing science rationale (e.g., MF shape tweaks) alongside the mechanical refactor steps to keep reviewers aligned.

## Further things to address between version 0.9 and 1.0
- Short-term (final 1–2 months; 1.0 blockers)
  - Fix MSLP scaling, normalize CLI defaults, implement lock-dir fallback, and add defuzz zero-support safeguards with tests and logs.
  - Calibrate key MF breakpoints (MSLP, solar) to local climatology and refresh baseline smoke artifacts; document changes in a concise changelog.
  - Add in-memory pipeline option and basic timing/telemetry to stabilize runtimes; correct units in docstrings/labels and refresh `docs/` cross-links.
- Post‑1.0 exploration (deeper R&D and scope expansion)
  - Redesign solar handling (clear-sky index, normalization) and refine snow logic (coverage fraction, obs assimilation) with ablation studies.
  - Introduce configuration registries, experiment runner, and packaging/CLI upgrades for multi-version comparisons at scale.
  - Prototype MF tuning (Bayesian/GA), richer diagnostics (ignorance visualization), and alternative data sources (HRRR abstraction), gating by reproducibility.
