# Repository Guidelines
Date updated: 2026-05-22

This is the top-level operating guide for Clyfar agents.

## First Read
- Read `HIBERNATION.md` after this file for current seasonal ops state and priorities.

## Project Layout
- `run_gefs_clyfar.py` is the main entry point for GEFS ingest, preprocessing, FIS inference, plotting, and export.
- Core directories: `fis/`, `nwp/`, `preprocessing/`, `obs/`, `viz/`, `utils/`, `export/`.
- Local artifacts, not source: `data/`, `figures/`, `figures_parallel/`.
- Archived notes and drafts: `docs/archive/root_notes/`.

## Run
- Local environment: `conda create -n clyfar python=3.11.9 && conda activate clyfar`
- CHPC environment: use Miniforge at `~/software/pkg/miniforge3`; operational jobs activate `clyfar-nov2025` in `scripts/submit_clyfar.sh`.
- Interactive shells and agents may inherit `clyfar-nov2025`, but do not assume it. Check `CONDA_DEFAULT_ENV`; if needed, run `source ~/software/pkg/miniforge3/etc/profile.d/conda.sh && conda activate clyfar-nov2025`.
- Install deps: `pip install -r requirements.txt`
- Smoke test: `python run_gefs_clyfar.py -i 2024010100 -n 2 -m 2 -d ./data -f ./figures --testing`
- Full run: `python run_gefs_clyfar.py -i 2024010100 -n 8 -m 10 -d ./data -f ./figures`

## Ffion / LLM
- Preferred dev path: `./scripts/run_llm_outlook.sh <INIT> --force` or `--start ... --end ... --force`.
- Use `--check` for prerequisites.
- Default is upload-safe (`LLM_SKIP_UPLOAD=1`); use `--upload` intentionally.
- For uploads, source `~/.bashrc_basinwx` first or set `DATA_UPLOAD_API_KEY` and `BASINWX_API_URL`; if creds look stale, `unset DATA_UPLOAD_API_KEY BASINWX_API_URL; source ~/.bashrc_basinwx`.
- For `scripts/submit_clyfar.sh`, keep `CLYFAR_SKIP_INTERNAL_EXPORT=1` and set `CLYFAR_ENABLE_UPLOAD=0` for local-only runs.
- Ffion versioning is first-class: `FFION_VERSION` resolves prompt/bias/QA files via `templates/llm/ffion_registry.json`; record the exact manifest and hashes in rendered prompts.
- Validate generated outlooks with `scripts/validate_llm_outlook.py`.
- Use `Uinta` for geography/meteorology; `Uintah` only for civic/human entities.
- Prune old generated artifacts with `python scripts/prune_llm_case_artifacts.py --dry-run` first.

## Winter Replay Artifacts
- The replay launcher can run from a login shell in `tmux`/`screen`; Slurm runs the compute job. Do not assume an interactive `salloc` node is needed for the serial driver.
- Current replay defaults: `--account lawson-np --partition lawson-np --cpus 16 --mem 48G --time 02:00:00 --poll-seconds 30`.
- Short replay resume command: `python scripts/run_winter_replay.py --start <YYYYMMDDHH> --end 2026031518 --resume`.
- Use `/scratch/general/vast/u0737349/clyfar_replay/winter_2025_2026` for active replay execution.
- Use `/uufs/chpc.utah.edu/common/home/lawson-group6/clyfar/replay/winter_2025_2026` for durable performance-review outputs.
- Do not expect replay artifacts in GitHub, and do not move large replay outputs into `$HOME`.
- Check image paths directly on CHPC, especially `figures/heatmap/` and `figures/meteograms/` under the group6 archive root.
- Durable replay checkpoint: a ledger `SUCCESS` row, or the driver line `validated, ledger updated, cache cleanup complete`. Killing before that may force `--resume` to resubmit the current init.
- For suspected partial runs, inspect the current init's `*_run`, `CASE_*`, manifest, quicklook, logs, and ledger before deleting anything.

## Testing
- Put tests in `tests/test_*.py`.
- Prefer `env PYTHONPATH=. pytest ...` over bare `pytest`.
- For focused regression checks, use the Ffion bundle/validation tests in `tests/`.
- Before major changes, run the smoke workflow with `--testing` and reduced members.

## Safety
- Multiprocessing uses `spawn`; guard entry points with `if __name__ == "__main__":`.
- Treat `nwp/` cache and locking edits carefully.
- `.out` is the orchestration stream; `.err` usually has the traceback.
- A Slurm job can be `COMPLETED` while the LLM stage still failed; check explicit LLM markers.
- `squeue` is the live job check; `sacct` may fail from Slurm accounting DB/connectivity issues even on login nodes. Use logs and artifacts when accounting is unavailable.
- CHPC scheduler time is local Mountain time; BasinWx-facing artifacts and GEFS cycles are UTC.
- `scripts/submit_clyfar.sh` init anchoring must stay based on Slurm `SubmitTime`, not `utcnow()` alone.
- Common gotchas: `~/.local/bin` must be on `PATH` for `claude`; direct texlive path injection is preferred for PDF generation.

## Future Ops
- Move operational runtime off a mutable checkout.
- Prefer a pinned deploy tree plus separate dev worktree/clone.
- Use `HIBERNATION.md` as the pause/resume checkpoint.

## Cross-Repo
- `../ceidwad`: control plane for task cards and run reports.
- `../preprint-clyfar-v0p9`: manuscript source of truth.
- `../brc-knowledge`: durable reference material.
- `../brc-tools`: shared utilities only when directly relevant.
