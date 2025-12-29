# Prompt for the language model

Use American English, U.S. units (°F, mph, feet), and a confident but neutral tone.
The CASE metadata above already advertises every JSON + figure path.
Treat that table—and the previous init list—as part of the prompt context.

```text
You are explaining a Clyfar ozone outlook for the Uintah Basin.
The forecast init is {{INIT}} and the CASE directory on disk is {{CASE_ROOT}}.

You must weave in run-to-run consistency using the metadata table above. Also known as "dRisk/dt", talk about how both GEFS and Clyfar change every six hours over the last available runs for the same valid time of interest (e.g., discuss a trend towards higher snow values on a current Day 10 that has been consistent for many forecasts).

If the table lists previous cases, compare patterns between {{RECENT_CASE_COUNT}} consecutive runs.
Call out whether the current run matches, strengthens, or weakens earlier signals.

Data sources (all derived from GEFS-driven time series that Clyfar processes):
1) Quantities/percentiles: per-member GEFS time series (p10/p50/p90) for ozone (ppb) → use for trends and scenario ranges.
2) Exceedance probabilities: ensemble consensus probabilities for >30, >50, >60, >75 ppb thresholds.
3) Possibility-based category heatmaps: Dubois-Prade memberships (background/moderate/elevated/extreme) as Clyfar uses at its core, plus clustering diagnostics pre-computed.
4) Figures folder: GEFS time-series plots, probability bars/heatmaps, and scenario visualisations. Only use these if useful, as the data files should be enough.

If a Q&A block was provided earlier, treat its guidance as high priority.
Repeat any warnings from that block in every section you write.

### Task 1 – Three 5-day summaries at three complexity levels

For each block (Days 1–5, Days 6–10, Days 11–15), write:
a) A 3-sentence summary for the general public (field workers, residents).
b) A 3-sentence summary for mid-tier stakeholders (policy, general scientists, industry).
c) A 3-sentence summary for experts (forecasters, ozone specialists).

Guidance:
- Keep all text concise and concrete; avoid repetition across levels.
- Tie your language to the GEFS and/or Clyfar percentile time series (e.g., “median near 45 ppb, 90th percentile spikes to 70 ppb”).
- Flag run-to-run consistency when notable (e.g., “third straight run with elevated tails on Sat/Sun”).
- Refer to scenarios qualitatively (“most GEFS members”, “a small minority of runs”).

### Verboten Word List
For all issued discussion instead of this terminology, prefer another format:
- "p10" --> 10th percentile (and similar)

### Task 2 – Full-length (~1 page) outlook

Write a cohesive outlook (~1 printed page) that:
- Summarises the overall pattern across Days 1–15.
- Explains the scenario logic: dominant clusters vs tail/high-ozone clusters, in plain terms.
- Quantifies accessible daily max ozone ranges at key sites using ppb values from the GEFS percentiles.
- Notes run-to-run consistency/shifts compared with recent runs (use the case list above for evidence).
- Highlights GEFS time-series cues (e.g., synoptic-scale dips/spikes, weekend build-ups).
- Ends with what to monitor in subsequent runs and when the next update arrives.

### Task 3 – Alert level for the website

Using all evidence above, assign a single alert level for the full forecast period that fits the Clyfar outlook synthesised with uncertainty identified in Clyfar and GEFS data:

#### Magnitude, matching Clyfar fuzzy categories sets
- BACKGROUND – low ozone, no meaningful high-ozone risk expected.
- MODERATE – some chance of higher ozone on a few days, but not strongly signaled.
- ELEVATED – strong signal for one or more high-ozone days.
- EXTREME – persistent or widespread high-ozone conditions likely.

#### Confidence
- LOW: High spread in ensemble or known biases not yet corrected
- MEDIUM: Moderate ensemble agreement, typical uncertainty for lead time
- HIGH: Strong run-to-run consistency (dRisk/dt) and ensemble agreement

Output this final two lines in a machine-readable form *at the very end* of your response:

```
AlertLevel: BACKGROUND | MODERATE | ELEVATED | EXTREME
Confidence: LOW | MEDIUM | HIGH
```

### Output formatting

1) Three sections for Days 1–5, 6–10, 11–15 (public, stakeholder, expert paragraphs inside each section).
2) One “Full Outlook” section (~1 page).
3) The single alert level line described above.
```

## Notes for the forecaster / operator

- Edit this template (`templates/llm/prompt_body.md`) if you need to emphasise different language or steps.
- Add site-specific highlights manually before sending to your LLM CLI when needed.
- GEFS percentile and probability figures already live under `CASE_<init>/figs/`; link to them in stakeholder/expert text when useful.
- Do caveat where relevant that these forecasts (a) are subject to appropriate error for the lead time via dynamic error growth (or simpler language); (b) are uncertain due to Clyfar's experimental nature; (c) entire AI--human system still being tested for reliability on rare events like this (if during a rare event!).

## Final note/disclaimer for occasional uncertain runs/errors
Discretely let the developer/user know at the bottom of a later section that access to some files needed to fulfill objectively of this prompt were not found (e.g., I made a mistake typing this prompt) or absent (data corruption, etc.) as a form of internal data logger.
----

