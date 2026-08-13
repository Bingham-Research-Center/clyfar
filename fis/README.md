# Fuzzy Inference System Boundary

`fis/v0p9.py` is the accepted production control. `run_gefs_clyfar.py` imports
its `Clyfar` class and forecast/geographic metadata directly. `fis/fis.py`
contains the generic fuzzy-inference helpers.

The control contract is:

- inputs named `snow`, `mslp`, `wind`, and `solar`, with declared units and
  universes in `fis/v0p9.py`;
- `compute_ozone(...)` returning percentile values plus an unnormalised
  possibility value for each ozone category;
- stable category names and member/time output columns consumed by plotting,
  export, replay, and future verification.

Do not edit `v0p9.py` in place for optimisation. On an `exp/<factor>/<name>`
branch, add one treatment implementation or configuration, keep `v0p9` as the
control, and make selection explicit in run provenance. Optimizer output only
becomes source after its parameters and constraints are frozen and reviewable.

Rule search, membership-function tuning, a fifth pseudo-lapse-rate antecedent,
and upstream bias correction are separate treatments. Preserve raw predictors
beside any corrected predictors and require every treatment to emit the same
forecast/evaluation contract. Historical FIS modules remain available from Git
history rather than as selectable-looking files in the frozen tree.
