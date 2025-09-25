# Notebooks Index
Date updated: 2025-09-25

Each notebook lives in a domain-specific subfolder. For every file you will find:
- **Contains:** brief purpose or focus.
- **Stage:** `exploration`, `needs polishing`, or `ready to convert` (move logic into .py modules).

## fis/
- `clyfar_v0.ipynb`
  - Contains: Early fuzzy-inference membership and rule sketches for the original prototype.
  - Stage: needs polishing.
- `clyfar_v0p9.ipynb`
  - Contains: Working notes for the v0.9 membership functions, rules, and scenario checks.
  - Stage: needs polishing.
- `guide_to_fuzzy_inference.ipynb`
  - Contains: Walkthrough of fuzzy inference concepts applied to Clyfar variables.
  - Stage: exploration.

## nwp/
- `gefs_0p5_demo.ipynb`
  - Contains: GEFS 0.5° data loading and slicing examples.
  - Stage: exploration.
- `gefs_notebook.ipynb`
  - Contains: Broader NWP data experiments comparing members and variables.
  - Stage: needs polishing.

## obs/
- `messing_with_synoptic_data.ipynb`
  - Contains: Synoptic API pulls and observation cleaning tests.
  - Stage: exploration.
- `roosevelt_lidar.ipynb`
  - Contains: Roosevelt LIDAR analysis and visual QC.
  - Stage: exploration.

## preprocessing/
- `creating_rep_obs.ipynb`
  - Contains: Representative observation calculations feeding preprocessing modules.
  - Stage: needs polishing.
- `pseudolapserate_demo.ipynb`
  - Contains: Pseudo-lapse-rate derivations and terrain sampling experiments.
  - Stage: exploration.

## postprocessing/
- `possibility_fcsts.ipynb`
  - Contains: Post-processing ideas for possibility forecasts and visual outputs.
  - Stage: needs polishing.

## operations/
- `clyfar_script.ipynb`
  - Contains: Notebook version of the operational script with inline tweaks.
  - Stage: needs polishing.
- `operational_clyfar_forecast.ipynb`
  - Contains: Forecast orchestration runs with manual checkpoints and plots.
  - Stage: needs polishing.

## viz/
- `noaa_proposal_figures.ipynb`
  - Contains: Figure generation for NOAA proposal material and presentation graphics.
  - Stage: needs polishing.

## reference/
- `clyfar_explained.ipynb`
  - Contains: Narrative explanation notebook for stakeholders (inputs, outputs, logic).
  - Stage: ready to convert.

## sandbox/
- `pandas_playground.ipynb`
  - Contains: Ad-hoc pandas experiments and quick data sanity checks.
  - Stage: exploration.

Maintenance tips:
- Update this README when notebooks move, change focus, or graduate stages.
- Prefer promoting mature logic into `clyfar/` modules with tests.
- Archive obsolete notebooks under an `archived/` subfolder before deletion.
