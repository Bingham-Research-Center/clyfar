# Notebooks Index
Date updated: 2025-09-25

Each notebook lives in a domain-specific subfolder. For every file you will find:
- **Contains:** brief purpose or focus.
- **Stage:** `exploration`, `needs polishing`, or `ready to convert` (move logic into .py modules).

## fis/
- `clyfar_v0.ipynb`
  - Contains: Early fuzzy-inference membership and rule sketches for the original prototype.
  - Stage: needs polishing.
  - Next step: Extract finalised membership functions into `fis/versions/legacy/` for archival comparisons.
- `clyfar_v0p9.ipynb`
  - Contains: Working notes for the v0.9 membership functions, rules, and scenario checks.
  - Stage: needs polishing.
  - Next step: Translate confirmed MF parameters into YAML config to feed the upcoming registry system.
- `guide_to_fuzzy_inference.ipynb`
  - Contains: Walkthrough of fuzzy inference concepts applied to Clyfar variables.
  - Stage: exploration.
  - Next step: Convert explanatory plots into reusable figures in `notebooks/fis_guide_figures/` documentation.

## nwp/
- `gefs_0p5_demo.ipynb`
  - Contains: GEFS 0.5° data loading and slicing examples.
  - Stage: exploration.
  - Next step: Migrate data access snippets into `clyfar/nwp/interfaces.py` as regression tests.
- `gefs_notebook.ipynb`
  - Contains: Broader NWP data experiments comparing members and variables.
  - Stage: needs polishing.
  - Next step: Summarise best-performing representative metrics and codify them in preprocessing functions.

## obs/
- `messing_with_synoptic_data.ipynb`
  - Contains: Synoptic API pulls and observation cleaning tests.
  - Stage: exploration.
  - Next step: Package the observation fetch/clean pipeline into a script under `obs/` with CLI flags.
- `roosevelt_lidar.ipynb`
  - Contains: Roosevelt LIDAR analysis and visual QC.
  - Stage: exploration.
  - Next step: Extract vetted LIDAR processing steps into a dedicated module in `obs/` for reuse.

## preprocessing/
- `creating_rep_obs.ipynb`
  - Contains: Representative observation calculations feeding preprocessing modules.
  - Stage: needs polishing.
  - Next step: Turn proven calculations into unit-tested helpers inside `preprocessing/representative_obs.py`.
- `pseudolapserate_demo.ipynb`
  - Contains: Pseudo-lapse-rate derivations and terrain sampling experiments.
  - Stage: exploration.
  - Next step: Formalise lapse-rate logic into feature-engineering functions referenced by upcoming v1.1 builds.

## postprocessing/
- `possibility_fcsts.ipynb`
  - Contains: Post-processing ideas for possibility forecasts and visual outputs.
  - Stage: needs polishing.
  - Next step: Port the most effective visualisations into `viz/possibility_funcs.py` and hook into CLI output.

## operations/
- `clyfar_script.ipynb`
  - Contains: Notebook version of the operational script with inline tweaks.
  - Stage: needs polishing.
  - Next step: Diff against `run_gefs_clyfar.py` to ensure all manual adjustments are captured as CLI options.
- `operational_clyfar_forecast.ipynb`
  - Contains: Forecast orchestration runs with manual checkpoints and plots.
  - Stage: needs polishing.
  - Next step: Log the manual checkpoint logic as automation hooks in the experiment runner roadmap.

## viz/
- `noaa_proposal_figures.ipynb`
  - Contains: Figure generation for NOAA proposal material and presentation graphics.
  - Stage: needs polishing.
  - Next step: Export key figure templates to a scriptable pipeline for reproducible proposal graphics.

## reference/
- `clyfar_explained.ipynb`
  - Contains: Narrative explanation notebook for stakeholders (inputs, outputs, logic).
  - Stage: ready to convert.
  - Next step: Convert the narrative into Markdown (`docs/clyfar_explained.md`) and link from the website/docs.

## sandbox/
- `pandas_playground.ipynb`
  - Contains: Ad-hoc pandas experiments and quick data sanity checks.
  - Stage: exploration.
  - Next step: Promote any recurring patterns into `utils/dataframe_tools.py`; archive the rest when stable.

Maintenance tips:
- Update this README when notebooks move, change focus, or graduate stages.
- Prefer promoting mature logic into `clyfar/` modules with tests.
- Archive obsolete notebooks under an `archived/` subfolder before deletion.
