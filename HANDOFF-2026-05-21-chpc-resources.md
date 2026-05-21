# Handoff — 2026-05-21 — CHPC resource doc consolidation

## What was done

Collapsed three docs in `brc-knowledge/scholarium/reference-base/resources/` into one canonical `chpc-team-resource-inventory.md` (664 lines). Tiered layout: ToC, §1–§8 quick-ref, Q1–Q5 Q&A, Appendices A–E. Plain language, acronyms expanded. Verified on notch137 (interactive, `lawson-np`) 2026-05-21.

Key corrections folded in: scratch is **1.5 PB** (not 1 PB); group4 + group5 mounts **broken** on notch137 today, group6 OK; new gotchas (Slurm CLI fails on compute, `quota -s` noisy on compute, `/home/lawson` is a Vast label not a path); cores notation reframed as "Slurm cores / OS threads (sockets × cores × threads)" for both owned Notchpeak nodes.

## Still to do (this session couldn't)

**Hard-delete the two retired files** — Bash sandbox blocks (see "Sandbox finding" below). Run yourself:

```bash
! rm ~/gits/brc-knowledge/scholarium/reference-base/resources/chpc-dashboard-lookup.md
! rm ~/gits/brc-knowledge/scholarium/reference-base/resources/inventory-response-admin-dashboard.md
```

**Commit/push** of the brc-knowledge change probably blocked too (`.git/index` is on read-only mount); see "Sandbox finding". If commit failed in-session, re-run from your shell:

```bash
cd ~/gits/brc-knowledge && git add scholarium/reference-base/resources/chpc-team-resource-inventory.md && git rm scholarium/reference-base/resources/chpc-dashboard-lookup.md scholarium/reference-base/resources/inventory-response-admin-dashboard.md && git commit -m "docs(chpc): consolidate three resource refs into one canonical" && git push
```

## Followups (separate scope, do later)

1. Re-verify §3 (`sacctmgr`) and §4 (`sinfo`) tables **from a login node** (`ssh notchpeak.chpc.utah.edu`); bump dates in Appendix E.
2. `notch392` + `kp234–237` warranty/spec rows in §2 inherited from 2026-04-07 — re-verify next time you're on notch392, or `scontrol show node <name>` from a login.
3. Switch `clyfar/scripts/submit_clyfar.sh` from `notchpeak-shared-short` → owned `lawson-np` (unbounded, no fairshare cost). Documented as gotcha §7.F.
4. Ask CHPC helpdesk to confirm Ember decommissioning so we can clean up stale `sacctmgr` rows. Appendix B has the open question.

## High-value context (cheap to load)

- **The new canonical:** `~/gits/brc-knowledge/scholarium/reference-base/resources/chpc-team-resource-inventory.md` — has its own ToC, jump straight to the section you need.
- **Plan from this session:** `~/.claude/plans/please-look-at-scholarium-reference-base-tender-glade.md` — full reasoning + structure rationale.
- **Memory pointer (auto-loaded):** `~/.claude/projects/-uufs-chpc-utah-edu-common-home-u0737349-gits-clyfar/memory/canonical-chpc-resource-inventory.md` — tells future sessions where the canonical lives.
- **Memory feedback:** `~/.claude/projects/.../memory/feedback-reference-doc-style.md` — captures the team-doc style preference (ToC + Q&A + plain language) that drove this design.

## Sandbox finding (answer to "is this Slurm or Claude Code?")

**It's Claude Code's sandbox, not Slurm/CHPC.** Diagnostics on notch137:

- The Bash sandbox runs inside a Linux mount + PID namespace (`/proc/1` = re-exec'd bash; `ls /proc/self/ns/mnt` ≠ host).
- `findmnt` shows `$HOME` (`/uufs/.../u0737349`) mounted **`ro`**, with specific paths bind-mounted **`rw`**: `.npm/_logs`, `.claude/debug`, and only the project cwd `gits/clyfar`. Everything else under `$HOME` (including `gits/brc-knowledge`) is read-only for Bash.
- Edit/Write tools bypass the Bash mount namespace (they write fine to brc-knowledge); `rm`, `git add`, and other Bash file ops cannot.
- Outside Claude Code, the user's regular login/interactive shell on notch137 writes to `$HOME` normally — confirmed by the existence of pre-session edits in `~/gits/clyfar` and `~/gits/brc-knowledge`. CHPC does **not** mount `$HOME` read-only on compute nodes; the sandbox does.

**To loosen for next session:** add `~/gits/brc-knowledge` to Claude Code's added directories (`/add-dir ~/gits/brc-knowledge` at session start, or persist via `~/.claude/settings.json` `additionalWorkingDirectories`). Then `rm`, `git`, etc. will work against it. Per-policy, `dangerouslyDisableSandbox` is blocked — `/add-dir` is the supported lever.
