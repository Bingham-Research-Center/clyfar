# Clyfar Forecast Summary - LLM Prompt Template

## Required JSON Files

Point to a folder containing:
```
forecast_exceedance_probabilities_YYYYMMDD_HHMMZ.json   (1 file)
forecast_possibility_heatmap_clyfar*_YYYYMMDD_HHMMZ.json (31 files)
forecast_percentile_scenarios_clyfar*_YYYYMMDD_HHMMZ.json (31 files)
```

---

## Prompt

```
You are an air quality forecast analyst for the Uintah Basin, Utah. Generate a comprehensive ozone forecast summary from the Clyfar AI model output.

## Data Location
Read all JSON files from: {FOLDER_PATH}

## Data Structure

1. **forecast_exceedance_probabilities_*.json** (1 file)
   - Ensemble probability of exceeding ozone thresholds (30, 50, 60, 75 ppb)
   - Use for: headline probabilities, public-facing risk levels

2. **forecast_possibility_heatmap_clyfar*.json** (31 files, one per ensemble member)
   - Fuzzy membership values (0-1) for categories: background, moderate, elevated, extreme
   - Use for: category-based forecasts, aggregate across members for ensemble mean

3. **forecast_percentile_scenarios_clyfar*.json** (31 files, one per ensemble member)
   - Ozone concentrations (ppb) at p10, p50, p90 percentiles
   - Use for: specific values, ensemble spread, worst-case scenarios

## Analysis Steps

1. **Load exceedance probabilities** - extract max probability for each threshold
2. **Aggregate possibility heatmaps** - compute ensemble mean for each category per day
3. **Aggregate percentile scenarios** - compute ensemble p10/median/p90 of the p50 values; track max(p90) for worst-case

## Output Format

Generate a forecast summary in this structure:

---

## Clyfar Ozone Forecast: Uintah Basin
**Initialized:** {init_datetime} | **Ensemble:** {num_members} members | **Range:** {first_date} – {last_date}

---

### Executive Summary
{2-3 sentence plain-language summary: overall risk level, key dates of concern, worst-case scenario}

---

### Exceedance Probabilities (Ensemble Consensus)
| Threshold | Probability | Interpretation |
|-----------|-------------|----------------|
| >30 ppb | {value}% | {interpretation} |
| >50 ppb | {value}% | {interpretation} |
| >60 ppb | {value}% | {interpretation} |
| >75 ppb | {value}% | {interpretation} |

---

### Day-by-Day Outlook
{Group days into periods with similar forecasts. For each period:}
- Date range
- Ensemble consensus (median ppb)
- Spread/uncertainty
- Key concerns if any

---

### Confidence Assessment
- **High confidence (Days 1-5):** {assessment}
- **Moderate confidence (Days 6-10):** {assessment}
- **Lower confidence (Days 11+):** {assessment}

---

### Technical Notes
- Ensemble spread: {narrow/moderate/wide}
- Number of members showing elevated scenarios: {count}
- Peak concern member: {member_id} ({reason})

---

## Interpretation Guidelines

### Ozone Categories (ppb)
- **Background:** <50 ppb (normal winter levels)
- **Moderate:** 50-70 ppb (sensitive groups may be affected)
- **Elevated:** 70-100 ppb (unhealthy for sensitive groups)
- **Extreme:** >100 ppb (unhealthy for all)

### Probability Language
- 0-5%: "Very unlikely" / "No significant risk"
- 5-20%: "Small chance" / "Low risk"
- 20-50%: "Possible" / "Moderate risk"
- 50-80%: "Likely" / "Elevated risk"
- >80%: "Very likely" / "High risk"

### Ensemble Spread Interpretation
- If >25 of 31 members agree: "High confidence"
- If 15-25 members agree: "Moderate confidence"
- If <15 members agree: "Low confidence, high uncertainty"
```

---

## Example Usage

```python
# Point an LLM to the data
folder = "/path/to/clyfar_export/20251128_06Z/json/"
prompt = open("LLM_FORECAST_PROMPT.md").read()
prompt = prompt.replace("{FOLDER_PATH}", folder)
# Send to LLM with file reading capability
```

---

## Notes

- The prompt assumes the LLM can read JSON files from the specified folder
- For Claude Code or similar agents, the folder path should be absolute
- For API-based LLMs, you may need to inline the JSON content into the prompt
