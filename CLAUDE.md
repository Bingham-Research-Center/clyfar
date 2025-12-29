# Clyfar - Claude Code Context

## Project
**Clyfar** = Operational ozone forecasting for Uinta Basin, Utah (Bingham Research Center)
- GEFS ensemble (31 members) → Fuzzy Inference System → Possibility distributions
- Outputs: daily ozone forecasts (JSON + PNG) pushed to basinwx.com
- Version: v0.9 operational | 4x daily on CHPC

## Quick Commands
```bash
# Smoke test (2 members, fast)
python run_gefs_clyfar.py -i 2025010100 -n 4 -m 2 -d ./data -f ./figures -t

# Full production run
python run_gefs_clyfar.py -i 2025010100 -n 16 -m 31 -d ./data -f ./figures

# Unit tests
pytest tests/

# LLM outlook generation
./LLM-GENERATE.sh 2025010100
```

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
├── percentiles/    # Scenario JSONs
├── probs/          # Exceedance probabilities
├── possibilities/  # Category heatmaps
├── figs/           # Generated visualizations
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
