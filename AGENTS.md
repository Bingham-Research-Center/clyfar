# Repository Guidelines
Date updated: 2026-05-14

This is the top-level operating guide for Clyfar agents.

## First Read
- Read `HIBERNATION.md` after this file for current seasonal ops state and priorities.

## Project Layout
- `run_gefs_clyfar.py` is the main entry point for GEFS ingest, preprocessing, FIS inference, plotting, and export.
- Core directories: `fis/`, `nwp/`, `preprocessing/`, `obs/`, `viz/`, `utils/`, `export/`.
- Local artifacts, not source: `data/`, `figures/`, `figures_parallel/`.
- Archived notes and drafts: `docs/archive/root_notes/`.

## Run
- Environment: `conda create -n clyfar python=3.11.9 && conda activate clyfar`
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
- Use `/scratch/general/vast/u0737349/clyfar_replay/winter_2025_2026` for active replay execution.
- Use `/uufs/chpc.utah.edu/common/home/lawson-group6/clyfar/replay/winter_2025_2026` for durable performance-review outputs.
- Do not expect replay artifacts in GitHub, and do not move large replay outputs into `$HOME`.
- Check image paths directly on CHPC, especially `figures/heatmap/` and `figures/meteograms/` under the group6 archive root.

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
