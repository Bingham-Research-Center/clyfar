# Pre-v1 Roadmap (60-Hour Sprint Plan)
Date: 2025-11-15

Context: stabilize v0.9.x, run targeted experiments (solar → Random Forest, MF tuning), and align with the LaTeX technical report before declaring v1.0 ready for operational winter 2025/2026 use. The LaTeX source is not currently in this repo (no `.tex` files detected). Add its location to documentation ASAP so code + report stay synchronized.

## Guiding Principles
1. **Baseline first**: finish v0.9 hardening and documentation before layering experiments.
2. **Experiment scaffolding**: build reusable config/runner pieces so solar-RFR and MF gradient descent share tooling.
3. **Two-way documentation**: every code change feeds into both Markdown docs and the LaTeX technical report (reference sections by label once paths exist).
4. **Time-boxed execution**: assume ~60 person-hours with AI assistance; defer anything that risks derailing the freeze.

## Small Goals (≤4 hours total each)
- Document the baseline (`docs/baseline_0_9.md`), constraints, and smoke scripts (link to LaTeX appendix section TBD).
- Add `clyfar/__init__.py` + `pyproject.toml` skeleton for editable installs.
- Create `scripts/run_smoke.sh` and `scripts/run_regression.sh` wrappers; cite them in both README and LaTeX methodology.
- Stub `configs/examples/baseline.yaml` and `data/<run_id>/run.json` writer for provenance.
- Update onboarding docs with the LaTeX report link/reference number once available.

## Medium Goals (4–10 hours)
- **Solar → Random Forest prototype**:
  - Gather solar predictors from existing preprocessing outputs.
  - Train an RFR (scikit-learn) offline, serialize under `models/solar_rfr.joblib`.
  - Add feature flag in FIS preprocessing to consume RFR output; document method in LaTeX (e.g., Section “Solar Proxy”).
- **MF gradient-descent tuning**:
  - Externalize membership parameters into YAML.
  - Implement loss function + gradient descent loop (potentially using autograd or manual derivative) for one pollutant.
  - Capture experiment logs and summarize findings in both Markdown (`docs/fis_optimization.md`) and LaTeX.
- **Experiment runner**: implement `python -m clyfar.experiments run --config ...`, log metadata, and support resume-by-member.
- **Data abstraction**: introduce `ForecastDataset` protocol + GEFS wrapper, prepping for HRRR integration post-v1.

## Large Goals (10–20 hours)
- **Packaging & CLI overhaul**: migrate major module families into `clyfar/`, add Typer/Click CLI (`clyfar run`, `clyfar experiment`), keep `run_gefs_clyfar.py` as shim, and document commands in both README + LaTeX.
- **Continuous verification loop**: build CI (GitHub Actions) that runs lint + smoke with cached data, archives artefacts, and posts status badges.
- **Observability + metrics parity**: enrich logging (JSON, timings), compare v0.9 vs experimental runs across a winter-season backfill, and integrate the summary tables into the technical report.

## Sequencing Recommendation
1. **Week 1 (~30 hours)**: complete small goals + baseline documentation, ship smoke/regression scripts, tag `v0.9.0`, and ensure LaTeX references exist.
2. **Week 2 (~20 hours)**: tackle medium goals—RFR prototype, MF tuning scaffolding, experiment runner, and data abstraction. Each experiment should have a matching section or appendix entry in LaTeX.
3. **Final stretch (~10 hours)**: focus on large goals that unblock future work (packaging/CLI, observability). Defer CI if it jeopardizes v1 timeline; otherwise, land a minimal pipeline that runs the smoke test on PRs.

## Coordination with Technical Report
- Add a “Documentation sync” subsection in `docs/baseline_0_9.md` (and LaTeX) listing the latest code commit and report commit/Overleaf version.
- When new experiments run, create paired entries: Markdown summary + LaTeX subsection (include figure/table labels). Keep a `docs/report_sync.md` log pointing both ways.
- If the LaTeX repo is private, store a text pointer (URL or repo path) plus contact instructions in `docs/README.md` and `docs/AI_AGENT_ONBOARDING.md` to keep AI agents aligned.

## Definition of Done for v1.0 Prep
- Baseline v0.9 artefacts locked, reproducible, and mirrored in LaTeX.
- At least one alternative solar input (RFR) and one MF optimization experiment completed with documented impact.
- Experiment runner + provenance logging in place for future studies.
- Packaging/CLI rework started (even if final polish lands post-v1) so the project is ready for distribution.
- Final validation checklist (docs/v0p9_testing_checklist.md) fully executed and referenced in both Markdown + LaTeX deliverables.
