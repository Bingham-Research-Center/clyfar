# Verification Boundary

This frozen repository supplies Clyfar forecasts and provenance; it does not
own the evolving scorecard mathematics or a scoring-library implementation.

## Authority

The live equations in `../latex-poss-verif-clyfar/sections/` and
`../latex-poss-verif-clyfar/scripts/minimal_reference_evaluator.py` own the
verification mathematics.  Record their repository commit and working-tree
state in each evaluation manifest.  Historical notes and `possverif` do not
override that source.

`../possverif` version 0.1.0 is a prototype of the earlier formulation. It
implements the redundant five-number card, a reserved ignorance probability
bin, and verification-time probability flooring. Do not add it as a Clyfar
dependency or treat its tests as the new scorecard specification.

## Evaluation input contract

Preserve, at minimum:

- initialization, verification day, UTC/standard/civil valid times, lead,
  member, and input-source identity;
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

The daily verification clock is fixed Mountain Standard Time (UTC-07:00), as
used for the EPA ozone standard; `America/Denver` civil time is retained only
for display and daylight-saving audit.  For each member, maximise unrounded
`ozone_50pc` on the standard-time day, choose the earliest valid time on a tie,
and carry every other scalar, possibility, and predictor field from that same
row.  This coherent peak is Clyfar's MDA8 analogue; it is not a rolling average
of the forecast sequence.

For observations, calculate the 17 station eight-hour means beginning
07:00--23:00 standard time.  A window ordinarily requires six valid hours; a
station day ordinarily requires 13 valid windows.  Retain the standard's
above-70-ppb completeness exceptions after window truncation, an unrounded
primary value, and a parallel whole-ppb truncation audit.  Select each
station's earliest maximum
window in each precision stream after that stream's declared truncation, then
apply the declared spatial quantile across eligible stations.  Retain both
selected times when truncation changes the peak window.
Never add one day to an observation timestamp.  Preserve every window, valid
hour count, selected time, QC status, requested/returned station identity, and
reducer parameter.  The Basin spatial quantile is an EPA-aligned verification
target, not a regulatory site design value.

Historical full-resolution forecast Parquets remain valid inputs.  Dailymax
Parquets, possibility exports, percentile exports other than the p50 maximum,
daily possibility figures, and every forecast--observation match made with the
old next-day or civil-day label require regeneration before verification.  The
p50 peak and member exceedance count should retain the fixed-MST operator
identity in derived tables.  MSLP, wind, and snow reducers retain physical
`America/Denver` dates after removal of their former shift; solar already used
its physical local date.

Evaluate strict exceedance of 40, 50, 60, and 70 ppb from the same unrounded
Basin MDA8 target, with 50 ppb primary.  Require all 31 members for primary
probability results and retain exact issued fractions.  Do not extend the
threshold ladder above 70 ppb without observed support and a new declared
analysis decision.

The implementation covers signed truth margin, diffuseness, ordinal miss
distance, cumulative-log information regret, difficulty calibration, and
alpha-cut coverage. Score normalised shape separately from commitment; do not
make a non-verifying ignorance bin or an after-the-fact epsilon floor part of
the closed-world score.  Zero-support log contradictions remain infinite and
visible.

Develop the evaluator on an `eval/<name>` branch or in a dedicated scoring
package. Keep evaluation datasets, bootstrap products, plots, and reports
outside this checkout.
