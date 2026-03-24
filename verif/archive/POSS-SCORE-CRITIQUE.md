# Review + critique: possibilistic scoring ideas for Clyfar

*Date written: 2026-01-22 (updated after reading scholarium summaries)*  
*Primary target doc: `verif/POSS-SCORE-IDEAS-PLAIN.md`*  
*Key context docs:*  
- `../brc-knowledge/scholarium/active-projects/clyfar/summary-clyfar-prototype.md`  
- `../brc-knowledge/scholarium/active-projects/clyfar/summary-fuzzy-inference.md`  
- `../brc-knowledge/scholarium/active-projects/clyfar/summary-possibility-theory.md`  
- `../brc-knowledge/scholarium/active-projects/clyfar/summary-poss-subnormal.md`  
- (Older background) `../brc-knowledge/archive/2025-11-pre-overhaul/POSSIBILITY-SUBNORMAL-MATH.md`

## 0) What problem are we actually solving?

Clyfar outputs **possibilities** (how compatible outcomes are with rules/evidence), not **probabilities** (how likely outcomes are).

So the verification problem is:

> Given observations `y_t` and possibilistic forecasts `π_t(·)`, define a score that rewards forecasts that  
> (i) make the observation “plausible”,  
> (ii) are as *specific/sharp* as possible, and  
> (iii) handle **subnormality** (explicit “we don’t know”) in a sensible, non-gameable way.

A stretch goal is an “apples-to-apples” comparison against probabilistic forecasts (CDFs/quantiles/ensembles) and/or deterministic forecasts.

## 0.1) Extra context that affects what “good verification” means

From the four `summary-*` docs, the **purpose** of the possibilistic product is not “probability replacement”:

- The guiding question is *conservative and risk-averse*: “**could** a hazardous event happen?” rather than “how likely?” (`summary-possibility-theory.md`).
- Clyfar is explicitly meant to communicate **second-order uncertainty** (uncertainty about the model’s own knowledge) via **subnormality** and an “unsure” amount (`summary-poss-subnormal.md`).
- In cusp / tipping-point situations, the FIS can output **subnormal** distributions, and the docs treat that as a *feature* (“rules don’t strongly support any outcome; be honest”) rather than a bug (`summary-clyfar-prototype.md`, `summary-fuzzy-inference.md`).
- A core motivation is that a scalar “centroid” can **mute tail risk**; the possibility distribution may still flag an extreme as unusually plausible even when the centroid forecast is wrong (`summary-clyfar-prototype.md`).

Implication: it may be better to report a **scorecard** (e.g., tail-risk ranking skill + sharpness + ignorance) than to force everything into one “probability-like” score.

## 1) Minimal definitions that stay consistent under subnormality

### 1.1 Raw vs normalized possibility

Let Clyfar output a *raw* possibility distribution `π_raw(z) ∈ [0,1]`.

Define the **subnormality level**

`m = sup_z π_raw(z)`  (so `m ∈ [0,1]`)

and the **ignorance / unsure amount**

`I = 1 - m`.

(In the brc-knowledge summaries this same idea also appears as “unsure” or `H_Π`; and in the Π/N/U framework it’s the `U` term. They’re all aiming at the same concept: “how much the system can’t support any outcome.”)

If `m > 0`, define the **normalized shape**

`π_norm(z) = π_raw(z) / m`, so `sup_z π_norm(z) = 1`.

This split is important:

- `π_norm` describes *shape / relative preferences* among outcomes.
- `I` describes *how much the system is abstaining / missing evidence*.

### 1.2 Events, possibility, and necessity (the key “gotcha”)

For any event `A` (example: `A_T = {z ≥ T}`),

`Π_norm(A) = sup_{z∈A} π_norm(z)`

and the **classical** necessity is

`N_norm(A) = 1 - Π_norm(A^c)`.

This classical duality **only behaves as intended when the distribution is normalized**.

If you apply `N(A)=1-sup_{z∈A^c} π_raw(z)` directly to a *subnormal* `π_raw`, you can get nonsense like “A is almost necessary” even when “A is barely possible”.

Concrete example (first-year-undergrad level):

- Suppose `π_raw(z) ≤ 0.3` for *all* `z`. Then `m=0.3`, so `I=0.7`.
- For any non-trivial event `A`, you’ll have `Π_raw(A) ≤ 0.3` and `Π_raw(A^c) ≤ 0.3`.
- If you define `N_raw(A) = 1 - Π_raw(A^c)`, then `N_raw(A) ≥ 0.7`.
- That violates the basic consistency intuition `N(A) ≤ Π(A)` (“something can’t be more certain than it is possible”).

So: **use normalized `π_norm` for necessity-style quantities, and keep ignorance `I` separate**.

Practical alignment with code:

- `postprocesing/possibility_funcs.py` normalizes (max→1) before computing necessity-like outputs.
- It computes `unsure = 1 - max(raw)` from subnormality.

That same split should appear in verification formulas.

## 2) Critique of the current proposals in `POSS-SCORE-IDEAS-PLAIN.md`

This section is intentionally picky: the goal is to prevent subtle math errors from becoming “verification folklore”.

### Issue A — Necessity under subnormality (major)

The doc defines for thresholds:

`N_t(T) = 1 - sup_{z<T} π_t(z)`.

If `π_t` is subnormal, this can make `N_t(T)` artificially large even when the model is basically saying “I have no idea”.

**Correction**: compute conditional/normalized necessity from `π_norm`, and separately track ignorance `I`.

This matches the “tripartite” communication idea in `summary-poss-subnormal.md`: report (possibility, ignorance, conditional necessity) rather than letting subnormality accidentally turn into “false certainty”.

### Issue B — `α` plays two different roles

The “interval score” formula used is from probabilistic verification, where `α` means a **miscoverage probability** (a target like 10% miss rate for a 90% interval).

In the doc, `α` is also used as an **α-cut level** in a possibility distribution (“keep points with possibility ≥ α”).

Those are *not* the same concept in general.

Why it matters:

- In probabilistic scoring, the coefficient `(2/α)` is not arbitrary: it’s what makes the score “proper” (incentive-compatible) for interval forecasts at nominal level `1-α`.
- In possibility scoring, unless you have a calibrated mapping from α-cut levels → empirical coverages, `(2/α)` is just a weight choice, not a principled constant.

**Two clean fixes**:

1) **Rename** the possibility cut level to something like `r ∈ (0,1]` (“relative plausibility level”), to avoid accidental probability interpretation.
2) If you *want* probabilistic comparability, **calibrate** `r` levels to empirical coverages and then use interval scores at those coverages (details in §3B).

### Issue C — “Area under π” as sharpness can be gamed by subnormality

The doc suggests using

`NS = (1/L) ∫ π(z) dz`

as “nonspecificity / spread”.

But if you use the *raw* `π_raw`, making everything smaller (more subnormal) shrinks the area and looks “sharper”, even though it’s less informative.

**Fix**: compute nonspecificity on the normalized shape, e.g.

`NS_shape = (1/L) ∫ π_norm(z) dz`

and keep `I` separate.

Equivalent “layer-cake” view:

`∫ π_norm(z) dz = ∫_0^1 |S_norm(r)| dr`

where `S_norm(r) = {z : π_norm(z) ≥ r}`.

### Issue D — Handling `α = 0` and `α > m`

Any formula with `1/α` or `2/α` must **exclude** `α=0`.

Also, for subnormal cases (`m < 1`), any α-cut at `α > m` is empty. The doc doesn’t say what to do then.

**Fix**: either

- work with normalized `π_norm` and `r ∈ (0,1]`, or
- define α-grid as `α_k = r_k · m_t` (relative cuts), or
- explicitly “skip α-cuts above `m_t`”.

### Issue E — Discrete categories: “width” should respect ordering/bin widths

The categorical score suggestion uses `|S(α)|/|Ω|` as a width proxy.

This is fine if bins are equal-width and the α-cuts always form a contiguous block of ordered categories.

But:

- if bins aren’t equal, “size” is not “width in ppb”.
- if outputs are multi-modal, `S(α)` can be non-contiguous (e.g., `{background, extreme}`), and `|S|` hides that weirdness.

**Fix**: for ordinal categories, consider width as

`width(S) = (max_index(S) - min_index(S)) / (K-1)`

or (better) use actual ppb bin widths if available.

### Issue F — Verifying only a defuzzified number is misaligned with the project goal

The broader project context (especially `summary-clyfar-prototype.md`) is that the possibility outputs exist because centroid/defuzzified values can hide:

- tail risk (e.g., “extreme category ranked in top few %”)
- epistemic gaps (subnormality in cusp situations)

So, if the verification target is “does Clyfar communicate second-order uncertainty well?”, any metric that collapses to a single ppb value is at best incomplete.

## 3) Scoring methods that (a) respect subnormality, and (b) can compare across forecast types

I’m proposing several options because your “best” choice depends on what you want the score to mean.

### 3A) Option 0: A tripartite verification scorecard (aligns with the communication goal)

This follows `summary-poss-subnormal.md` directly. For each case `t`, compute:

1) **Ignorance:** `I_t = 1 - sup_z π_raw,t(z)` (how “unsure” Clyfar is)
2) **Conditional/normalized shape:** `π_norm,t` (relative plausibilities)
3) **Conditional necessity for key events:** `N_t(A)` computed from `π_norm,t`

Then verify *three separate questions*:

- **Tail-risk ranking:** do high `Π_norm(A_T)` (or high `π_norm(extreme)`) days line up with actual exceedance days?
- **Sharpness:** are the cut-sets of `π_norm` tight when Clyfar is confident?
- **Self-awareness:** is `I_t` larger on hard/low-skill days?

This is often easier to interpret (and harder to game) than a single combined score.

### 3A) Option 1: Normalized cut-set score + explicit ignorance penalty (simple, robust)

This is the “fix the math, keep the spirit” version of PWIS.

1) Split `π_raw` into `π_norm` and `I`.
2) Choose a grid of **relative cut levels** `r ∈ 𝓡 ⊂ (0,1]` (example: `𝓡 = {0.1,0.2,…,1.0}`).
3) For each `r`, define the cut-set `S_norm(r) = {z : π_norm(z) ≥ r}`.

For continuous `z`, if `S_norm(r)` is an interval `[ℓ(r), u(r)]`, define a generic “set score”

`SS(r) = (u(r)-ℓ(r)) + c(r)·d(y, S_norm(r))`

where `d(y,S)` is distance from `y` to the set (0 if inside).

Then define the overall score

`Score = κ·I + Σ_{r∈𝓡} w(r)·SS(r)`.

Notes:

- This is not claiming probabilistic “properness”; it’s a reasonable engineering score.
- It behaves sensibly under subnormality because sharpness uses `π_norm` shape, while `I` is priced separately.
- If you want to emphasize “core” plausibility, pick weights `w(r)` increasing in `r` and penalty scale `c(r)` increasing in `r`.

### 3B) Option 2: Coverage-calibrated PWIS (best for fair comparison to probability/quantile forecasts)

If you want fairness vs probabilistic forecasts, you really want cut-sets that correspond to **comparable empirical coverages**.

Recipe:

1) Work with normalized `π_norm` and define cut-sets `S_norm(r)` for `r ∈ (0,1]`.
2) On a calibration dataset, estimate the **coverage function**

`cov(r) = mean_t 1{ y_t ∈ S_norm,t(r) }`.

Because cut-sets shrink as `r` increases, `cov(r)` should decrease as `r` increases (roughly).

3) Choose target coverages `p ∈ {0.5, 0.8, 0.9}` (or whatever you’ll also use for probabilistic models).
4) For each `p`, find the cut level `r(p)` such that `cov(r(p)) ≈ p`.
5) Use the standard **interval score** at nominal miscoverage `α_prob = 1 - p` on the interval `S_norm(r(p))`.

Finally:

`WIS_like = κ·I + Σ_{p} v(p)·IS_{α_prob}( S_norm(r(p)), y )`.

This produces a score that is *structurally identical* to WIS for probabilistic central prediction intervals, so comparisons are much cleaner.

What you gain:

- interpretability (“this set is aiming for 80% coverage”)
- comparability to quantiles/ensembles
- a clear calibration diagnostic (the `cov(r)` curve)

### 3C) Option 3: Threshold event score using (necessity, possibility) as an interval forecast

For an event `A_T = {y ≥ T}`, and normalized `π_norm`:

- `u = Π_norm(A_T)` (“could exceed”)
- `l = N_norm(A_T) = 1 - Π_norm(A_T^c)` (“must exceed”)

This gives an interval `[l,u]` that you can read as:

> “the true exceedance probability is somewhere between `l` and `u`”

Then an undergrad-friendly “interval log score” is:

`S_T =  e·[-log(u+ε)] + (1-e)·[-log(1-l+ε)] + λ·(u-l) + κ·I`

where `e = 1{y ≥ T}`.

This matches the common imprecise-probability idea: if the event happens you get penalized for having too small an upper bound; if it doesn’t happen you get penalized for having too large a lower bound; width `(u-l)` penalizes vagueness.

### 3D) Option 4: Ordered-category possibilistic score (RPS-like, no continuous curve needed)

If Clyfar outputs category possibilities for ordered categories `1..K`, you can build *cumulative* upper/lower bounds (for “y ≤ k” events):

`U_k = Π_norm(y ≤ k) = max_{i≤k} π_norm(i)`

`L_k = N_norm(y ≤ k) = 1 - max_{i>k} π_norm(i)`

Observation indicator:

`O_k = 1{ y_obs ≤ k }`.

Now score how far the observation is from the interval `[L_k, U_k]` across all cutpoints:

`S = Σ_{k=1}^{K-1} dist(O_k, [L_k, U_k])^2 + λ·Σ_{k=1}^{K-1} (U_k - L_k) + κ·I`

where `dist(x,[a,b]) = 0` if `x∈[a,b]`, else distance to the nearer endpoint.

Why this is appealing:

- It’s the same spirit as the ranked probability score (RPS) but for bounds.
- It works directly on discrete categories (no need for continuous ozone grid).

### 3E) Option 5: Tail-risk ranking score (captures the “top few % extreme possibility” idea)

If the scientific value is partly “can the model flag rare-but-important days even when centroids are wrong?”, then **ranking** metrics are natural.

Example for a threshold `T` (like 70 ppb):

1) Define observed event `e_t = 1{y_t ≥ T}`.
2) Define a ranking score from Clyfar, such as `s_t = Π_norm,t(A_T)` (or `s_t = π_norm,t(extreme)`).
3) Evaluate how well `s_t` ranks the exceedance days:
   - ROC-AUC (general ranking skill), and/or
   - Precision–Recall AUC (better when exceedances are rare).

This avoids pretending `s_t` is a probability; it just asks: “do bigger possibility values correspond to more frequent events?”

Optional: assess whether `I_t` modifies usefulness:

- Compare AUC on all cases vs AUC restricted to “low-ignorance” cases (`I_t ≤ τ`).
- Or build a composite rank score like `s_t = (1-I_t)·Π_norm,t(A_T)` if you want “high risk *and* model confident”.

### 3E) Optional stretch: convert possibility → probability for “classic” scores (use with caution)

If you truly need a single comparable score like CRPS/log-score across everything, you can convert the possibilistic forecast to a probability distribution `p(z)` and then score `p` in the usual way.

But you must be honest: **this conversion injects assumptions** (it collapses second-order uncertainty).

Some possible conversions (in increasing “assumption strength”):

1) **Normalize-by-sum**: `p_i = π_i / Σ_j π_j` (simple, but not theoretically justified in general).
2) **Softmax**: `p_i ∝ exp(τ·π_i)` (tune τ; still an assumption).
3) **Max-entropy under constraints**: choose `p` that maximizes Shannon entropy subject to compatibility constraints implied by `π` (more principled, but heavier).

If you go this route, I’d strongly recommend reporting both:

- the classic probabilistic score on `p`, and
- an “ignorance / abstention” statistic like `I`.

## 4) “Information theory” in possibility space (what’s the analog of Shannon entropy?)

There isn’t one single universally agreed “possibility entropy” the way Shannon entropy is standard for probability.

But there *are* well-motivated uncertainty measures, usually split into:

1) **Nonspecificity** (how large is the plausible set?)  
2) **Fuzziness/ambiguity** (how graded is the membership/possibility?)

### 4.1 Undergrad-friendly nonspecificity (layer-cake / area view)

For normalized `π_norm` on a fixed domain of length `L`:

`NS_shape = (1/L) ∫ π_norm(z) dz`

Interpretation: average plausibility across the domain; smaller means more of the domain is being ruled out.

Equivalently (same number, different intuition):

`∫ π_norm(z) dz = ∫_0^1 |S_norm(r)| dr`

Interpretation: average size of the α-cut sets across strictness levels.

### 4.2 A simple “surprisal” idea that still makes sense

Even though `π(y)` is not a probability, the quantity

`surprise(y) = -log(π_norm(y) + ε)`

still behaves like “how incompatible was the observation with what the model thought was plausible”.

This can be a useful diagnostic term inside a larger score, as long as you don’t claim it is Shannon information.

## 5) Ten questions to clarify what you want (to guide the correction)

These are the questions that most affect what the “right” metric should be.

1) What exact forecast object are we scoring: per-member possibilistic outputs, an ensemble-aggregated possibility curve, or a single “scenario mean” possibility?
2) Do you want verification on the full continuous ozone curve `π(z)` (20–140 ppb grid in `summary-fuzzy-inference.md`), or only on the 4-category outputs (background/moderate/elevated/extreme)?
3) For the communication goal: is high ignorance `I` supposed to make users **more cautious** (risk-averse) or simply make them **less trusting** of the forecast?
4) Should `I` be penalized (operational usefulness) or can it be “good” if it happens exactly on hard/tipping-point days (epistemic honesty)?
5) Are your main verification questions about thresholds (e.g., `y≥70`), about category correctness, or about full-distribution shape?
6) If thresholds matter: which thresholds, and do you want one score per threshold or a pooled multi-threshold score?
7) Do you mostly want a *ranking* claim (“extreme possibility is top 2% on episode days”) or a *calibration/coverage* claim (“my 80%-like cut-set contains the truth ~80% of the time”)?
8) If you want fair comparison to probabilistic systems: what will competitors provide (ensembles, full CDFs, or a fixed set of quantiles)?
9) Are you willing to learn a mapping from possibility cut levels `r` → empirical coverage (enables a clean WIS-like comparison), and if so should that mapping be global, seasonal, or lead-time dependent?
10) Do you want a single scalar metric, or a small scorecard (e.g., tail-risk ranking + sharpness + ignorance/self-awareness) that matches the “second-order uncertainty” story?
