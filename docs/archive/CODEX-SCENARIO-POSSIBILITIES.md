# Clyfar Scenario Visualisation – SOP

## 1. Purpose

Provide a repeatable way to:
- Generate example plots from Clyfar JSON outputs (quantities, probabilities, possibilities).
- Cluster ensemble members into a small number of scenarios.
- Produce LLM‑friendly summaries and public‑facing text.
- Inform future website UI/UX for risk communication.

---

## 2. Prerequisites

From repo root (`clyfar`):

- Conda env: `clyfar-2025` (or `clyfar-nov2025`) active.
- Local JSON exports under `data/json_tests/`, e.g.:
  - `forecast_percentile_scenarios_*_YYYYMMDD_HHMMZ.json`
  - `forecast_exceedance_probabilities_YYYYMMDD_HHMMZ.json`
  - `forecast_possibility_heatmap_*_YYYYMMDD_HHMMZ.json`
- Matplotlib cache dir set when running scripts:
  - `MPLCONFIGDIR=.mplconfig`

---

## 3. How to Run the Demo Scripts

All commands from repo root.

### 3.1 Quantities (ppb) – ensemble distribution

```bash
MPLCONFIGDIR=.mplconfig python scripts/demo_quantities.py YYYYMMDD_HHMMZ
# Example:
MPLCONFIGDIR=.mplconfig python scripts/demo_quantities.py 20251207_0000Z
```

Outputs → `data/json_tests/brainstorm_quantities/`:
- `boxplot_p50_<init>.png`
- `fan_p50_<init>.png`
- `hist_max_p90_<init>.png`

### 3.2 Probabilities – exceedance

```bash
MPLCONFIGDIR=.mplconfig python scripts/demo_probabilities.py YYYYMMDD_HHMMZ
```

Outputs → `data/json_tests/brainstorm_probabilities/`:
- `exceedance_lines_<init>.png`
- `exceedance_days_<init>.png`
- `exceedance_heatmap_<init>.png`

### 3.3 Scenarios from percentiles (ppb, p50/p90)

```bash
MPLCONFIGDIR=.mplconfig python scripts/demo_scenarios_clusters.py YYYYMMDD_HHMMZ
```

Outputs → `data/json_tests/brainstorm_scenarios/`:
- `scenario_<k>_union_<init>.png` – union p10–p90 envelope per scenario.
- `scenario_<k>_medoid_<member>_<init>.png` – p10/p50/p90 for representative member.
- CLI printout: scenario sizes and medoid member IDs.

### 3.4 Scenarios from possibilities (categories)

```bash
MPLCONFIGDIR=.mplconfig python scripts/demo_scenarios_possibility.py HHMMZ
# init is just HHMMZ fragment (e.g. 0000Z, 0600Z)
```

Outputs → `data/json_tests/brainstorm_scenarios_possibility/`:
- `scenario_<k>_mean_heatmap_<init>.png` – cluster‑mean category heatmap.
- `scenario_<k>_highrisk_<init>.png` – fraction of members with high `P(elevated+extreme)`.
- `scenario_membership_<init>.png` – fraction of members in each scenario.

### 3.5 Collecting a one‑folder summary (example: 00Z run)

```bash
mkdir -p data/json_tests/test_summary_00Z_pngs
cp data/json_tests/brainstorm_quantities/*0000Z*.png data/json_tests/test_summary_00Z_pngs || true
cp data/json_tests/brainstorm_probabilities/*0000Z*.png data/json_tests/test_summary_00Z_pngs || true
cp data/json_tests/brainstorm_scenarios/*0000Z*.png data/json_tests/test_summary_00Z_pngs || true
cp data/json_tests/brainstorm_scenarios_possibility/*0000Z*.png data/json_tests/test_summary_00Z_pngs || true
```

---

## 4. Plot Reference (What Each Figure Shows)

### 4.1 Quantities (ppb)

- `boxplot_p50_<init>.png`  
  - X: forecast days; Y: ozone in ppb.  
  - Box for each day summarises median (p50) across members.  
  - Good for: “how much spread between scenarios each day?”

- `fan_p50_<init>.png`  
  - X: days; Y: ozone p50.  
  - Shaded band: p10–p90 of p50 across members; line: ensemble median.  
  - Good for: “central tendency and uncertainty over time.”

- `hist_max_p90_<init>.png`  
  - Histogram of each member’s maximum p90 over the horizon.  
  - Good for: highlighting members that ever reach high ppb.

### 4.2 Probabilities (exceedance)

- `exceedance_lines_<init>.png`  
  - X: days; Y: probability; one line per threshold (e.g. >30, >50, >60, >75 ppb).  
  - Good for: public‑facing “chance of high ozone” story.

- `exceedance_days_<init>.png`  
  - Bars per threshold: number of days with p>0.2 and p>0.5.  
  - Good for: “how many days have meaningful risk?”

- `exceedance_heatmap_<init>.png`  
  - 2D grid: thresholds (rows) × days (columns), color = probability.  
  - Good for: quick scan of where risks cluster in time and severity.

### 4.3 Scenarios – percentiles (ppb)

From `demo_scenarios_clusters.py`:

- `scenario_<k>_union_<init>.png`  
  - X: days; Y: ozone ppb.  
  - Grey spaghetti: p50 of each member in scenario.  
  - Pink band: union p10–p90 across those members.  
  - Dark outline: max p90 (“scenario ceiling”), dashed line: median p50.  
  - Good for: “scenario envelope” plot.

- `scenario_<k>_medoid_<member>_<init>.png`  
  - Single member’s fan (p10, p50, p90) for that scenario.  
  - Good for: using real member as the example storyline.

### 4.4 Scenarios – possibilities (categories)

From `demo_scenarios_possibility.py`:

- `scenario_<k>_mean_heatmap_<init>.png`  
  - Category vs day; color = mean possibility (0–1) across members.  
  - Good for: “in this scenario, which days lean elevated/extreme?”

- `scenario_<k>_highrisk_<init>.png`  
  - X: days; Y: fraction of scenario members with `P(elevated+extreme) > 0.5`.  
  - Good for: “how many scenarios within this cluster are genuinely high‑risk?”

- `scenario_membership_<init>.png`  
  - Bar per scenario ID; height = fraction of members.  
  - Good for: “how common is each storyline?”

---

## 5. Prompting LLMs to Describe a Run

### 5.1 Minimal workflow

1. **Generate plots + have JSON ready**  
   - Run the four demo scripts for the init of interest.  
   - Note the JSON paths (`data/json_tests/*.json`) and the cluster summary printed by `demo_scenarios_clusters.py` and `demo_scenarios_possibility.py`.

2. **Give the LLM precise context pointers**  
   In your prompt, include:
   - Which init to use (e.g. `20251207_0000Z`).  
   - The directory with JSON (`data/json_tests`).  
   - The scenario summary from the script output (cluster sizes, medoid members).

3. **Ask for structured outputs**  
   Example prompt pattern:  
   > “Using the Clyfar JSON for init 20251207_0000Z in `data/json_tests` and the scenario clusters already computed (Scenario 1: 29/31, medoid clyfar000; Scenario 2: 1/31, medoid clyfar009; Scenario 3: 1/31, medoid clyfar007), write:  
   > 1) A 2–3 paragraph summary for the general public (plain language, no acronyms).  
   > 2) A bullet list for stakeholders (percent of members per scenario, key ppb ranges, which days are high‑risk).  
   > Focus on: (a) what most likely happens, (b) what rare high‑ozone paths look like, (c) how confident we are.”

4. **Constraints to mention in prompts**
   - “Avoid technical jargon; explain ppb and probabilities in everyday terms.”  
   - “Do not reference JSON filenames or code; talk only about days, ranges, and likelihood.”  
   - “Highlight that scenarios are ‘possible futures’ not guarantees.”

---

## 6. Path to Website Integration (Math → Risk → UI/UX)

### 6.1 From math to scenarios

- Inputs from Clyfar:
  - Quantities: p10/p50/p90 per member per day.
  - Probabilities: exceedance per threshold per day.
  - Possibilities: category possibilities per member per day.

- Scenario engine (backend):
  - Run clustering (like `demo_scenarios_clusters.py` and `demo_scenarios_possibility.py`) per forecast.
  - For each scenario:
    - Save: member list, medoid ID, p50/p90 envelope, mean possibilities, high‑risk fraction per day.
    - Derive: labels such as “Baseline low‑ozone”, “Less likely higher‑ozone”, “Rare extreme path”.

### 6.2 UI elements on BasinWx

- **Scenario cards (top‑level)**  
  - One card per scenario (max 3).
  - Fields:
    - Scenario name: “Most likely”, “Less likely but higher ozone”, “Rare extreme”.
    - % of members (e.g. “94% of model members”).
    - Short text summary (LLM‑generated).
    - Simple icon/badge indicating risk level (e.g. green / amber / red).
    - “View details” link.

- **Scenario detail view**
  - Main chart: medoid percentile fan (p10/p50/p90) for that scenario.
  - Secondary chart: cluster‑level high‑risk fraction over days.
  - Optional: small possibility heatmap showing typical category mix.
  - Text: 3–5 bullet points focusing on:
    - which days are “higher concern,”
    - how much higher than usual,
    - how likely the scenario is overall.

- **Ensemble overview**
  - Small “all scenarios” panel:
    - Pie or stacked bar: fraction of members in each scenario.
    - Simple sentence: “Most ensemble members keep ozone in the low range; a small fraction allow moderate or higher ozone later in the period.”

### 6.3 Risk communication principles

- Lead with:
  - “What is most likely” (Scenario 1).
  - “What could go wrong” (tail scenarios).
  - “How confident we are” (scenario percentages and exceedance probabilities).

- Avoid:
  - Raw member counts or technical acronyms on the public page.
  - Very detailed grid plots for the general audience; reserve for expert view.

- Provide:
  - Tooltips explaining ppb (“parts per billion”) and probability (“chance out of 100”).
  - Simple color coding (consistent with existing category colors).

---

## 7. Summary for Assistants

- Use the four demo scripts to generate a full “bundle” of figures per run.
- Use clustering outputs (cluster sizes + medoids) as the backbone of explanations.
- When prompting LLMs:
  - Point to the JSON and scenario summaries explicitly.
  - Request both public‑friendly text and stakeholder bullet lists.
- For the website:
  - Think in terms of 2–3 scenario cards with simple charts and clear percentages, not 31 individual members.
  - Let the detailed plots (heatmaps, spaghetti) live behind “advanced” links or expert tabs.

