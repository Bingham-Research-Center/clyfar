# Maintained Documentation
Date updated: 2026-08-07

The frozen fork keeps only current operational, testing, storage, and core
method references. Historical plans, session handoffs, event studies, and
generated artifacts remain available through Git history rather than an
in-tree archive.

Read `README.md`, `AGENTS.md`, and `HIBERNATION.md` before using this index.

## Operations and reproducibility

- `docs/STORAGE-GUIDE.md` — CHPC scratch/archive/cache policy and non-repo defaults.
- `docs/TESTING.md` — pytest conventions and focused test commands.
- `docs/setup_conda.md` — Miniforge/Conda environment setup.
- `docs/replay_resource_profiles.md` — winter replay Slurm profiles.
- `docs/slurm/clyfar_test.sbatch` — bounded CHPC smoke template.

## Implementation and method

- `docs/project_overview.md` — architecture, new-work boundaries, and version/provenance policy.
- `docs/external_data_references.md` — authoritative GEFS/Herbie data references.
- `docs/herbie_api_cheatsheet.md` — maintained GEFS/Herbie query patterns.
- `verif/README.md` — live scorecard authority and evaluation data contract.

When changing this set, update this index in the same change. New dated
handoffs, roadmaps, case reports, and notebook outputs belong outside the
frozen repository.
