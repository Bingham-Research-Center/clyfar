# Science Questions
Date updated: 2025-10-09

Living list of science questions to guide Clyfar model improvement and publication work. Add rows as hypotheses emerge; keep cells concise and actionable.

| question | context | proposed analysis | data needed | priority | status | owner |
| --- | --- | --- | --- | --- | --- | --- |
| Is the 60–90 mm snow‑depth transition too narrow? | Snow “sufficient/negligible” ramp: 60→90 mm; above ~90 mm, “sufficient”=1. May be sharp under noise/heterogeneity. | Sweep/widen (e.g., 50–110 mm), evaluate rule‑activations + skill; optimize MF with monotonicity constraints (BO/TPE), cross‑season CV + event‑day checks. | GEFS basin snow‑depth (mm) series; observed ozone; event list; fixed preprocessing. | High (pre‑1.0) | Open | TBD |
| Is the solar “high” ramp (500→700 W m⁻²) appropriate for winter basins? | Current MF: moderate 200–700; high 500→700. Winter peaks often below thresholds. | Replace heuristic with learned surrogate: Random Forest Regression using humidity/cloud proxies, sin/cos(DOY) for clear‑sky geometry, and simple NWP features; compare to clear‑sky index normalization; ablate inputs; choose best by verification. | GEFS SW radiation, RH/cloud proxies, time features; observed ozone; evaluation scripts. | High (pre‑1.0) | Open | TBD |
| Is the MSLP “high” threshold (≈1025→1035 hPa ramp) too high for local climatology? | Rules depend on high MSLP; starvation possible if ramp sits in tail. | Refit breakpoints to local percentiles (e.g., 80–95th); test basin mean/median MSLP vs point; measure rule‑firing rates + forecast skill deltas. | Historical GEFS MSLP fields; basin mask; observed ozone; event list. | High (pre‑1.0) | Open | TBD |

Notes
- Memberships are defined in `fis/v0p9.py` under `_define_membership_functions()`; snow depth is modeled in mm.
- Keep monotonic/ordering constraints on membership shapes during optimization; log parameter sets and resulting metrics for reproducibility.
