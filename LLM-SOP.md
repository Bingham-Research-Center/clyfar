# LLM Forecast SOP

## Quick Start (Ad-hoc)

```bash
# On CHPC interactive node
salloc -n 4 -A notchpeak-shared-short -p notchpeak-shared-short -t 1:00:00
source ~/software/pkg/miniforge3/etc/profile.d/conda.sh && conda activate clyfar-nov2025
cd ~/gits/clyfar

# REQUIRED: Use default CLI path
unset LLM_CLI_COMMAND LLM_CLI_BIN LLM_CLI_ARGS

# Generate (YYYYMMDDHH format)
./LLM-GENERATE.sh 2026010406
# → data/json_tests/CASE_*/llm_text/LLM-OUTLOOK-*.md + .pdf
```

**If CASE data missing**, sync from export:
```bash
python scripts/sync_case_from_local.py --init YYYYMMDDHH \
  --source ~/basinwx-data/clyfar/basinwx_export --history 5
```

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success (validated) |
| 1 | CLI failure |
| 2 | Validation failed (meta-response detected, archived to `llm_text/archive/`) |

---

## Environment

**Production**: Always `unset LLM_CLI_COMMAND` (custom commands cause ~60% meta-response failures).

**Required:**
- `DATA_UPLOAD_API_KEY` - BasinWx upload
- `SYNOPTIC_API_TOKEN` - Observations ([register](https://developers.synopticdata.com/))

---

## Q&A Context

Inject warnings into outlook:
```bash
source scripts/set_llm_qa.sh        # enable (edit QA_CONTENT first)
./LLM-GENERATE.sh INIT
source scripts/set_llm_qa.sh off    # disable
```

Or manually: `export LLM_QA_FILE=/path/to/warnings.md`

---

## Scheduled Runs

Handled by `scripts/submit_clyfar.sh`:
1. Runs Clyfar forecast
2. Exports JSON/PNG to BasinWx
3. Runs `LLM-GENERATE.sh` with validation
4. Uploads PDF to BasinWx

No manual intervention needed. Check logs at `~/logs/basinwx/clyfar_*.out`.

---

## CASE Directory Structure

```
CASE_YYYYMMDD_HHMMZ/
├── clustering_summary.json     # Auto-generated ensemble structure
├── possibilities/              # 31 ozone category heatmaps
├── percentiles/                # 31 ozone percentile scenarios
├── probs/                      # 1 exceedance probability file
├── weather/                    # 32 GEFS weather files
└── llm_text/
    ├── forecast_prompt_*.md    # Rendered prompt
    ├── LLM-OUTLOOK-*.md        # Generated outlook
    └── LLM-OUTLOOK-*.pdf       # PDF version
```
