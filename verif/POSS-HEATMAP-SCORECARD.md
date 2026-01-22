# Possibilistic verification scorecard for Clyfar heatmaps (4 categories × ~15 days)

*Date written: 2026-01-22*  
*Context docs used:*  
- `../brc-knowledge/scholarium/active-projects/clyfar/summary-clyfar-prototype.md`  
- `../brc-knowledge/scholarium/active-projects/clyfar/summary-fuzzy-inference.md`  
- `../brc-knowledge/scholarium/active-projects/clyfar/summary-possibility-theory.md`  
- `../brc-knowledge/scholarium/active-projects/clyfar/summary-poss-subnormal.md`  

This note is a “churn” on your answers: it proposes a practical **scorecard** for the *heatmap product* (possibility-by-category over lead days), and shows how to compare it fairly to probabilistic (ensemble) and deterministic forecasts without pretending possibility is probability.

## 1) What we are scoring (forecast object)

You said the primary unit is **per-member heatmaps** (31 members), with a long-run plan to cluster members into 1–3 “scenario clusters” and use the **medoid** member as a representative.

So for verification, it helps to be explicit about indices:

- `t` = valid day (or valid day × lead time; choose one convention and stick to it)
- `j` = ensemble member index, `j=1,…,31`

For each verification case `(t,j)` (one day at one lead time for one member):

- Forecast: 4 category possibilities  
  `π_raw = (π_bg, π_mod, π_elev, π_ext)`, each in `[0,1]`.
  - These are **possibilities/compatibilities**, not probabilities; they do not need to sum to 1.
  - They may be **subnormal**: `max(π_raw) < 1`.

- Observation: daily max ozone value `y` (ppb), and/or an observed category label derived from `y`.

The “heatmap” is just stacking these vectors over lead days for each member.

### 1.1) How to aggregate scores across members (two good defaults)

Because the observation happens once, but you have 31 member-forecasts, you’ll usually want:

1) **Member-average score** (expected score if you treat each member as one plausible scenario):

`Score_t = (1/31) Σ_j Score_{t,j}`

2) **Distribution of member scores** (to show spread across members):

Report median, IQR, and worst decile of `{Score_{t,j}}`.

Both are useful: the mean answers “typical member performance”; the distribution answers “how inconsistent are members?”

### 1.2) How to evaluate clustered scenarios (when you start publishing clusters)

If you cluster the 31 members into clusters `c=1,…,C` (with `C∈{1,2,3}`), sizes `n_c`, and medoids `j*(c)`:

- **Scenario weights:** `w_c = n_c/31` (ensemble frequency)
- **Scenario forecast:** use the medoid’s heatmap (or cluster-mean heatmap if you want smoother displays)

Then you can report (at least) two scenario-level verification views:

1) **Medoid-as-scenario verification:** `Score_c = mean_t Score_{t, j*(c)}` with weights `w_c`.
2) **Within-cluster verification:** average over members inside each cluster:
   `Score_c = mean_t (1/n_c) Σ_{j∈cluster c} Score_{t,j}`.

The second is more statistically stable; the first matches what a user sees if you truly only present the medoid.

## 2) The tripartite decomposition that matches the project narrative

Your summaries emphasize: *possibility for risk bounds* + *explicit ignorance* + *conditional necessity when you normalize*.

For each day:

1) **Ignorance / “unsure” amount**

`m = max(π_raw)`  
`I = 1 - m`

Interpretation: if no category is strongly supported by the rules, `m` is small and `I` is large.

2) **Normalized shape (conditional on what the model “knows”)**

If `m>0`, define

`π_norm = π_raw / m`  so `max(π_norm)=1`.

Interpretation: `π_norm` is the *relative preference* over categories given the evidence the rulebase can process; `I` is what’s missing.

3) **Conditional necessity for events**

Necessity behaves sensibly only after normalization.

For any event `A` (like “extreme”, or “elevated-or-extreme”):

- `Π(A) = max_{cat∈A} π_norm(cat)`  
- `N(A) = 1 - max_{cat∉A} π_norm(cat)`

Interpretation: `Π(A)` = “could happen?” and `N(A)` = “basically unavoidable, *given what the model knows*”.

## 3) Observations are fuzzy too: two options (crisp vs fuzzy truth)

Because your output categories overlap (by design), the observation has some ambiguity near boundaries.

### Option A (simplest): crisp observed category

Map `y` to a single category `ω_obs ∈ {bg, mod, elev, ext}`. Two common choices:

- Threshold-based binning (easy to explain to stakeholders).
- Max-membership rule: compute the membership degree of `y` in each output fuzzy set and take `argmax`.

You said you want “the same bins for the observation as for the forecast”. The cleanest way to do that (without inventing new thresholds) is:

> Use the **same output membership functions** the model uses, compute the 4 memberships at the observed `y`, and set `ω_obs = argmax`.

That makes the observation’s “binning” consistent with the model’s category definitions.

### Option B (more faithful): fuzzy observed category vector

Compute observation memberships

`μ_obs = (μ_bg(y), μ_mod(y), μ_elev(y), μ_ext(y))`

from the **same** output membership functions the FIS uses.

Interpretation: on a boundary day, you might have e.g. `μ_mod(y)=0.6`, `μ_elev(y)=0.4` instead of forcing a hard label.

This helps avoid “verification artifacts” where the score jumps just because `y` crosses a bin edge.

## 4) Scorecard: 5 things that answer 5 different questions

You said you like “independent, multifaceted scores that must be read together”. Good: it matches the underlying science (risk bounds + epistemic humility).

I’d recommend tracking these 5 blocks (per lead time and pooled):

### 4.1 Calibration of *plausible sets* (a possibilistic reliability idea)

Pick a few strictness levels `r ∈ (0,1]` (example: `r = 0.5, 0.7, 0.9`).

Define the forecast’s **plausible set of categories** at strictness `r`:

`S(r) = {cat : π_norm(cat) ≥ r}`.

Then compute **coverage**:

- Crisp truth: `cover(r) = mean 1{ω_obs ∈ S(r)}`
- Fuzzy truth: `cover(r) = mean Σ_{cat∈S(r)} μ_obs(cat)`

Interpretation to a reader:

> “At strictness 0.7 (keeping only categories the model thinks are strongly plausible), the observation is still inside the plausible set X% of the time.”

This is the closest analogue to probabilistic calibration for this heatmap product.

### 4.2 Sharpness (how specific the forecast is)

The calibration metric can be gamed by always including all 4 categories. So we also measure “how big” the plausible set is.

For 4 ordered categories, two easy sharpness measures:

- **Set size:** `sharp_size(r) = mean |S(r)| / 4`
- **Set width (uses ordering):**  
  `sharp_width(r) = mean (max_index(S(r)) - min_index(S(r))) / 3`

Interpretation:

> “At strictness 0.7, the model typically narrows to ~1–2 categories” (sharp)  
> vs “it usually keeps 3–4 categories” (less specific).

### 4.3 A single combined set score (optional; if you really want one number)

If you want a one-number score that balances calibration and sharpness, use a **set score** per `r`:

`Score_t(r) = width(S_t(r)) + β·1{ω_obs,t ∉ S_t(r)}`

and average over `t` and over a grid of `r` values.

Notes:

- This is like “interval scores” but for category-sets.
- Choosing `β` is partly a value judgement; if you don’t want to choose, just report calibration + sharpness separately.

### 4.4 Tail-risk ranking for 70 ppb (your NAAQS-focused need)

For the exceedance event `E = {y ≥ 70}`, you can form a **risk score** from the heatmap in a few ways.

If you only have categories, a simple proxy is:

`s = max(π_norm(elev), π_norm(ext))`  (event possibility via union = max)

Then evaluate how well `s` ranks exceedance days using:

- ROC-AUC (general ranking skill)
- PR-AUC (better when exceedances are rare)

Interpretation:

> “On days when the model assigns higher ‘could-be-high-ozone’ possibility, exceedances happen more often.”

This directly matches the “top few % extreme possibility” insight from `summary-clyfar-prototype.md`.

If you do have the **continuous aggregated activation curve** `π_norm(z)` available, do the cleaner version:

`s = Π_norm(y≥70) = sup_{z≥70} π_norm(z)`

### 4.5 Ignorance / self-awareness (keep it open-ended, as you requested)

You explicitly want to keep open whether high ignorance is “good” or “bad” (like ensemble spread).

So don’t bake it into the main loss yet; **diagnose it**.

Two very interpretable checks:

1) **Ignorance vs error:** does higher `I` correlate with worse forecast outcomes?
   - Outcome could be category miss, or exceedance miss, or absolute ppb error from a defuzzified point.

2) **Abstention curve (like selective prediction):**
   - Sort cases by `I` (most ignorant first).
   - For a threshold `τ`, “abstain” on cases with `I>τ` and compute skill on the remaining cases.
   - Plot: performance vs fraction of cases kept.

Interpretation:

> “When Clyfar says ‘I’m unsure’, it really is the hard regime.”

This lets you tell a coherent story without deciding in advance whether to penalize `I`.

## 5) What you meant by “learn r → coverage” (plain language)

You asked what I meant by calibrating cut levels.

In probability forecasts, a “90% interval” has a built-in meaning: it should contain the truth about 90% of the time (if calibrated).

In possibility forecasts, the cut level `r=0.7` does **not** automatically mean “70% coverage”. It is just a **strictness knob**: higher `r` keeps only more-plausible categories.

So we can *learn* what strictness levels correspond to what coverages, by counting in historical data:

1) Pick a strictness `r` (say 0.7).
2) For each day, compute the plausible set `S_t(0.7)`.
3) Count how often the observation is inside it.
4) That fraction is the empirical coverage of `r=0.7`.

Do that for many `r` values, and you get a curve:

`r  ↦  coverage(r)`.

Then you can say things like:

> “In this basin/season, keeping categories with normalized possibility ≥ 0.7 produces a set that covers the truth about 80% of the time.”

Why this helps comparison:

If you want to compare against a probabilistic model’s “80% prediction set”, you can compare it against the possibilistic cut level `r` that empirically gives ~80% coverage.

## 6) Fair comparison to probabilistic and deterministic forecasts (without forcing equivalence)

### 6.1 Compare via *prediction sets* (best apples-to-apples across possibilities vs probabilities)

For a probabilistic model that outputs category probabilities `p(cat)`:

- Build a “top‑p prediction set” by including the most likely categories until the total probability is ≥ `p` (like a “credible set”).
- Score that set with the **same calibration + sharpness** machinery as above.

This avoids pretending that possibility levels are probabilities; you compare what both methods *actually communicate*: sets of plausible categories.

### 6.2 Compare exceedance forecasting via “precise vs imprecise probabilities”

For exceedance at 70 ppb:

- A probabilistic model gives one number `p = P(y≥70)`.
- Clyfar gives a **range** `[N(E), Π(E)]` (conditional on knowns), plus `I`.

You can use an “interval forecast” score where a precise probability is just a special case:

- AQM: interval `[p,p]` (width 0)
- Clyfar: interval `[N,Π]` (width ≥ 0)

Then a single scoring formula can cover both, while still allowing Clyfar to express imprecision.

### 6.3 Deterministic comparison (CSI/POD/FAR)

If you want classic categorical verification for exceedance:

- Deterministic AQM thresholding gives hits/misses and CSI/POD/FAR.
- For Clyfar, you have to choose an operational rule like “forecast exceedance if Π(E) ≥ θ”.

Then you can sweep `θ` and get a curve (ROC-like) rather than one arbitrary point.

### 6.4 Cross-entropy / information-gain framing (what carries over cleanly)

You said you like probability scores based on **cross entropy** / **log score** (and decompositions like KL / information gain).

Two important “carry-overs”:

1) **For probabilistic forecasts**, cross entropy is the right tool:
   - If your forecast is category probabilities `p(cat)`, and the observed category is `ω_obs`,
     the multiclass log score is `LS = -log p(ω_obs)`.
   - If you include observation uncertainty, replace the one-hot truth with a soft truth vector `q`
     and use cross entropy: `CE(q,p) = -Σ_cat q(cat) log p(cat)`.

2) **For possibilistic forecasts**, you can get *information-gain-like* ideas without calling them Shannon:
   - The “compatibility surprisal” `-log(π_norm(ω_obs)+ε)` behaves like “how incompatible was reality with what the member thought plausible”.
   - The sharpness of plausible sets `S(r)` is like “how many categories are still on the table”.

If you need a single “fair” comparison number across probability vs possibility, prefer the **prediction-set route** in §6.1 (same object type: sets), or an exceedance interval route in §6.2 (same object type: probability interval).

## 7) A recommended “minimal publishable” verification bundle

If you want something that is simple, interpretable, and consistent with the project thesis, I’d start with:

1) **Calibration curve:** `cover(r)` vs `r` (per lead day group: days 1–5, 6–10, 11–15).
2) **Sharpness curve:** `sharp_width(r)` vs `r` on the same axes.
3) **Ignorance diagnostics:** histogram of `I`, and an abstention curve.
4) **Tail-risk ranking:** PR-AUC for `y≥70` using `s = Π_norm(y≥70)` (or the category proxy).

Plus: compare all of these to a climatology baseline and (if available) to AQM.

---

## 8) What I still need from you to “lock in” a final scorecard

Given your answers, the remaining practical details are:

1) For observed categories, do you want **threshold binning** or the **argmax-membership binning** (recommended) described in §3?
2) When you start verifying scenario clusters, do you want “score the medoids” (matches what users see) or “score all members within each cluster” (more stable)?

Once those are chosen, the next concrete step is: pick a small `r` grid (e.g. `r∈{0.5,0.7,0.9}`) and decide whether to report:

- calibration + sharpness as two curves (my preference), or
- a single combined set score with a chosen miss penalty.
