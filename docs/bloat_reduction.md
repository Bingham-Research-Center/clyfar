# Bloat & Token-Saving Cleanup List
Date: 2025-11-15

Goal: shrink context overhead for humans + AI agents while keeping the scientific trail intact. Use this as a living inventory; strike items as they’re completed.

## High-Priority Targets
1. **`postprocesing/` typo directory** — merge into `postprocessing/` (or `viz/` if only plots) and delete the duplicate tree. Leave a shim module for compatibility until v1.0.
2. **`bkup/` scripts** — audit each file; anything obsolete belongs in `notebooks/archived/` or should be removed after confirming no references via `rg`.
3. **`filetree.txt`** — regenerate automatically or drop; the current static dump confuses AI agents when it’s out of date.
4. **Large notebook outputs** — ensure `.ipynb_checkpoints/` are gitignored and heavy notebooks are referenced only through summaries (see `notebooks/README.md`).
5. **`figures*/` and `data*/`** — double-check `.gitignore` coverage and remind contributors not to reference these directories in documentation as sources of truth.
6. **Verbose docs** (`docs/ml_ideas.md`, `docs/patches_table.md`) — keep but add warning headers so agents skip unless needed.
7. **`performance_log.txt`** — rotate or compress logs older than 30 days to stop token-heavy reads; document location in `docs/validation.md`.
8. **Missing LaTeX pointer** — the technical report referenced in planning isn’t present in the repo (no `.tex` files found). Add a stub in `docs/README.md` + `docs/AI_AGENT_ONBOARDING.md` once the shared path (e.g., `reports/clyfar_tech_report/main.tex` or external repo link) is confirmed so AI agents know where to sync context without searching blindly.

## Token-Saving Restructures
- **Documentation hub**: move long-form narrative from `README.md` into `docs/project_overview.md`, leaving the root README lean (mission + quickstart + links).
- **Indexing bundle**: create `docs/index.md` listing only the files agents should read per task type (mirrors `docs/AI_AGENT_ONBOARDING.md`) and link it from the repo root.
- **Module summaries**: add short `MODULE.md` files in directories like `preprocessing/` and `nwp/` that describe contents in <30 lines, so agents can skim instead of opening every file.
- **Deprecation staging**: mark files scheduled for deletion with a `# DEPRECATED after v0.9` docstring and track them in this file; it reduces rework and gives agents context before they load them.

## Workflow Notes
- Prefer `rg --files` or `rg -n "keyword"` to locate references instead of `find`/`grep` combos.
- Encourage use of `head/tail` to peek at large files (>500 lines) before opening fully; document this in `AGENTS.md`.
- Capture a weekly `git count-objects -v` snapshot to see whether artifacts are leaking into the repo history.

## Open Questions
- Confirm whether the LaTeX technical report lives in another repo (e.g., Overleaf, Git LFS). Once known, add a pointer plus sync instructions so code + narrative stay aligned.
- Decide if notebooks should move to a separate knowledge-base repo referenced as a submodule to cut checkout size.
- Evaluate whether `data_seth/` is still needed; if yes, document provenance and size so contributors don’t accidentally read it.
