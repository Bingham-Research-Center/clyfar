# ML Ideas for Clyfar Evolution
Date updated: 2025-09-25

## Optimising Membership Functions & Variables
- Gradient-based tuning
  - Use differentiable surrogate (e.g., Gaussian Process) to approximate FIS output gradients.
  - Optimise MF parameters via Adam with regularisation on overlap.
  - Inject constraints ensuring linguistic labels retain ordering (e.g., calm < breezy).
- Bayesian optimisation
  - Treat MF breakpoints as hyperparameters; use TPE or BO to minimise forecast error.
  - Batch-evaluate candidate MF sets using cached datasets to reduce runtime.
- Sensitivity analysis
  - Perform Sobol indices to rank variable influence; drop low-impact inputs.
  - Use SHAP on FIS surrogate to understand membership weight contributions.
- Adaptive variable selection
  - Train L1-penalised meta-model to identify redundant variables before adding rules.
  - Build feature toggles in configs to allow quick A/B comparisons.

## Genetic & Evolutionary Strategies for Rules
- Grammar-guided genetic programming
  - Define rule syntax grammar; evolve rule combinations with fitness = forecast skill.
  - Maintain interpretability by penalising depth/complexity during selection.
- NSGA-II for multi-objective search
  - Optimise for accuracy, sparsity, and interpretability simultaneously.
  - Keep Pareto front snapshots for human review.
- Population seeding
  - Start GA with existing expert rules; mutate antecedent thresholds or consequents.
  - Constrain mutations to preserve physical plausibility (e.g., high solar ↔ higher ozone).

## Balancing Complexity vs Simplicity
- Complexity budget
  - Set explicit caps on #variables, #rules, and MF overlaps per variable.
  - Track model size metrics in `run.json` and enforce alerts when exceeding thresholds.
- Pruning schedule
  - After optimisation, run pruning pass removing rules with minimal activation frequency.
  - Use Akaike/BIC-style penalties in optimisation objective.
- Hierarchical modelling
  - Decompose into modular sub-FIS (e.g., snow block, solar block) feeding a meta-FIS.
  - Allows swapping modules without exploding rule count.

## Communicating Possibility & Ignorance
- Possibility distributions with ignorance term
  - Allow subnormal distributions; compute `ignorance = 1 - max(possibility)`. 
  - Surface "unsure" band in plots and data exports.
- Alternative visualisations
  - Add fan charts showing upper/lower envelopes of possibility mass.
  - Provide categorical timelines with opacity scaled by certainty.
- Narrative outputs
  - Generate templated text summarising most plausible category + ignorance statement.
  - Include reasons (active rules, dominant drivers) for transparency.

## Lean Execution Principles
- Regular pruning
  - Schedule quarterly reviews to retire unused variables, rules, configs.
  - Maintain `CHANGELOG` entries noting removals for traceability.
- Minimal surfaces
  - Keep notebooks slim; migrate logic into modules with tests.
  - Prefer shared utilities over copy-pasted code snippets.
- Experiment hygiene
  - Archive obsolete experiment configs; tag active ones clearly (e.g., `v1.1-PLR`).

## Future Delivery & API
- API blueprint
  - Design REST/GraphQL endpoints serving time series of percentile forecasts, possibility bands, and ignorance.
  - Include metadata (init time, version, config hash) for reproducibility.
- Serialization standards
  - Export standard JSON schema for downstream dashboards.
  - Support `pandas`-friendly formats (parquet/arrow) for bulk data.
- Templated reporting
  - Auto-render static images (heatmaps, percentile plots) + interactive dashboards via Panel/Altair.
  - Provide CLI flag to push artefacts to web storage or CMS.

---

## Plain Language Summary
- Sharpen the fuzzy system by tweaking the shapes of membership curves with tools like gradient descent or Bayesian search. Keep the labels in the right order and drop inputs that do not matter much.
- Try evolutionary tricks—think genetic algorithms—to invent new IF/THEN rules while punishing overly complicated rule sets.
- Put limits on the number of variables and rules so the model stays simple. Remove rarely used rules and split the system into smaller, easier-to-read blocks when it grows.
- When we report possibilities, allow an "unsure" bucket to show how much we simply do not know. Visuals can fade or widen when confidence drops, and short text summaries can explain why a certain risk level was chosen.
- Keep the code lean: routinely delete stale experiments, move copy-pasted notebook code into tested modules, and keep a changelog of what was removed.
- Plan for sharing results through an API that spits out time series, risk bands, and metadata. Store outputs in friendly formats and provide scripts that publish charts or dashboards automatically.
