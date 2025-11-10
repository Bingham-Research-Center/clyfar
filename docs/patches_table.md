| task | description | future relevance |
| --- | --- | --- |
| **MSLP Scaling** | Correct GEFS `prmsl` unit conversion before passing values into Clyfar so rules see realistic pressures. | Forms the baseline for any re-architected pipeline; the same unit fix will live in the shared preprocessing layer. |
| **Lock Directory** | Provide a default writable lock directory for `GEFSData` when `CLYFAR_TMPDIR` is unset to keep parallel downloads stable. | Likely replaced by a centralized I/O manager, but the fallback location pattern will be reused. |
| **Defuzz Safeguard** | Make percentile defuzzification emit NaNs (with logging) when aggregated support is zero instead of silently returning bounds. | Becomes part of the core fuzzy engine API contracts and automated monitoring. |
| **Mask Divide Fix** | Use the previously computed safe neighbor counts in `weighted_average` to avoid zero-division when smoothing elevations. | Probably superseded by vectorized raster tooling; still documents the desired numerical behavior. |
| **CLI Defaults** | Normalize `main` defaults so `'auto'/'all'` inputs resolve cleanly for programmatic invocation and document usage. | Will help define the interface for the eventual orchestrator or workflow manager. |
| **Parquet Bypass** | Reuse in-memory GEFS results when running Clyfar immediately after preprocessing and respect `--no-gefs` when only reading saved data. | Evolves into cache-aware data passing in the refactored system. |
| **Timing Hook** | Re-enable `@configurable_timer` instrumentation with a verbosity guard to capture runtime metrics without noise. | Provides the template for structured telemetry in the new architecture. |
| **Diagnostics** | Add optional logging of rule activations and antecedent percentiles to understand fuzzy-system usage. | Feeds the calibration dataset for redesign and future ML/fuzzy hybrids. |
| **Validation Script** | Document local smoke test steps and add an SLURM submission template for reproducible runs on CHPC. | Will migrate into the DevOps documentation but remains directly useful. |
| **Regression Check** | Run the testing CLI after changes, archive logs/figures, and note commands for repeating on SLURM. | Process habit that carries forward regardless of code layout. |
