# Clyfar Field Log

## 2025-11-15
### Smoke baseline (`2024010100`)
- Ran `scripts/run_smoke.sh 2024010100` with 2 CPUs / 2 members.
- Logged metadata to `data/baseline_0_9/20240101_0000Z_smoke/run.json` (SHA `83a2298`).
- Artefacts: `data/20240101_0000Z/` parquet, `figures/20240101_00Z/` plots, `data/baseline_0_9/logs/smoke_2024010100.log`.

### Snow mask diagnostics (Uintah Basin)
- Compared representative snow (0.75 quantile) for GEFS members `p01/p02` under three masks:
  - `no_fix`: original `elev < 1850 m` (baseline behaviour).
  - `old_fix`: 250 m buffer without smoothing (legacy hotfix).
  - `new_fix`: buffered + smoothed mask (current code).
- Case: GEFS init 2025-01-25 00Z, forecast hours 0–36 (6 h step).
- Findings: `no_fix` and `new_fix` match (e.g., p01 10→50 mm through the event); `old_fix` inflates basin snow to 60–105 mm due to high-elevation spillover.
- Figure saved to `figures/baseline_mask_comparison.png` showing both members.
- Note: reverted to the legacy buffered mask (no smoothing) for v0.9.5 so the baseline matches historical runs; schedule mask tuning after the freeze.

### Notes
- Mask smoothing fix effectively removes rim contamination without muting basin snowfall.
- Next steps: run regression triad, attach metrics (percentile MAE, ignorance/reliability for exceedances), and mirror into LaTeX report.
