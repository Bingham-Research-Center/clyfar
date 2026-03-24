# Bridging possibility heatmaps and probabilistic forecasts (fair comparisons + info-gain ideas)

*Date written: 2026-01-22*  
*Audience: “first-year undergrad stats + operational forecasting”*  

This note responds to two needs:

1) You want to verify **Clyfar per-member possibilistic heatmaps** (4 category possibilities per day).  
2) You also want a way to compare “apples-to-apples” against **probabilistic** forecasts (e.g., an AQM lagged-weighted ensemble that outputs probabilities) using information-theory language like cross entropy / KL / information gain, and you want to include **observation uncertainty**.

The key idea is: **don’t force possibility to be probability.** Instead, compare models through *common objects* that both can produce:

- **Prediction sets** (“which categories are plausible?”)  
- **Probability bounds** for events (`[N, Π]` as an interval forecast)  

Both are natural in possibility theory, and both can be derived from probabilities too.

---

## 1) One-day objects (so we can compare models cleanly)

### 1.1 Possibilistic heatmap cell (per member, per day)

For one member `j` on one day `t`, Clyfar gives:

`π_raw,t,j(cat)` for `cat ∈ {bg, mod, elev, ext}`.

Define:

- `m = max_cat π_raw(cat)`  
- `I = 1 - m` (ignorance / “unsure”)  
- `π_norm = π_raw / m` if `m>0` (conditional shape)

### 1.2 Probabilistic forecast cell

A probabilistic model might give:

- a probability vector `p_t(cat)` over the same 4 categories, or
- a probability `p_t(E)` for an event like exceedance `E = {y≥70}`.

### 1.3 Observation as a category (same bins as forecast)

You said you want the same bins for observation and forecast. The cleanest “binning” rule is:

1) Use the same 4 output membership functions used by the forecast categories.
2) Compute the 4 memberships at the observed ozone value `y`.
3) Set the observed category to `ω_obs = argmax`.

This gives a crisp label while staying consistent with the fuzzy category definitions.

---

## 2) Observation uncertainty: how to include it in a proper way

Even if you publish a crisp observed category, the true ozone value has error (instrument + representativeness).

The standard way to include this in scoring is to replace “hard truth” with a **soft truth distribution** `q`.

### 2.1 Soft truth over categories

Assume the latent true ozone `Y_true` is uncertain given the observed `y_obs`.

Example model:

`Y_true | y_obs  ~ Normal(y_obs, σ_obs^2)`

Then define a probability for each category:

`q(cat) = P( Y_true ∈ bin(cat) | y_obs )`.

If you don’t want hard bins, you can also use membership functions:

`q(cat) = E[ μ_cat(Y_true) | y_obs ]`  (expected membership).

Either way, `q` is a probability vector on the 4 categories, and it encodes observation uncertainty.

### 2.2 Cross entropy with observation uncertainty (probabilistic forecasts)

If a probabilistic forecast gives `p(cat)`, the natural proper score is cross entropy:

`CE(q,p) = - Σ_cat q(cat) log p(cat)`.

Special case:

- If `q` is one-hot (no obs uncertainty), `CE` becomes the usual **log score / ignorance**: `-log p(ω_obs)`.

Interpretation (plain language):

> Cross entropy is the average “surprise”. Lower is better. If you predict high probability where the truth (or soft truth) is concentrated, you get low surprise.

### 2.3 Deterministic forecasts with observation uncertainty

If a deterministic model predicts a scalar `x̂` (ppb), and you assume `Y_true|y_obs` is Normal as above:

- Expected squared error:
  `E[(x̂ - Y_true)^2 | y_obs] = (x̂ - y_obs)^2 + σ_obs^2` (if unbiased).

So you can score deterministically while being honest about obs noise.

---

## 3) Two “common objects” for fair comparison: sets and bounds

### 3.1 Prediction sets (category sets)

**Possibility → set:** for strictness `r∈(0,1]`,

`S_poss(r) = {cat : π_norm(cat) ≥ r}`.

**Probability → set:** for target coverage `p0` (like 0.8),

`S_prob(p0)` = smallest set of categories whose probabilities sum to ≥ `p0`.

Now both models output a category set, and you can compare them using the same metrics:

- calibration/coverage: how often the observation is inside the set
- sharpness: typical set size or width

This is the cleanest “apples-to-apples” route for the heatmaps.

### 3.2 Probability bounds for events (interval forecasts)

Possibility theory gives bounds on probability:

`N(A) ≤ P(A) ≤ Π(A)`.

For a category event `A` (like `A = {elev, ext}`), compute from `π_norm`:

- `Π(A) = max_{cat∈A} π_norm(cat)`
- `N(A) = 1 - max_{cat∉A} π_norm(cat)`

Then Clyfar produces a **probability interval** `[N(A), Π(A)]`.

For a probabilistic model that outputs `p(A)`, that’s the special case `[p(A), p(A)]` (zero-width interval).

So: both models can be compared on the same “object type”: a probability interval for the same event.

---

## 4) How to use cross entropy / KL / information gain (probabilistic side)

### 4.1 From cross entropy to KL (why “information gain” language fits)

For a fixed true distribution `q` and forecast `p`:

`CE(q,p) = H(q) + KL(q || p)`

where:

- `H(q)` is the entropy of truth (irreducible uncertainty)
- `KL(q||p)` is the extra “penalty” for mismatch (always ≥ 0)

In practice you don’t know the exact `q`, but empirically you can still use:

- mean cross entropy vs lead time
- improvement over climatology = an “information gain”-style number:

`IG = CE(q, p_clim) - CE(q, p_model)`

Interpretation:

> IG is how many “nats” (or bits if you use log base 2) you save versus climatology.

### 4.2 Decomposition (Brier-like intuition)

The Brier score has a famous reliability–resolution–uncertainty decomposition.

The log score also has decompositions into “calibration (reliability)” and “sharpness/resolution” terms, but they’re a bit more technical.

Undergrad-friendly way to keep the same *spirit*:

- Make reliability diagrams (calibration plots).
- Report sharpness (spread of predicted probabilities).
- Report mean log score / cross entropy.

That gives you the same three-part story even if you don’t write the full algebraic decomposition.

---

## 5) What “information gain” could mean on the possibilistic side (without lying)

Possibility isn’t additive, so Shannon-style entropy isn’t canonical.

But you can still talk about “information” in two honest ways:

### 5.1 Specificity / nonspecificity (how much the forecast narrows the world)

If the forecast often outputs small plausible sets `S_poss(r)`, it is “more informative” in the everyday sense: fewer categories remain plausible.

A simple “Hartley-style” information measure for one set is:

`Info(S) = log(4 / |S|)`  (0 if S is all 4 categories; larger if S is 1–2 categories)

You can average this across days and strictness levels.

This measures **sharpness/specificity**, not correctness.

### 5.2 Compatibility surprisal (how contradictory was the outcome?)

Define:

`Surp = -log(π_norm(ω_obs) + ε)`

This behaves like a “surprise” number (big when the observation was low-possibility), but you should label it as **compatibility surprisal**, not a probabilistic log score.

### 5.3 Interval calibration as the key “probability-like” promise

If you use the probability-bounds view `[N(A), Π(A)]`, you can directly test:

For an event `A`:

- empirical frequency should not exceed the upper bound “too often”
- empirical frequency should not go below the lower bound “too often”

In symbols (over many cases with similar forecasts):

`N(A) ≤ freq(A) ≤ Π(A)`.

That’s the most “probability-like” and scientifically honest calibration test for possibilistic outputs.

It also compares cleanly to probabilistic forecasts, because for a probability forecast `[p,p]` the condition reduces to `freq(A) ≈ p` (standard calibration).

---

## 6) Practical recipe for your setup (per-member now, clusters later)

### 6.1 Per-member heatmap verification (now)

For each member `j`:

1) Compute `π_raw,t,j` and derived `π_norm,t,j`, `I_t,j`.
2) Compute observed category `ω_obs,t` (same bins).
3) Report:
   - coverage + sharpness curves for `S_poss(r)` across `r` values
   - exceedance ranking metrics using `Π({elev,ext})` as a proxy (or use continuous `Π(y≥70)` if available)
   - ignorance diagnostics (histograms + abstention curves)
4) Aggregate across members using:
   - mean score over members, and
   - distribution of member scores (median/IQR).

### 6.2 Scenario clusters (later)

After clustering:

- Score each member anyway (cheap), then summarize by cluster:
  - within-cluster mean score
  - medoid score (what users see)
  - cluster weight `w_c`

This gives you a defensible statement like:

> “Scenario 1 (85% of members) is well-calibrated and sharp; Scenario 2 (10%) captures rare high-ozone possibilities; Scenario 3 (5%) is high-ignorance and should be treated cautiously.”

---

## 7) One concrete “fair comparison” table you can publish

If you have Clyfar possibility heatmaps and an AQM probability forecast, a clean comparison table is:

1) **Category-set calibration** (coverage vs set size)  
   - Clyfar: `S_poss(r)`  
   - AQM: `S_prob(p0)`

2) **Exceedance bounds calibration** for `A={y≥70}`  
   - Clyfar: interval `[N(A), Π(A)]`  
   - AQM: point `p(A)` (interval `[p,p]`)

3) **Ignorance / abstention**  
   - Clyfar: `I` (subnormality)  
   - AQM: spread proxy (if ensemble-based), or forecast entropy

4) **Information gain vs climatology** (probabilistic only, unless you choose a transformation)  
   - AQM: `IG = CE(q,p_clim) - CE(q,p_aqm)`
   - Clyfar: report sharpness gain + surprisal diagnostics instead, unless you explicitly transform π→p.

---

## 8) If you absolutely want a single cross-entropy number for Clyfar (optional, assumption-heavy)

If you truly want “bits” for Clyfar too, you must map possibility → probability.

One principled option (from evidence theory) is the **pignistic transform** for a consonant belief function induced by `π_norm`. It produces a probability vector `p_bet` that is compatible with the nested-sets interpretation.

Then you can compute cross entropy `CE(q, p_bet)` and compare directly to AQM.

But: this injects a modeling assumption (how you resolve second-order uncertainty into first-order probability). If you publish this, be explicit that it is a *derived* probability.

