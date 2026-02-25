# LLM Forecast SOP

Ffion workstream target: v1.1 (current tag: ffion-v1.1).
Clyfar current milestone: v0.9.8.

## Known issues
- Q&A outputs can be verbose if prompt conditioning drifts from the default path.
- Clustering logic still needs review; treat summaries as provisional.

## Versioning policy
- Clyfar tags (`v0.9.x`, `v1.0`, ...) track scientific/output logic changes (FIS, clustering, preprocessing, exports).
- Ffion tags (`ffion-v1.x`) track prompt/workflow/LLM pipeline changes and can advance independently.
- Record both tags in release notes or session logs when they move in tandem.

## v1.1 branch scope
- Integration branch: `hotfix/ffion-1.1-clustering` (merged with latest `main`).
- Reviewed as context only (not merged for v1.1): `feature/case-aware-demo-scripts`, `bugfix/cfgrib-load-fallback`, `michael_branch`.
- v1.1 focus: unified clustering logic across summary/demo surfaces, stronger clustering diagnostics, confidence-aware prompt conditioning, and more robust markdown→PDF rendering defaults.

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

## Preferred Dev Test Path (Cron-Parity)

Use this for repeatable Ffion testing that mirrors the production post-forecast path in `scripts/submit_clyfar.sh`:

```bash
# Single init (sync CASE + cron-parity env + local LLM-GENERATE)
./scripts/run_llm_outlook.sh 2026022400 --force

# Serial 6-hourly window (chronological, for previous-outlook continuity tests)
./scripts/run_llm_outlook.sh --start 2026022000 --end 2026022400 --force
```

Notes:
- Default is test-safe (`LLM_SKIP_UPLOAD=1`). Add `--upload` only when you intentionally want website uploads.
- Default retries match cron parity (`LLM_MAX_RETRIES=3`).
- Script unsets `LLM_CLI_COMMAND/LLM_CLI_BIN/LLM_CLI_ARGS` by default to match production behavior.

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

Inject optional operator notes into outlook:
```bash
source scripts/set_llm_qa.sh        # enable (edit QA_CONTENT first)
./LLM-GENERATE.sh INIT
source scripts/set_llm_qa.sh off    # disable
```

Or manually: `export LLM_QA_FILE=/path/to/notes.md`

Notes are applied only where relevant to affected lead windows/scenarios.

Default short-term bias definitions are loaded from `templates/llm/short_term_biases.json`.

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
├── forecast_clustering_summary_YYYYMMDD_HHMMZ.json  # Auto-generated ensemble structure
├── possibilities/              # 31 ozone category heatmaps
├── percentiles/                # 31 ozone percentile scenarios
├── probs/                      # 1 exceedance probability file
├── weather/                    # 32 GEFS weather files
└── llm_text/
    ├── forecast_prompt_*.md    # Rendered prompt
    ├── LLM-OUTLOOK-*.md        # Generated outlook
    └── LLM-OUTLOOK-*.pdf       # PDF version
```
