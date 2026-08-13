# Verification Boundary

This frozen repository supplies Clyfar forecasts and provenance; it does not
own the evolving scorecard mathematics or a scoring-library implementation.

## Authority

Before evaluation work, locate the live rigour note rather than copying an old
scorecard into this tree:

```bash
rg --files ../brc-knowledge | rg 'scorecard-rigour.*\.md$'
```

Select one source explicitly and record its path, sibling-repository commit,
working-tree state, and file hash in the run manifest. The current
`possibilistic-verification-methods.md` is an earlier reference and may conflict
with the newer rigour note.

`../possverif` version 0.1.0 is a prototype of the earlier formulation. It
implements the redundant five-number card, a reserved ignorance probability
bin, and verification-time probability flooring. Do not add it as a Clyfar
dependency or treat its tests as the new scorecard specification.

## Evaluation input contract

Preserve, at minimum:

- initialization, valid time/local day, lead, member, and input-source identity;
- ordered category labels and the unrounded raw possibility vector;
- commitment and normalized shape as separate, reproducible quantities;
- observed ozone and the exact category-threshold mapping used;
- Clyfar version, FIS treatment identity, commit/dirty state, and data lineage.

Use member-level parquet output for scoring; exported heatmap JSON is rounded
for communication. Keep the ensemble-member axis until the evaluation defines
whether it scores members separately or scores one declared fusion operator.
Likewise, verify that the local-day aggregation represents the forecast event
being scored before treating componentwise daily maxima as a categorical
possibility distribution.

The new implementation must cover the rigour note's independent per-forecast
and sample quantities, including signed truth margin, diffuseness, ordinal miss
distance, difficulty calibration, and alpha-cut coverage. Score normalized
shape separately from commitment; do not make a non-verifying ignorance bin or
an after-the-fact epsilon floor part of the closed-world score.

Develop the evaluator on an `eval/<name>` branch or in a dedicated scoring
package. Keep evaluation datasets, bootstrap products, plots, and reports
outside this checkout.
