# Pre-v1 Roadmap (60-Hour Sprint Plan)
Date updated: 2025-11-11

Context: stabilize v0.9.x, run targeted experiments (solar → Random Forest, MF tuning), and align with the LaTeX technical report before declaring v1.0 ready for operational winter 2025/2026 use. The LaTeX repo lives at `/Users/johnlawson/Documents/GitHub/preprint-clyfar-v0p9` (see `docs/EXTERNAL_RESOURCES.md`). Keep code and report synchronized at release boundaries.

## Guiding Principles
1. **Baseline first**: finish v0.9 hardening and documentation before layering experiments.
2. **Experiment scaffolding**: build reusable config/runner pieces so solar-RFR and MF gradient descent share tooling.
3. **Two-way documentation**: every code change feeds into both Markdown docs and the LaTeX technical report 
   (reference sections by label once paths exist).
4. **Time-boxed execution**: assume ~60 person-hours with AI assistance; defer anything that risks derailing the freeze.

## Small Goals (≤4 hours total each)
- Document the baseline (`docs/baseline_0_9.md`), constraints, and smoke scripts (link to LaTeX appendix section).
- Add `clyfar/__init__.py` + `pyproject.toml` skeleton for editable installs.
- Create `scripts/run_smoke.sh` and `scripts/run_regression.sh` wrappers; cite them in both README and LaTeX methodology.
- Stub `configs/examples/baseline.yaml` and `data/<run_id>/run.json` writer for provenance.
- Update onboarding docs with the LaTeX report link/reference number once available.
- Centralize general NWP download scripts in sibling repo `../brc-tools`; reference here to avoid duplication.

## Medium Goals (4–10 hours)
- **Solar → Random Forest prototype**:
  - Replace the current near-zenith heuristic/GEFS scalar with an RFR trained on representative predictors (forecast local time, cos(zenith), cloud proxies, persistence terms) so timezone offsets stop leaking into the MF inputs.
  - Gather training data from the existing preprocessing outputs plus observed solar summaries; serialize the fitted model under `models/solar_rfr.joblib`.
  - Add a feature flag in preprocessing to consume the RFR estimate (and log fallback values) before entering FIS; document methodology + validation in both Markdown and LaTeX (Section “Solar Proxy”).
  - Use this pipeline as the template for future RFR experiments (e.g., pseudo-lapse-rate) so we reuse data plumbing and evaluation scripts.
- **MF gradient-descent tuning**:
  - Externalize membership parameters into YAML.
  - Implement loss function + gradient descent loop (potentially using autograd or manual derivative) for one pollutant.
  - Capture experiment logs and summarize findings in both Markdown (`docs/fis_optimization.md`) and LaTeX.
- **Experiment runner**: implement `python -m clyfar.experiments run --config ...`, log metadata, and support resume-by-member.
- **Data abstraction**: introduce `ForecastDataset` protocol + GEFS wrapper, prepping for HRRR integration post-v1.
- **Snow bias assimilation**:
  - Implement the GEFS snow offset correction (subtract/add the initial observed-minus-forecast delta to the entire time series until the adjusted signal hits zero, then stop) to crudely assimilate representative observations.
  - Evaluate whether HRRR lagged ensembles can supply complementary snow deltas; design hooks so the same adjustment pipeline can swap in higher-resolution sources during v1.1.

## Large Goals (10–20 hours)
- **Packaging & CLI overhaul**: migrate major module families into `clyfar/`, add Typer/Click CLI (`clyfar run`, `clyfar experiment`), keep `run_gefs_clyfar.py` as shim, and document commands in both README + LaTeX.
- **Continuous verification loop**: build CI (GitHub Actions) that runs lint + smoke with cached data, archives artefacts, and posts status badges.
- **Observability + metrics parity**: enrich logging (JSON, timings), compare v0.9 vs experimental runs across a winter-season backfill, and integrate the summary tables into the technical report.

## Sequencing Recommendation
1. **Week 1 (~30 hours)**: complete small goals + baseline documentation, ship smoke/regression scripts, tag `v0.9.5`, and ensure LaTeX references exist.
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
