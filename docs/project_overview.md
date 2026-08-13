# Clyfar Project Overview
Date updated: 2026-08-07

Clyfar produces wintertime ozone guidance for the Uinta Basin from GEFS
forecast inputs. It reduces ensemble weather fields to basin-representative
predictors, applies a fuzzy inference system, renders forecast products, exports
BasinWx JSON, and can generate a Ffion narrative outlook.

## Runtime flow

1. `run_gefs_clyfar.py` parses the run contract and coordinates the pipeline.
2. `nwp/` retrieves and caches the required GEFS fields. Herbie caches live
   outside the checkout; the small lookup tables in `data/geog/` are the only
   versioned data files.
3. `preprocessing/` converts gridded ensemble fields into representative basin
   time series for snow depth, pressure, wind, solar radiation, and related
   predictors.
4. `fis/` evaluates the accepted fuzzy membership functions and rules. The
   maintained production baseline is implemented in `fis/v0p9.py`.
5. `viz/` creates heatmaps, meteograms, and diagnostic figures.
6. `export/` writes the BasinWx-compatible forecast representation.
7. `scripts/run_llm_outlook.sh` assembles the versioned Ffion bundle and invokes
   the LLM path with uploads disabled by default.

## Main contracts

- Multiprocessing uses `spawn`; executable paths must retain main guards.
- Run and cache roots are externalized according to `docs/STORAGE-GUIDE.md`.
- `scripts/submit_clyfar.sh` is the operational Slurm entrypoint and anchors the
  forecast initialization time.
- `scripts/run_winter_replay.py` owns replay manifests, quicklooks, ledger
  updates, validation, and durable resume behavior.
- Ffion prompt, bias, QA, and bundle selection are versioned under
  `templates/llm/`; `utils/versioning.py` and `utils/ffion_bundle.py` resolve the
  active contract.

## New-work boundaries

New work must not turn the frozen operational checkout into a mixed research
tree. Use one branch and external worktree per lane.

| Lane | Owner and stable interface | Boundary |
|---|---|---|
| Ffion | A future `brc-ffion` owns prompting, bundle resolution, narrative validation, and LLM/PDF execution. Clyfar owns the versioned CASE inputs and forecast provenance. | During migration, `FFION_MANIFEST` is the compatibility seam. Do not remove the bundled Ffion path until an external bundle produces parity on fixed CASE fixtures. |
| Evaluation | `../brc-knowledge` owns the scorecard mathematics; a scoring package owns its implementation; Clyfar supplies member-preserving raw possibilities, observations, and provenance. | Do not depend on the current `../possverif` prototype. Follow `verif/README.md` and pin the exact scorecard source used. |
| Optimisation | Treatment branches may change rules, membership functions, add a pseudo-lapse-rate input, or correct upstream predictors. | Preserve `fis/v0p9.py` as the control. Each treatment must emit the same forecast contract and retain raw plus transformed predictors. |

Scenario clustering remains a Clyfar-side forecast product: it converts the
GEFS/Clyfar ensemble into deterministic context. Ffion may consume that context
but should not own or silently alter the meteorological calculation.

### Ffion migration map

Move the consumer side first: `templates/llm/`, bundle resolution, prompt
rendering, outlook extraction/validation, LLM invocation, and PDF production.
Keep the producer side here: Clyfar/GEFS inference, export and CASE schemas,
scenario clustering, replay bookkeeping, and the Slurm integration adapter.
`scripts/run_case_pipeline.py` currently crosses that boundary and should be
split at the completed CASE/clustering-summary contract rather than copied
whole into both repositories.

Perform the extraction from a clone or filtered history, not by deleting the
live Clyfar path first. The migration gate is parity on fixed external CASE
fixtures for resolved bundle identity and hashes, rendered prompt, validator
result, exit codes, and stage markers. Generated LLM prose is not a byte-stable
parity target. Keep the bundled implementation until the external CLI passes
that gate and the operational wrapper can select it explicitly.

## Versions, tags, and experiment identity

- Clyfar releases use annotated `vX.Y.Z` tags. While Ffion remains bundled,
  its compatibility releases retain annotated `ffion-vX.Y.Z` tags.
- An independent `brc-ffion` should be created by history-preserving extraction,
  then use its own annotated `vX.Y.Z` tags. Clyfar records the Ffion version,
  manifest path, and component hashes; the two projects do not share a version
  number.
- Never move an existing tag. A maintenance fix gets a new patch tag; a bundle
  or prompt change gets a new Ffion patch tag even when the Clyfar version is
  unchanged.
- Experiment branches start from one exact annotated Clyfar baseline. Prefer
  `eval/<name>` and `exp/<factor>/<name>` branch names; tag only durable
  checkpoints, using a namespaced tag such as `exp/rules-ga/v0.1.0`.
- Every comparison records the baseline and treatment commits, dirty-tree
  state, Clyfar/FIS/Ffion identities, input-data identifier, scorecard source
  path and hash, random seeds, and output root. Run reports belong in
  `../ceidwad`, not this repository.

## Possibility output

The fuzzy system maps meteorological inputs onto linguistic memberships and
combines rule activations into categorical ozone possibilities. These values
are possibilities, not calibrated probabilities. Downstream products retain
the category distribution and percentile-like ozone summaries without
silently converting the semantics to probability.

## Frozen scope

This repository preserves the accepted implementation and its automated tests.
Exploratory notebooks, event analyses, proposal figures, session notes, and
research roadmaps are intentionally excluded from the current tree. Use Git
history or the sibling repositories named in `AGENTS.md` when that context is
needed.

For execution, start with `README.md`. For safe modification, follow
`AGENTS.md`, `HIBERNATION.md`, `docs/TESTING.md`, and
`docs/STORAGE-GUIDE.md`.
