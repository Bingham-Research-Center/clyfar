# Clyfar Prioritized TODOs
Date updated: 2026-03-02

This is the active, operations-focused TODO list for the current clyfar line (`v1.0.2`).

Ordering combines:
1. Likelihood the work will be done in the near term.
2. Estimated implementation effort.

## Tier 1: High Likelihood, Low-Medium Effort
1. Snow edge-pixel validation closure
Status: `in progress` via `docs/v1_0_readiness.md` Gate 1.
Goal: finish deep-dive bias/MAE evidence and decide keep/adjust criteria.
2. Solar time/physics regression safety
Status: `in progress` via `docs/v1_0_readiness.md` Gate 2.
Goal: keep DST and >240h persistence tests green; extend coverage as edge cases appear.
3. Herbie cache operational hardening
Status: `open` (README TODO).
Goal: add cache hygiene options (`--fresh-cache` or per-job cache isolation) in the production path.
4. Version metadata consistency
Status: `active`.
Goal: keep all operational outputs sourcing clyfar version from `__init__.__version__`; avoid stale hardcoded values.

## Tier 2: High Likelihood, Medium Effort
1. Packaging and install hygiene
Goal: complete `pyproject.toml` + editable-install workflow and stable import path guarantees.
2. Public API contracts for stage boundaries
Goal: define typed interfaces for ingest/preprocess/FIS/export so changes are easier to test and review.
3. Experiment runner provenance tightening
Goal: ensure run metadata (`run.json`, config hash, commit) is complete and consistent across operational/ad hoc runs.

## Tier 3: Medium Likelihood, Higher Effort
1. CLI consolidation
Goal: move orchestration to a first-class CLI while keeping `run_gefs_clyfar.py` as a stable shim.
2. CI smoke + regression automation
Goal: PR-level lint/tests/smoke with cached deps and artifact publication.
3. Data ingest abstraction for multi-model support
Goal: formalize GEFS/HRRR-compatible interfaces and tests for parity.

## Tier 4: Lower Likelihood Near-Term, Research-Oriented
1. Solar proxy ML experiments (e.g., RFR variants) for potential post-v1 upgrades.
2. MF optimization loops (gradient/heuristic tuning) with reproducible experiment reporting.
3. Broader observability stack (JSON logs, dashboards, automated run-quality summaries).

## Source Documents
- `docs/v1_0_readiness.md`
- `docs/v1_0_risk_register.md`
- `docs/roadmap.md` (historical planning context)
- `docs/pre_v1_roadmap.md` (historical planning context)
