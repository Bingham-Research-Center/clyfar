# Clyfar - Claude Code Context

## Project
**Clyfar** = Operational ozone forecasting for Uinta Basin, Utah (Bingham Research Center)
- GEFS ensemble (31 members) → Fuzzy Inference System → Possibility distributions
- Outputs: daily ozone forecasts (JSON + PNG) pushed to basinwx.com
- Version: v0.9 operational | 4x daily on CHPC

## Common Tasks (for humans and Claude CLI)

### 1. Run full pipeline (GEFS download + Clyfar + export)
```bash
# Production run on CHPC (replace YYYYMMDDHH with init time, e.g., 2025123006)
python run_gefs_clyfar.py -i YYYYMMDDHH -n 16 -m 31 \
  -d ~/basinwx-data/clyfar -f ~/basinwx-data/clyfar/figures

# Smoke test (fast, 2 members)
python run_gefs_clyfar.py -i YYYYMMDDHH -n 4 -m 2 -d ./data -f ./figures -t
```

### 2. Generate LLM outlook (requires CASE data to exist)
```bash
# Step 1: Sync CASE data from export directory (if not already done)
python scripts/sync_case_from_local.py --init YYYYMMDDHH \
  --source ~/basinwx-data/clyfar/basinwx_export --history 5

# Step 2: Generate LLM outlook
./LLM-GENERATE.sh YYYYMMDDHH

# Output: data/json_tests/CASE_*/llm_text/LLM-OUTLOOK-*.md
```

### 3. Check data readiness before LLM generation
```bash
# Verify CASE directory has required JSONs
ls data/json_tests/CASE_YYYYMMDD_HHMMZ/{possibilities,percentiles,probs,weather}/

# Check recent exports exist
ls ~/basinwx-data/clyfar/basinwx_export/*YYYYMMDD_HHMMZ.json | wc -l
# Should be 95 files (63 ozone + 32 weather)
```

### 4. Set Q&A context (optional warnings for LLM)
```bash
# Edit scripts/set_llm_qa.sh to change QA_CONTENT, then:
source scripts/set_llm_qa.sh      # enable
source scripts/set_llm_qa.sh off  # disable
```

### Quick reference
| Task | Command |
|------|---------|
| Full pipeline | `python run_gefs_clyfar.py -i INIT -n 16 -m 31 -d ~/basinwx-data/clyfar -f ~/basinwx-data/clyfar/figures` |
| Sync CASE data | `python scripts/sync_case_from_local.py --init INIT --source ~/basinwx-data/clyfar/basinwx_export --history 5` |
| LLM generation | `./LLM-GENERATE.sh INIT` |
| Unit tests | `pytest tests/` |

## Directory Structure
```
run_gefs_clyfar.py      # Main entry point (CLI orchestrator)
fis/v0p9.py             # FIS rules, membership functions, Clyfar class
preprocessing/          # Feature engineering (snow, wind, mslp, solar, temp)
nwp/gefsdata.py         # GEFS download via Herbie
obs/obsdata.py          # Observations from Synoptic API
viz/                    # Plotting (meteograms, heatmaps, forecasts)
export/to_basinwx.py    # JSON/PNG upload to website
utils/                  # Shared helpers, lookups, geography
templates/llm/          # LLM prompt templates
scripts/                # Operational scripts, demos, pipelines
tests/                  # pytest unit tests
```

## Key Files by Task
| Task | Read First |
|------|------------|
| Bug fix / feature | `run_gefs_clyfar.py`, `docs/project_overview.md` |
| FIS / science change | `fis/v0p9.py`, `docs/science-questions.md` |
| NWP download issues | `nwp/gefsdata.py`, `nwp/download_funcs.py` |
| Preprocessing | `preprocessing/representative_nwp_values.py` |
| Export / website | `export/to_basinwx.py` |
| LLM outlook | `LLM-SOP.md`, `templates/llm/prompt_body.md` |
| Lookups / stations | `utils/lookups.py` |

## CHPC Deployment
- Conda: `clyfar-nov2025` in `~/software/pkg/miniforge3`
- Repo: `~/gits/clyfar`
- Data: `~/basinwx-data/clyfar`
- Logs: `~/logs/basinwx/clyfar_*.out`
- SLURM: `notchpeak-shared-short`, 16 CPUs, 48GB, 2h timeout
- Schedule: UTC 03:30, 09:30, 15:30, 21:30

## Environment Variables
```bash
DATA_UPLOAD_API_KEY     # BasinWx upload (unset to disable)
BASINWX_API_URL         # Default: https://basinwx.com
SYNOPTIC_API_TOKEN      # Observation API
```

## Coding Conventions
- PEP 8, 4-space indent, type hints where practical
- Modules: `snake_case.py` | Classes: `CamelCase` | Vars: `snake_case`
- Versioned modules: `vXrY` pattern (e.g., `v0p9.py`)
- Multiprocessing: `spawn` start method, avoid global state
- Commits: present tense, explain *why* not just *what*

## Core Concepts
- **Possibility theory**: Dubois-Prade framework, max-based aggregation
- **Subnormal distribution**: When max(possibility) < 1, remainder = ignorance
- **Ozone categories**: Background (20-50 ppb), Moderate (40-70), Elevated (50-90), Extreme (60-125)
- **dRisk/dt**: Run-to-run consistency tracking

## LLM Outlook Workflow
```
LLM-GENERATE.sh → run_case_pipeline.py → templates/llm/prompt_body.md
                                       → demo_*.py scripts (figs)
                                       → llm_text/forecast_prompt_*.md
```

CASE directory structure:
```
CASE_YYYYMMDD_HHMMZ/
├── percentiles/    # 31 ozone scenario JSONs
├── probs/          # 1 exceedance probability JSON
├── possibilities/  # 31 ozone category heatmap JSONs
├── weather/        # 32 GEFS weather JSONs (31 members + 1 percentiles)
└── llm_text/       # Prompts and LLM outputs
```

## Related Repos
- `brc-tools` (sibling): Shared utilities
- `ubair-website` (sibling): BasinWx Node.js frontend
- `preprint-clyfar-v0p9`: LaTeX technical report

## Skip These (low value)
- `notebooks/` - Exploratory, often stale
- `data/`, `figures*/` - Regenerated artifacts
- `docs/archive/` - Deprecated documentation

## Test Before Commit
```bash
python run_gefs_clyfar.py -i 2025010100 -n 2 -m 2 -d ./data -f ./figures -t
```
