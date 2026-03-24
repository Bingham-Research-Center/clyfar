# Possibilistic verification ideas for Clyfar

Goal: evaluate Clyfar operationally using its **possibility outputs** (not crisp yes/no; not probabilities), with emphasis on “reduced exceedance surprise” and honest communication of **ignorance** (subnormality / “unsure” mass).

## Notation (per forecast instance `t`)

- Observation (daily max ozone): `y_t ∈ ℝ` (ppb) or ordered category `ω_t ∈ Ω`.
- Forecast possibility distribution on ozone values: `π_t(z) ∈ [0,1]`, possibly **subnormal**.
  - `m_t = sup_z π_t(z) ≤ 1`, `I_t = 1 - m_t` (ignorance / “unsure”).
- `α`-cut set: `S_t(α) = { z : π_t(z) ≥ α }` for `α ∈ [0, m_t]`.
  - For unimodal outputs, `S_t(α)` is typically an interval `[ℓ_t(α), u_t(α)]`.
- Exceedance event for threshold `T`: `A_T = { z ≥ T }`
  - Upper plausibility: `Π_t(T) = Π_t(A_T) = sup_{z≥T} π_t(z)`
  - Lower certainty: `N_t(T) = N_t(A_T) = 1 - sup_{z<T} π_t(z)`

---

## 1) A score for possibilistic forecasts (distribution-level, not defuzzified)

### Proposal 1A: `α`-cut weighted interval score (set-based; sharpness + miss penalty)

Treat a possibility distribution as a **nested family of prediction sets**. Score those sets.

Choose a grid `𝒜 = {α_1, …, α_K}` (e.g., `α_k = 0.05k`).

For each `α ∈ 𝒜`, compute the `α`-cut interval `S_t(α) = [ℓ_t(α), u_t(α)]` and define the (Gneiting–Raftery) interval score:

`IS_t(α) = (u_t(α)-ℓ_t(α)) + (2/α)·(ℓ_t(α)-y_t)_+ + (2/α)·(y_t-u_t(α))_+`

Then define the possibilistic score (lower is better):

`PWIS_t = κ·I_t + Σ_{α∈𝒜} w(α)·IS_t(α)`

Recommended weights: `w(α) ∝ α` (punish misses in the high-possibility “core” more than in the low-possibility “tails”).

Why it’s possibility-native (and “information-ish” without Shannon/KL):
- The **sharpness term** integrates set sizes: `∫ |S_t(α)| dα = ∫ π_t(z) dz` (Fubini). That is a maxitive/nested-set analogue of “nonspecificity”: small area under `π` = more specific forecast.
- The **miss penalties** ask: how far outside the plausible set did reality fall, and at what plausibility level?
- `I_t` explicitly prices subnormal “I don’t know”.

Categorical / binned variant (ordered `Ω` or bins):
- `S_t(α) = { ω ∈ Ω : π_t(ω) ≥ α }`
- Replace width with set size and miss indicator:
  - `IS^cat_t(α) = |S_t(α)|/|Ω| + (1/α)·1{ω_t ∉ S_t(α)}`
- `PWIS^cat_t = κ·I_t + Σ w(α)·IS^cat_t(α)`

### Proposal 1B (simpler): contradiction + nonspecificity + ignorance

If you want something you can compute even without extracting `α`-cuts cleanly:
- “Contradiction” of the realized value: `C_t = 1 - π_t(y_t)` (or `-log(π_t(y_t)+ε)`)
- “Nonspecificity” (area under the curve): `NS_t = (1/L)∫ π_t(z) dz` where `L` is domain length (or `NS_t = (1/|Ω|)Σ_ω π_t(ω)` for categories)

`Score_t = C_t + λ·NS_t + κ·I_t`

This is a compact “be right, be sharp, admit ignorance” loss.

---

## 2) “Climatology” in possibility space (for skill scores)

You want a baseline `π_clim` that is **not** a probability forecast, but still yields nested sets to compare against.

### Proposal 2A: climatology as quantile-induced consonant possibility

Let `F_clim(z)` be the climatological CDF for the relevant season/regime (e.g., winter only; optionally day-of-year smoothed).

Define a climatological possibility distribution:

`π_clim(z) = 1 - 2·|F_clim(z) - 0.5|`

Then the `α`-cuts are exactly climatological central quantile intervals:

`S_clim(α) = { z : π_clim(z) ≥ α } = [Q_clim(α/2), Q_clim(1-α/2)]`

This is operationally handy because it makes “climatology” look like a nested plausibility family (same object type as Clyfar’s `α`-cuts), without interpreting `α` as probability.

### Proposal 2B: frequency-normalized categorical climatology

For ordered categories `Ω` (or ppb bins), let `f(ω)` be the empirical frequency in the archive.

`π_clim(ω) = f(ω) / max_{ω'} f(ω')`

(Optionally smooth across adjacent bins/categories if you want unimodality.)

### Skill score

For any loss where “lower is better” (e.g., `PWIS`):

`Skill = 1 - mean_t(Score_model) / mean_t(Score_clim)`

Compute per lead `ℓ` as well: `Skill(lead=ℓ)` to show horizon decay (the operational question).

---

## 3) Like-for-like comparisons with probabilistic and quantile forecasts (without KL/Brier)

Key trick: compare everything as **nested prediction sets** `S_t(α)`, then score those sets (e.g., `PWIS`).

### 3A: put probability forecasts into the same “nested-set” shape

Given a probabilistic forecast CDF `F_t`, define:

`S^prob_t(α) = [Q_t(α/2), Q_t(1-α/2)]`

Now `S^prob_t(α)` and Clyfar’s `S_t(α)` are both just families of intervals indexed by `α`, so you can apply **the same** `PWIS` definition to both.

If you only have quantiles (e.g., 10/50/90):
- Score only the corresponding `α` levels you have (e.g., 10–90 is central 80% ⇒ `α=0.2`) using the interval-score piece at those `α`.
- This is a “partial PWIS” analogous to a reduced WIS; still apples-to-apples if you apply the same `α` set to all methods.

### 3B: a common “depth-of-truth” index

Define the maximum plausibility level whose cut-set still contains the observation:

`α*_t = sup{ α : y_t ∈ S_t(α) }`

For Clyfar, `α*_t = π_t(y_t)`.
For probabilistic `F_t` using central intervals, `α*_t = 1 - 2·|F_t(y_t) - 0.5|`.

This gives a like-for-like, unitless “how deep into the core did reality land?” quantity that can be summarized (mean, quantiles) vs lead time, without ever treating forecasts as additive probabilities.

### 3C: exceedance-focused comparison (surprise reduction for operational thresholds)

For a threshold `T`, define a binary outcome `e_t = 1{y_t ≥ T}` and score **plausibility + certainty + informativeness**:

`L_t(T) = e_t·[-log(Π_t(T)+ε)] + (1-e_t)·[-log(1-N_t(T)+ε)] + λ·(Π_t(T)-N_t(T)) + κ·I_t`

Compute `mean_t L_t(T)` for operational thresholds (`T = 60, 70, 75 ppb`, etc.) and per lead time. This directly answers: “did the model stop being *surprised* by exceedances earlier than climatology?”

Optional (Clyfar-specific) “self-awareness” check:
- Does `I_t` predict when Clyfar will be wrong?
  - Example metric: Spearman `ρ( I_t, |ĉ_t - y_t| )`, where `ĉ_t` is the centroid (or any scalar summary you already compute).
  - Or treat “large error” as an event and compute AUC using `I_t` as the ranking score (abstention/quality-control value).

---

## Clarifications that affect which score is best

1. Do you want verification on the continuous `π_t(z)` curve, or only on 4 categories (`background/moderate/elevated/extreme`)?
2. Should subnormality be rewarded as “honest abstention” (small `κ`), or penalized as “not operationally useful” (large `κ`)?
3. Which exceedance thresholds matter operationally (e.g., `T=70 ppb` only, or multiple)?
