# Verification boundary

Start with the [scorecard’s Clyfar handoff](https://github.com/Bingham-Research-Center/forecast-verification-scorecard/blob/main/docs/clyfar-scoring.md).
On CHPC the checkout is `../manuscripts/forecast-verification-scorecard`.
Its manuscript, executable evaluator and synthetic checks own the working
mathematics. V32 is the preliminary pin. Follow the handoff for subsequent
revisions and record the exact commit and evaluator hash used.

## Evaluation input contract

| Source in Clyfar | Use in one evaluation case |
| --- | --- |
| Per-initialization `*_run/parquets/<member>_df.parquet` | Recover initialization and member identity from the run and file. Interpret the native time index as UTC, derive lead and apply the study’s day boundary. |
| `background`, `moderate`, `elevated`, `extreme` | Preserve this order, raw precision and exact zeros. Record maximum raw support (commitment). For positive commitment, divide by that maximum for shape. Count missing and all-zero rows in availability. |
| `ozone_50pc`, companion percentile columns, predictors and clipping flags | The five-winter receiver selects each member’s earliest daily p50 peak and carries the entire row. A componentwise daily maximum or rounded website heatmap represents a different product. |
| Run metadata and FIS source | Record producer version, commit, dirty status, FIS hash, input identity and product hash. |
| Observations and reference from the evaluation study | Declare the event, units, category credit, member or fusion rule, and training-only reference before pairing cases. Keep exact ensemble event counts separate from converted possibility scores. |

The seasonal receiver is the `eval/five-winter-v0p9` branch of the v1
manuscript repository (CHPC worktree `../preprint-clyfar-v0p9-five-winter`).
It owns observation reduction, adapters, replay campaigns, scores and figures.
Its historical evaluator snapshot requires parity against the chosen method
revision before reuse. Keep Clyfar, brc-tools and the older possverif prototype
out of the role of defining scorecard mathematics.
