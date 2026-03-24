# Possibilistic verification ideas for Clyfar (plain language + math)

Goal: evaluate Clyfar operationally when it outputs **possibilities** (what is plausible) rather than **probabilities** (what is likely). We want to reward forecasts that (1) put the observation inside their “plausible range”, (2) stay as tight as possible when confident, and (3) honestly say “I’m unsure” when the rules don’t support any outcome (subnormality).

## Notation (one forecast case, indexed by `t`)

- Observation: daily max ozone `y_t` (ppb). If you verify in ordered bins/categories, write the observed category as `ω_t ∈ Ω`.
- Possibility forecast on ozone values: `π_t(z) ∈ [0,1]`.
  - Read `π_t(z)` as “how compatible is value `z` with the inputs + fuzzy rules”. It is **not** a probability, so it does not need to add up to 1.
  - Subnormality: `m_t = sup_z π_t(z) ≤ 1`. Ignorance (an “unsure” mass): `I_t = 1 - m_t`.
- `α`-cut (a “plausible set” at strictness level `α`): `S_t(α) = { z : π_t(z) ≥ α }` for `α ∈ [0, m_t]`.
  - Bigger `α` means “I only keep values the model finds *very* plausible”, so `S_t(α)` shrinks as `α` increases (nested sets).
  - If `π_t` is roughly single-peaked, `S_t(α)` is usually an interval `[ℓ_t(α), u_t(α)]`.
- Exceedance above a threshold `T`: `A_T = { z ≥ T }`.
  - Possibility of exceedance (upper plausibility): `Π_t(T) = sup_{z≥T} π_t(z)`.
  - Necessity of exceedance (lower certainty): `N_t(T) = 1 - sup_{z<T} π_t(z)`.
  - Plain language: `Π_t(T)` answers “could `y_t ≥ T` happen?” and `N_t(T)` answers “is `y_t ≥ T` basically unavoidable?”.

---

## 1) A score for possibilistic forecasts (use the whole curve, not a single defuzzified number)

### Proposal 1A: `α`-cut weighted interval score (PWIS)

Core idea: treat one possibility curve `π_t` as **many prediction intervals** (`α`-cuts). Then score those intervals the same way we score quantile intervals in classical forecast verification.

Pick a small set of `α` levels, `𝒜 = {α_1, …, α_K}` (example: `α_k = 0.05k`). For each `α`, compute the `α`-cut interval `S_t(α) = [ℓ_t(α), u_t(α)]`.

For each `α`, use the interval score (Gneiting–Raftery):

`IS_t(α) = (u_t(α)-ℓ_t(α)) + (2/α)·(ℓ_t(α)-y_t)_+ + (2/α)·(y_t-u_t(α))_+`

How to read the three terms:
- `(u-ℓ)` rewards **sharpness** (narrower plausible ranges are better).
- The `(_+ )` terms penalize when the observation falls **below** the interval or **above** the interval; the factor `(2/α)` makes misses at high `α` (the “core”) hurt more.

Combine across `α` levels and add an ignorance penalty:

`PWIS_t = κ·I_t + Σ_{α∈𝒜} w(α)·IS_t(α)`  (lower is better)

Recommended weights: `w(α) ∝ α`. Plain language: missing the observation outside the “most plausible” core should count more than missing it outside the low-plausibility fringe.

Why this is a natural “information” proxy for possibility (without Shannon/KL):
- Summing widths across `α` levels measures how *spread out* the curve is. In fact, “total width across all `α`” is mathematically equivalent to “area under `π_t(z)`”. Smaller area ⇒ the forecast rules out more values ⇒ more specific guidance.
- The miss penalties measure how badly reality contradicts what the model called plausible at each strictness level.
- `I_t` explicitly charges the model when it says “I don’t know” (you set `κ` based on how much you want to discourage abstention).

Quick computation recipe (continuous `z`):
1. Choose `𝒜` and weights `w(α)`.
2. For each `α`, compute `[ℓ_t(α), u_t(α)]` from the curve.
3. Compute `IS_t(α)` and sum with weights.
4. Add `κ·I_t`.

Categorical/binned version (if you only have `Ω` categories or ppb bins):
- `S_t(α) = { ω ∈ Ω : π_t(ω) ≥ α }`
- Replace “interval width” with “set size”, and use a miss indicator:
  - `IS^cat_t(α) = |S_t(α)|/|Ω| + (1/α)·1{ω_t ∉ S_t(α)}`
- `PWIS^cat_t = κ·I_t + Σ_{α∈𝒜} w(α)·IS^cat_t(α)`

### Proposal 1B (lighter-weight): contradiction + spread + ignorance

If extracting `α`-cut intervals is annoying, score three simple things:
- Contradiction at the realized value: `C_t = 1 - π_t(y_t)` (or `C_t = -log(π_t(y_t)+ε)` if you want “surprise-like” growth near 0).
- Spread / nonspecificity: `NS_t = (1/L)∫ π_t(z) dz` where `L` is the `z`-domain length (or `NS_t = (1/|Ω|)Σ_ω π_t(ω)` for categories).
- Ignorance: `I_t = 1 - sup_z π_t(z)`.

Combine:

`Score_t = C_t + λ·NS_t + κ·I_t`  (lower is better)

Plain language: “be right” (`C_t` small), “be sharp” (`NS_t` small), and “don’t hide behind uncertainty” (`I_t` small unless you truly need it).

---

## 2) “Climatology” in possibility space (baseline for skill)

We need a baseline forecast of the *same type* (a possibility curve or nested plausible sets), so the skill score compares apples-to-apples.

### Proposal 2A: build a climatology possibility curve from the climatological CDF

Let `F_clim(z)` be the climatological CDF for the relevant regime (e.g., winter only; optionally smooth by day-of-year).

Define:

`π_clim(z) = 1 - 2·|F_clim(z) - 0.5|`

Plain language: values near the climatological median are “most plausible” (`π≈1`), and values deep in either tail are “least plausible” (`π≈0`). This creates a simple, symmetric “climatology possibility curve”.

Key property (why this is useful): its `α`-cuts are exactly central climatological quantile intervals:

`S_clim(α) = { z : π_clim(z) ≥ α } = [Q_clim(α/2), Q_clim(1-α/2)]`

So your baseline automatically produces nested intervals you can score with the exact same PWIS machinery.

### Proposal 2B: categorical climatology (bins/categories)

If you verify on ordered categories/bins, let `f(ω)` be the empirical frequency of category `ω` in the archive. Define:

`π_clim(ω) = f(ω) / max_{ω'} f(ω')`

Plain language: the most common category gets possibility 1, rarer categories get smaller possibility (optionally smooth across adjacent bins if you want a single-peaked baseline).

### Skill score (relative improvement over climatology)

For any score where “lower is better” (e.g., `PWIS`):

`Skill = 1 - mean_t(Score_model) / mean_t(Score_clim)`

Interpretation: `Skill > 0` means Clyfar beats climatology; `Skill = 0` ties; `Skill < 0` is worse than climatology. Compute by lead time too: `Skill(lead=ℓ)`.

---

## 3) Like-for-like comparison with probability and quantile forecasts (without KL/Brier)

Main trick: reduce every method to the same object: a family of nested prediction sets `S_t(α)`. Then score those sets.

### 3A: convert a probabilistic forecast into nested central intervals

Given a probabilistic forecast CDF `F_t`, define the central interval:

`S^prob_t(α) = [Q_t(α/2), Q_t(1-α/2)]`

Now a probabilistic model and Clyfar both yield a nested family of intervals indexed by the same `α`, so you can apply the same PWIS definition to both.

If you only have a few quantiles (e.g., 10/50/90):
- The 10–90 interval is a central 80% interval, which corresponds to `α=0.2` in the formula above.
- Score only the `α` values you actually have for all models (a “partial PWIS”), so the comparison stays fair.

### 3B: “depth-of-truth” (one-number summary that works for both)

Define:

`α*_t = sup{ α : y_t ∈ S_t(α) }`

Plain language: `α*_t` is the strictest level at which the observation is still inside the model’s “plausible set”. Bigger means the observation landed deeper in the model’s core expectations.

For Clyfar: `α*_t = π_t(y_t)`.

For a probabilistic `F_t` using central intervals:

`α*_t = 1 - 2·|F_t(y_t) - 0.5|`

Interpretation: `α*_t≈1` if `y_t` is near the predictive median; `α*_t≈0` if `y_t` is in an extreme predictive tail. Summarize `α*_t` by lead time to show how “surprise” grows with horizon.

### 3C: exceedance-focused score (reduce “exceedance surprise” for operational thresholds)

For an operational threshold `T`, define the observed event `e_t = 1{y_t ≥ T}`. Use possibility/necessity as your forecasted upper/lower bounds for that event:
- `Π_t(T)` = “could exceed `T`?”
- `N_t(T)` = “must exceed `T`?”

Score exceedance surprise + uncertainty + ignorance:

`L_t(T) = e_t·[-log(Π_t(T)+ε)] + (1-e_t)·[-log(1-N_t(T)+ε)] + λ·(Π_t(T)-N_t(T)) + κ·I_t`

How to read this:
- If an exceedance happens (`e_t=1`) and the model said it was barely possible (`Π_t(T)` small), you pay a big penalty.
- If no exceedance happens (`e_t=0`) and the model said exceedance was nearly certain (`N_t(T)` large), you pay a big penalty.
- `(Π-N)` is the model’s “I’m not sure” interval width for the event; penalizing it encourages more informative forecasts.
- `I_t` still tracks global ignorance/subnormality.

Compute `mean_t L_t(T)` for thresholds like `T = 60, 70, 75 ppb`, and by lead time.

Optional (useful operationally): does Clyfar know when it might be wrong?
- Check whether `I_t` is larger on high-error days, e.g. Spearman `ρ( I_t, |ĉ_t - y_t| )` where `ĉ_t` is the centroid/median you already compute.
- Or treat “large error” as an event and compute AUC using `I_t` as the ranking score (abstention/quality-control value).

---

## Clarifications (these choices change the “right” score)

1. Verify on continuous `π_t(z)` (ppb curve), or only on a few ozone categories?
2. Should “unsure” (`I_t`) be treated as honest abstention (small `κ`) or as reduced usefulness (large `κ`)?
3. Which thresholds `T` matter operationally (one threshold like 70 ppb vs a small set)?
