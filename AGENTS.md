# Repository Guidelines
Date updated: 2026-08-07

Minimal cold-start router for the frozen Clyfar fork.

## Read first
- `HIBERNATION.md`: freeze boundary, seasonal ops state, and safe resume checks.
- `README.md`: environment, entrypoints, smoke commands, and output defaults.
- `docs/STORAGE-GUIDE.md`: scratch/archive/cache policy.
- `docs/TESTING.md`: test conventions.
- `docs/README.md`: deeper maintained references only when a task needs them.

## Repository boundary
- Treat this line as maintenance-frozen: preserve the accepted Clyfar/Ffion behavior unless a task explicitly authorizes a science or feature change.
- Keep source, tests, templates, small required static lookups in `data/geog/`, and concise maintained docs in Git.
- Keep run data, replay/reforecast results, CASE bundles, figures, logs, Matplotlib state, and Herbie caches outside the checkout.
- Do not add dated handoffs, session summaries, case-study artifacts, generated notebook output, or speculative roadmaps. Use Git history, `../ceidwad`, `../brc-knowledge`, or the manuscript repo as appropriate.
- For legacy-checkout cleanup, classify tracked static data, derived outputs, and
  regenerable caches before acting. Preserve `data/geog/`; relocate reviewed
  outputs separately; do not bundle a deep Herbie cache into a cross-filesystem
  move. For high-file-count outputs, stage by same-filesystem rename and use a
  monitored resumable transfer. Follow `docs/STORAGE-GUIDE.md`.

## Fast orientation
- Forecast entrypoint: `run_gefs_clyfar.py`.
- Winter replay driver: `scripts/run_winter_replay.py`.
- Ffion wrapper: `scripts/run_llm_outlook.sh`.
- Verification authority and implementation boundary: `verif/README.md`.
- Ffion extraction and experiment contracts: `docs/project_overview.md`.
- Core source: `fis/`, `nwp/`, `preprocessing/`, `obs/`, `viz/`, `utils/`, `export/`.

## Workflow rules
- On CHPC, activate Miniforge explicitly when needed: `source ~/software/pkg/miniforge3/etc/profile.d/conda.sh && conda activate clyfar-nov2025`.
- Prefer `env PYTHONPATH=. pytest ...`; run the `README.md` smoke command before broad runtime changes.
- For replay triage, inspect exact logs, manifests, quicklooks, and `ledger.csv`; avoid broad scans of replay roots or caches.
- Avoid recursive `du`/`find` over repo-local caches during cold start. Cache
  depth can turn a harmless inventory into a long NFS operation.
- Multiprocessing uses `spawn`; retain `if __name__ == "__main__":` guards.
- Treat `nwp/` cache/locking edits and `scripts/submit_clyfar.sh` init anchoring carefully.
- Replay resume is durable only after a ledger `SUCCESS` row or `validated, ledger updated, cache cleanup complete`.
- Slurm `COMPLETED` does not prove the LLM stage passed; verify explicit markers plus `.out`/`.err`.
- Use `Uinta` for geography/meteorology; `Uintah` only for civic or human entities.

## Cross-repo pointers
- `../ceidwad`: task cards and run reports.
- `../preprint-clyfar-v0p9`: manuscript source of truth.
- `../brc-knowledge`: durable research/reference material.
- `../brc-tools`: shared operational utilities.
