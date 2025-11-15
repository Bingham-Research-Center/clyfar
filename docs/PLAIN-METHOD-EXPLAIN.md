# Plain Method History & Trajectory
Date updated: 2025-11-15

## Baseline Reinforcement Narrative
### Microtask trail from v0.9
1. Guarded Matplotlib caches via `MPLCONFIGDIR` export inside `run_gefs_clyfar.py`.
2. Mirrored smoke-test instructions between `README.md`, `AGENTS.md`, and `docs/README.md`.
3. Trimmed `utils/__init__.__all__` to the four production modules actually imported elsewhere.
4. Replaced the stale `filetree.txt` dump with a dated, high-level index.
5. Flagged token-heavy notebooks for archival in `notebooks/README.md`.
6. Added the external LaTeX report pointer to `docs/AI_AGENT_ONBOARDING.md`.
7. Authored `docs/baseline_0_9.md` with smoke + regression commands, artefact map, and SHA placeholders.
8. Created `scripts/run_smoke.sh` so every smoke run logs into `data/baseline_0_9/logs/` and `performance_log.txt`.

The v0.9 branch originally shipped as a single `run_gefs_clyfar.py` script and a set of informal notebooks. We hardened that baseline incrementally by first controlling runtime environments—`run_gefs_clyfar.py` now exports `MPLCONFIGDIR` so Matplotlib writes caches inside the workspace, eliminating noisy warnings on multi-user nodes. Documentation guardrails followed: `README.md`, `AGENTS.md`, and `docs/README.md` were synchronized so every contributor sees the same smoke command and environment instructions. We pruned the `utils` namespace (`__all__` exports now include only modules actually imported in production) to shrink CLI startup cost and reduce accidental token usage, and we documented stale notebooks plus external knowledge bases so agents know what to skip.

The baseline itself is now explicit. `docs/baseline_0_9.md` records the canonical smoke and regression commands, artefact directories, and placeholder SHAs for both the code and LaTeX report. `scripts/run_smoke.sh` wraps the `--testing` CLI to capture logs under `data/baseline_0_9/logs/` while mirroring status lines into `performance_log.txt`, guaranteeing provenance for every smoke execution. These additions shrink the gap between the ad‑hoc v0.9 workflow and a reproducible release candidate without touching the scientific core of v0p9. The next steps—freezing constraints, capturing regression stats, and updating the LaTeX appendix—are now straightforward because the supporting scaffolding already exists in-repo.
