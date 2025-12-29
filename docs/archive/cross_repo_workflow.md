# Cross-Repo Context Workflow
Date updated: 2025-10-05

Clyfar work draws on three local repositories: the main codebase (this repo), a knowledge base (Scholarium), and a preprint repo. To keep coordination clean and secure:

## 1. Document Each Repository Locally
- In every repo root, add a lightweight `CODEX-KB.md` describing:
  - Purpose and scope.
  - Key directories/files to consult.
  - Current branch/tag for reference.
  - Maintainer or point of contact.
- Avoid absolute paths; refer generically (e.g., “Scholarium KB repo under personal GitHub workspace”).

## 2. Reference External Docs from the Main Repo
- Update `docs/README.md` with an “External Knowledge Sources” section.
- For each source, list:
  - Repo name.
  - Relative note pointing to its `CODEX-KB.md` (e.g., “See Scholarium repo guidance doc”).
  - Optional summary of what information it provides (metrics, theory, references).

## 3. Inline Key Artifacts When Needed
- If certain tables or summaries are frequently cited, copy relevant excerpts into this repo’s `docs/` directory (with attribution).
- Keep synced by noting update dates and the originating repo/commit.

## 4. Link Repos via Submodule or Sync Script (Optional)
- **Submodule approach:** `git submodule add <repo-url> kb/scholarium` for read-only context.
  - Pros: reproducible, tracked revisions.
  - Cons: adds submodule management overhead.
- **Sync script approach:** create automation (Make/Poetry/Nox) that pulls latest notes from other repos into a temporary staging directory when needed.

## 5. Capture Cross-Repo Procedures
- Maintain a shared doc (e.g., `docs/cross-repo-workflow.md`) outlining steps to:
  - Export metrics/data from the knowledge base.
  - Drop reference outputs into the preprint repository.
  - Update this repo with synced summaries (if required).
- Include example commands, expected file locations, and validation checks.

Keeping these steps in place ensures Codex and collaborators can navigate the multi-repo knowledge pipeline without leaking sensitive paths or duplicating large artefacts.
