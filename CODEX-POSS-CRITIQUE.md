**Findings**
- Potential division by zero / undefined `α`. Both PWIS formulas use `(2/α)` but the docs don’t explicitly constrain `α` to `(0, m_t]`. If `𝒜` ever includes `0` or if you iterate beyond `m_t` for subnormal cases, you’ll hit invalid math or empty sets with undefined penalties. Consider a short note like “use `α∈(0, m_t]` and skip `α=0`”. `verif/POSS-SCORE-IDEAS-PLAIN.md:27-41`, `verif/POSS-SCORE-IDEAS-COMPLEX.md:24-35`
- Necessity under subnormality is ambiguous. You define `N_t(T) = 1 - sup_{z<T} π_t(z)` directly on subnormal `π_t`. That’s fine if you want “raw” necessity, but earlier Clyfar notes emphasize **conditional necessity** after normalization. Add one sentence to clarify which you intend so readers don’t mix the two. `verif/POSS-SCORE-IDEAS-PLAIN.md:10-17`, `verif/POSS-SCORE-IDEAS-COMPLEX.md:8-14`
- Category/binned PWIS uses `|S|/|Ω|` as a size proxy. If bins aren’t equal-width (or categories aren’t comparable), the “width” term won’t reflect actual ozone span. A quick note to “use equal-width bins or weight by bin width” would prevent misuse. `verif/POSS-SCORE-IDEAS-PLAIN.md:54-58`, `verif/POSS-SCORE-IDEAS-COMPLEX.md:41-45`

**Questions / assumptions**
- Are you okay explicitly stating `α` grid excludes 0 and is capped at `m_t`?
- Do you want to use raw `N_t` (subnormal) or “conditional” `N_c` after normalization?

Changes since last chat: two new docs added (`verif/POSS-SCORE-IDEAS-COMPLEX.md`, `verif/POSS-SCORE-IDEAS-PLAIN.md`), no code changes.

No tests run (docs-only change).
