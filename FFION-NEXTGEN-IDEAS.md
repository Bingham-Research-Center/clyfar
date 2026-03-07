# FFION Nextgen Ideas

## Scope

- Reviewed the last 8 Ffion markdown outlooks only, not PDFs.
- Reviewed matching `CASE_*` data under `data/json_tests/`.
- Inspected current prompt plumbing and versioning.
- Paths reviewed:
- `data/json_tests/CASE_20260304_1200Z`
- `data/json_tests/CASE_20260304_1800Z`
- `data/json_tests/CASE_20260305_0000Z`
- `data/json_tests/CASE_20260305_0600Z`
- `data/json_tests/CASE_20260305_1200Z`
- `data/json_tests/CASE_20260305_1800Z`
- `data/json_tests/CASE_20260306_0000Z`
- `data/json_tests/CASE_20260306_0600Z`
- Prompt files inspected:
- `templates/llm/prompt_body.md`
- `scripts/demo_llm_forecast_template.py`
- `LLM-GENERATE.sh`
- `scripts/run_case_pipeline.py`
- `utils/versioning.py`

## Bottom Line

- The final alerts are conservative and mostly operationally safe.
- Days 1-10 prose is usually consistent with the CASE data.
- Days 11-15 prose is directionally right, but often over-interprets weak tail signals.
- The biggest problems are not formatting. They are semantics, confidence logic, reference drift, and prompt/context design.

## Highest-Priority Findings

1. Outdated standards language appeared inside the reviewed sequence.
   - `data/json_tests/CASE_20260306_0600Z/llm_text/LLM-OUTLOOK-20260306_0600Z.md` says `75 ppb NAAQS` and `75 ppb national standard`.
   - Current EPA ozone NAAQS is 70 ppb, retained in 2020.
   - Official EPA page: https://www.epa.gov/ground-level-ozone-pollution/ozone-national-ambient-air-quality-standards-naaqs
   - This is a real science/policy accuracy problem, not a style issue.

2. The outlooks blur three different meanings of “risk”.
   - Ensemble fraction: e.g. `1 of 31 members`.
   - Exceedance probability from `probs/forecast_exceedance_probabilities_*.json`.
   - Fuzzy possibility membership from `possibilities/forecast_possibility_heatmap_*.json`.
   - These are not interchangeable.
   - Some runs still say things like `roughly 3% probability` when the source fact is really `1 of 31 ensemble members`.

3. Confidence for Days 11-15 is too sticky.
   - All 8 runs kept `BACKGROUND/MEDIUM` for Days 11-15.
   - The underlying signal did not stay equally strong.
   - It ranged from 7/31 non-null members with 109 ppb peak p90 to 2/31 members with 65 ppb peak p90 and 0% 50/60/75 exceedance.
   - The prose notices these changes, but the confidence tier does not move with the evidence.

4. Prompt instructions ask for wider run-to-run analysis than the structured context actually supplies.
   - The prompt body says to compare patterns across `{{RECENT_CASE_COUNT}}` consecutive runs.
   - The renderer only injects structured summaries for 2 prior outlooks within 18 hours.
   - That gap encourages the model to improvise “trend” language unless it does extra file reads.

5. Previous-outlook extraction is brittle.
   - `scripts/extract_outlook_summary.py` only recovered expert-summary blocks for 3 of these 8 reviewed docs.
   - For the other 5, downstream prompt context degrades to alert/confidence only.
   - That weakens future comparison quality and encourages repetitive or shallow “consistent/oscillating” language.

6. Data freshness and prompt freshness are not enforced.
   - There is no explicit staleness gate on CASE age.
   - There is no separate prompt artifact version or prompt hash.
   - `llm_text/archive/` can grow quietly.
   - This is a repo-bloat and repo-rot risk.

## What The 8-Run Data Actually Shows

| Init | Ffion/Clyfar | Max D1-5 non-bg | D11-15 non-null | D11-15 peak p90 | 50ppb peak | 75ppb peak | Notes |
|---|---|---:|---:|---:|---:|---:|---|
| 20260304_1200Z | 1.1.1 / 1.0.2 | 0.103 | 7/31 | 109 ppb | 3% | 3% | fallback used; guard relaxed; peak `clyfar017` on 2026-03-18 |
| 20260304_1800Z | 1.1.1 / 1.0.2 | 0.074 | 7/31 | 107 ppb | 3% | 0% | fallback used; guard relaxed; peak `clyfar018` on 2026-03-18 |
| 20260305_0000Z | 1.1.1 / 1.0.2 | 0.205 | 1/31 | 81 ppb | 3% | 0% | peak `clyfar010` on 2026-03-16 |
| 20260305_0600Z | 1.1.1 / 1.0.2 | 0.180 | 5/31 | 109 ppb | 3% | 0% | peak `clyfar001` on 2026-03-18 |
| 20260305_1200Z | 1.1.1 / 1.0.2 | 0.010 | 6/31 | 108 ppb | 10% | 3% | fallback used; guard relaxed; peak `clyfar011` on 2026-03-18 |
| 20260305_1800Z | 1.1.2 / 1.0.3 | 0.000 | 4/31 | 103 ppb | 6% | 0% | peak `clyfar007` on 2026-03-17 |
| 20260306_0000Z | 1.1.2 / 1.0.3 | 0.000 | 2/31 | 107 ppb | 3% | 0% | peak `clyfar021` on 2026-03-17 |
| 20260306_0600Z | 1.1.2 / 1.0.4 | 0.000 | 2/31 | 65 ppb | 0% | 0% | peak `clyfar018` on 2026-03-17 |

### Sequence Read

- Days 1-5 had a weak March 7 signal through 20260305_1200Z, then effectively disappeared by 20260305_1800Z.
- Days 6-10 stayed clean in all 8 runs.
- Days 11-15 never became a broad, stable ensemble signal.
- Days 11-15 broadened on 20260305_1200Z, then contracted again.
- The last reviewed run, 20260306_0600Z, is materially weaker than the preceding strong-tail runs.
- The prose usually says this. The alert tier does not fully reflect it.

## Content Review

### Science

- The physical mechanism used in the text is mostly reasonable and usually matches the CASE weather files.
- The common explanation is: fresh snow, higher pressure, lighter winds, increasing March sun, then higher ozone potential.
- For the strong-tail members, those weather descriptions were generally supported by the matching `weather/forecast_gefs_weather_*.json` files.
- The problem is not that the model invents impossible physics every run.
- The problem is that it sometimes states policy or standards facts loosely or inconsistently.
- There are no real references in the markdown itself.
- `verify with official sources` is a disclaimer, not a citation practice.
- The 70 vs 75 ppb drift inside one 24-hour sequence shows that pinned reference facts should not be left to model recall.

### Assumptions

- Several assumptions are present but not clearly labeled.
- Assumption: `1 of 31 members` can be described as `3% probability`.
- Assumption: persistence of the same member across runs is a key convergence test.
- Assumption: a `30% of members` threshold would justify a stronger alert.
- Assumption: p90 values above 100 ppb in one member are worth repeated emphasis even when `50ppb` ensemble exceedance is only 0-10%.
- Assumption: if a tail scenario rotates member identity, it is “noise”.
- Some of these are useful operational heuristics.
- None of them are explicitly defined as house rules in the prompt.
- Because they are implicit, the model applies them unevenly.

### Logical Consistency

- Within each individual run, the reasoning is usually coherent.
- Across runs, the model sometimes narrates the sequence more strongly than the data supports.
- `20260305_1200Z` is the clearest example.
- That run says there is `strengthening ensemble support` for late-period ozone.
- Numerically that is true on breadth alone.
- But that same run also has `fallback_used: true`, `min_size_guard_relaxed: true`, wide spread, `50ppb` peak only 10%, and `75ppb` peak only 3%.
- The prose does mention those caveats later, but the headline language still leans too hard toward strengthening.
- `20260306_0600Z` is the opposite case.
- That run has the weakest Days 11-15 tail in the sequence: weighted non-background `0.006`, `50/60/75ppb` exceedance all `0%`, peak p90 only `65 ppb`.
- The text recognizes the weakening, but the alert confidence still stays at `MEDIUM`.
- That may be defensible.
- It is not well calibrated.

### Relation Of Each Run To The Others

- The sequence is not converging toward a strong basin-wide ozone event.
- It is sampling a recurring late-period tail regime that keeps changing breadth, date, and member identity.
- The most stable part of the sequence is not the tail.
- The most stable part is the absence of meaningful Days 6-10 risk.
- The near-term March 7 concern was real but weak, and it faded out cleanly.
- The late tail briefly broadened on 20260305_1200Z, then narrowed again.
- The final run in this reviewed set is qualitatively different from the higher-tail runs.
- The current alert template does not express that difference strongly enough.

## Markdown And Section Layout

- Major section order is stable across all 8 runs.
- That is good.
- The layout drift is smaller than the reasoning drift.
- The comparison section changes style across runs.
- Some runs lead with a table and short paragraph.
- Some earlier runs use more freeform comparison language.
- The Alert Level section is inconsistent.
- `20260304_1200Z` and `20260304_1800Z` use block-by-block rationale bullets.
- Later runs often use one paragraph after the code block.
- This matters because downstream parsing is already fragile.
- FAQ sections are readable, but they repeat generic questions too often.
- They should do more run-specific clarification and less recycled basin explainer text.
- Data Logger is useful, but it is not normalized enough for reliable downstream reuse.

## Where The Prose Matches The CASE Data Well

- Background dominance in Days 6-10 is correctly described in all 8 runs.
- The dissipation of the March 7 signal is correctly recognized by 20260305_1800Z onward.
- Strong single-member late tails around March 17-19 are usually tied to the right member files.
- Weather-driver paragraphs usually point to the right snow / pressure / wind combinations.
- The conservative final alert level of `BACKGROUND` is supported across the sequence.

## Where The Prose Is Weak Or Risky

- Standards language is not pinned and drifted to an outdated 75 ppb claim.
- Ensemble fraction is sometimes presented as calibrated probability.
- The `probs` file uses `percentile_used = ozone_50pc`, but the prose sometimes makes it sound like a direct event probability.
- p90 tail values are sometimes emphasized without equally explicit reminder that they are within-member upper tails, not ensemble medians.
- Some runs call the sequence “noise” without giving the actual stable metrics first.
- Some runs rely too much on member-identity rotation and not enough on block-level metrics.

## Current Prompt Plumbing

- Base prompt text lives in `templates/llm/prompt_body.md`.
- The current renderer is `scripts/demo_llm_forecast_template.py`.
- The wrapper that optionally re-renders and then calls the LLM is `LLM-GENERATE.sh`.
- The CASE pipeline entry point is `scripts/run_case_pipeline.py`.
- Current Ffion runtime version is resolved from `utils/versioning.py`.
- Rendered prompt output lands at `data/json_tests/CASE_.../llm_text/forecast_prompt_<INIT>.md`.

### What The Renderer Actually Adds

- Case metadata.
- JSON subfolder inventory.
- Figure inventory.
- Recent CASE list, currently up to 8.
- Previous outlook summaries, currently max 2 and max 18 hours old.
- Optional bias notes.
- Optional operator notes.
- Clustering diagnostics snapshot.
- Full clustering JSON.
- Then the prompt body from `templates/llm/prompt_body.md`.

### Current Weak Spots In That Setup

- The prompt body is editable, but there is no separate prompt artifact version.
- Prompt changes and workflow changes are both effectively hidden under the same Ffion runtime banner.
- The prompt asks for deeper run-to-run comparison than the injected structured context reliably supports.
- Full clustering JSON adds token mass and can distract from the smaller set of metrics that actually govern alert reasoning.
- Previous-outlook summaries depend on regex extraction from generated prose, which is brittle.

## Pipeline State After This Refactor

- Prompt-science now has a separate registry from runtime `FFION_VERSION`.
- Registry path: `templates/llm/science_registry.json`
- Active bundle manifest: `templates/llm/science/ffion_science_v1.0.0.json`
- Versioned prompt source: `templates/llm/versions/ffion_prompt_v1.0.0.md`
- Versioned bias caveats: `templates/llm/biases/ffion_biases_v1.0.0.json`
- Versioned optional QA notes: `templates/llm/qa/ffion_qa_v1.0.0.md`
- Python resolver: `utils/ffion_science.py`
- CLI resolver: `scripts/resolve_ffion_science.py`
- QA helper no longer stores editable science inline.
- `scripts/set_llm_qa.sh` now resolves a versioned QA file from the science bundle or accepts an explicit `--qa-file`.
- Reforecast selectors now exist in the pipeline.
- The renderer accepts `--science-version` and `--science-manifest`.
- `LLM-GENERATE.sh`, `scripts/run_llm_outlook.sh`, `scripts/run_case_pipeline.py`, `LOCAL-LLM-PROD.sh`, and `CHPC-LLM-PROD.sh` now pass that science selection through.
- This keeps runtime `FFION_VERSION` unchanged.
- That is the right choice.
- These are prompt-science changes, not a Ffion runtime-version bump.

### What Changed To Make Science Versionable

- The editable science surface is now explicitly file-based and nameable.
- A reforecast can pin a science version without pinning a new runtime Ffion version.
- The old shell-script QA text is now a versioned markdown file.
- The prompt renderer now records science bundle metadata in the rendered `forecast_prompt_*.md`.
- The prompt body now carries `Ffion Science v...` metadata into the generated outlook header.
- This gives a cleaner subjectivity trail for a tech report or side-by-side write-up.

### Bloat Control Added

- Added `scripts/prune_llm_case_artifacts.py`.
- It is dry-run by default.
- It targets old `llm_text/archive/` files, temp attempt files, optional old rendered prompt files, and the old generated `data/llm_qa_context.md`.
- This is disk-bloat control for generated artifacts, not source deletion.

## Best Prompt Versioning Model

- Keep `FFION_VERSION` for runtime/workflow identity.
- Add `FFION_PROMPT_VERSION` for prompt semantics.
- Store immutable prompt source files under a versioned directory.
- Example path: `templates/llm/versions/ffion_prompt_v1.2.0.md`
- Keep `templates/llm/prompt_body.md` as an active pointer or small wrapper, not the only canonical source.
- Add a prompt registry file.
- Example: `templates/llm/prompt_registry.json`
- Registry fields should include: prompt version, file path, sha256, status, effective date, owner, notes.
- Stamp prompt version and prompt hash into:
- `forecast_prompt_<INIT>.md`
- `LLM-OUTLOOK-<INIT>.md`
- validation output
- Add a short prompt changelog file.
- Example: `docs/ffion_prompt_changelog.md`
- Do not version generated prompts or generated outlook archives in git.
- Do version the prompt source, registry, tests, and changelog.

## Detailed Prompt Tweaks

1. Add an explicit semantics block.
   - Define ensemble fraction, exceedance probability, possibility membership, and percentile spread in plain terms.

2. Ban `3% probability` unless the source is an actual calibrated probability field.
   - Use `1 of 31 ensemble members` or `roughly 3% of ensemble members` instead.

3. Pin standards and policy facts in one small immutable fact block.
   - Include source and last-checked date.
   - Do not ask the model to recall NAAQS from memory.

4. Add a machine-readable evidence ledger ahead of prose.
   - For each block: non-null member count, max block non-background, peak `50ppb`, peak `75ppb`, peak member/date, peak p50/p90.

5. Make the model cite those ledger numbers in the comparison section.
   - Do not allow generic `strengthening` or `weakening` without at least two numeric deltas.

6. Add a hard rule for comparison language.
   - `Strengthening` requires at least two of: broader member support, higher weighted non-background, higher exceedance, more persistent peak date, cleaner diagnostics.
   - `Weakening` requires the reverse.
   - Otherwise use `mixed`.

7. Add a hard rule for confidence language.
   - If `fallback_used` or `min_size_guard_relaxed` is true, default one tier lower unless another metric clearly offsets it.

8. Add a hard rule for trace tails.
   - If Days 11-15 has `50ppb = 0%` and `weighted_non_background < 0.01`, describe the tail as `trace`, not `small but meaningful`.

9. Add a hard rule for p90 discussion.
   - If only a single member has high p90, mention it only in Expert Summary unless block exceedance is also non-trivial.

10. Distinguish p50 exceedance from p90 scenario discussion every time both are used.
    - Current text mixes them too easily.

11. Force the model to label operational heuristics as heuristics.
    - Example: member persistence across runs.
    - Example: percent of members needed for alert escalation.

12. Remove invented thresholds from freeform prose unless they are explicitly given in the prompt.
    - The `30% of members` trigger should either be formalized or removed.

13. Add a compact 8-run structured summary table to the prompt.
    - Do not ask the model to infer longer trends from only two prior summary stubs.

14. Keep previous-outlook context structured, not regex-derived from prose.
    - Prefer a sidecar JSON with block alerts, key metrics, and one short reasoning sentence per block.

15. Add a prompt instruction to prefer stable metrics over member identity.
    - Member identity is secondary.
    - Block metrics are primary.

16. Add a prompt instruction to separate public, stakeholder, and expert content more aggressively.
    - Public should not carry fine-grained tail detail unless it changes action.

17. Add a prompt instruction to put run-specific clarification into FAQ.
    - Less basin-climatology boilerplate.
    - More “why this run changed from 6 hours ago”.

18. Standardize the Alert Level section format.
    - One fixed code block.
    - One fixed rationale template.
    - One bullet or sentence per block.

19. Standardize the comparison section format.
    - Always a small table plus one short paragraph.

20. Add a prompt instruction to say when a block is unchanged because the evidence is unchanged.
    - Current text sometimes keeps the same alert while the evidence changed a lot.

21. Add a prompt instruction to say when the alert is unchanged for conservatism rather than because the signal is identical.

22. Add a prompt instruction to name the exact data source for probability claims.
    - Example: `member-median exceedance probability`.

23. Add a prompt instruction to avoid `actionable thresholds` language unless a threshold is actually defined in the prompt.

24. Add a prompt instruction to name uncertainty source.
    - Example: sparse tail support.
    - Example: cluster spread.
    - Example: member rotation.
    - Example: long lead time.

25. Add a prompt instruction to note version shifts.
    - If Ffion or Clyfar version changed since the previous run, acknowledge that in a small metadata note, not in the meteorology.

26. Reduce prompt bloat.
    - Replace full clustering JSON in-prompt with a compact structured summary and file path.
    - Let the model read the full JSON only if needed.

27. Add a freshness block.
    - Include init age, render time, CASE availability time, prompt version, and prompt hash.

28. Add a specific science-reference block.
    - One or two pinned facts are enough.
    - Do not let standards and known-bias facts float as free text.

29. Add explicit wording examples.
    - Good: `2 of 31 members show a late tail, but member-median exceedance stays at 0%.`
    - Bad: `There is a 6% probability of an ozone event.`

30. Add a prompt instruction to say when the public takeaway is simpler than the expert tail.
    - Example: `Operationally background, with a weak expert-only tail to monitor.`

31. Add a prompt instruction to separate `ensemble majority outcome` from `tail scenario outcome` in every full outlook.

32. Add a prompt instruction to name the target date shift.
    - Example: `peak shifted from March 18 to March 17 while shrinking in breadth`.

33. Add a prompt instruction to report when Days 1-5 signal fully disappears.
    - This sequence had that transition.
    - It should be more prominent.

34. Add a prompt instruction to make Data Logger machine-friendly.
    - Standard file list.
    - Standard previous-run list.
    - Optional counts.

35. Add a post-generation validator for semantic mistakes.
    - Check for `75 ppb NAAQS`.
    - Check for `3% probability` when the source claim is a single member.
    - Check for unsupported `strengthening` language when diagnostics are weak.

## Subjective Or Inconclusive Points

- Whether Days 11-15 should ever be upgraded above `BACKGROUND` when breadth reaches `6/31` but `50ppb` exceedance remains only `10%`.
- Whether p90 values above 100 ppb in one member belong outside the Expert Summary at all.
- Whether member-identity persistence is actually a useful operational signal or just a convenient narrative device.
- Whether public-facing markdown should mention national standards at all.
- Whether FAQ belongs in the same artifact as the expert outlook.
- Whether the full outlook is still too long for the actual information carried by weak-tail runs.

## Data Currency And Repo-Rot Controls

- Add a staleness validator before generation.
- Fail or warn if the latest CASE init is older than the expected cadence.
- Fail or warn if prompt version or prompt hash is missing.
- Add a small sidecar file per CASE.
- Example: `llm_text/outlook_metrics_<INIT>.json`
- Put the evidence ledger there so future comparison does not rely on regex over generated prose.
- Add retention rules for `llm_text/archive/`.
- Keep only recent attempts or compress older ones outside the repo working tree.
- Keep generated artifacts out of git.
- Commit only source prompt files, registry, changelog, tests, and small fixtures.
- Add a CI check that docs and banner versions do not drift from `utils/versioning.py` and the active prompt version.

## Permissions And Access That Would Help

- Approve repo-wide read scans and local JSON summarization.
- Approve browser access to official domains only when standards or science references need checking.
- Good domains: `epa.gov`, `weather.gov`, `noaa.gov`.
- Approve read access to operational logs if a second pass should compare prose to actual generation behavior.
- Useful paths:
- `~/logs/basinwx/`
- `~/basinwx-data/clyfar/basinwx_export/`
- Approve dry-run validation commands when needed.
- Good command: `./scripts/run_llm_outlook.sh <INIT> --check`
- If deeper reproduction is needed, use an isolated scratch clone and separate export root.
- Keep upload disabled unless explicitly intended.

## Questions For A Next Pass

1. Should the alert system stay conservative-first, or should it track the strongest plausible tail more aggressively?
2. Do you want national standards mentioned in public-facing Ffion text at all?
3. Should ensemble-member fraction ever be described as probability, or should that be banned completely?
4. Do you want a formal house rule for when `BACKGROUND/MEDIUM` becomes `BACKGROUND/HIGH` on weak late tails?
5. Do you want an 8-run structured comparison sidecar added to each CASE?
6. Should prompt versioning use semver, date-based tags, or hash-based registry keys?
7. Should generated markdown stay human-readable first, or should it become easier to parse downstream even if the prose gets slightly stiffer?
8. Should FAQ remain in the artifact, or move to a separate website-facing layer?
9. Should Ffion be allowed to mention p90 ozone above 100 ppb in Public Summary when ensemble exceedance remains near zero?
10. Should the comparison section be allowed to use words like `noise`, `converging`, or `strengthening` without a fixed numeric rubric?
