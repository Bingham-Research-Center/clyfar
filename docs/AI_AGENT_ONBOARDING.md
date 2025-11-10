# AI Agent Onboarding Protocol
Date created: 2025-11-10

## Purpose
This document provides an efficient onboarding sequence for AI CLI agents (Codex, Copilot, etc.) entering this repository. Follow this protocol to minimize token usage, respect existing work, and avoid contradicting team conventions.

---

## 1. Mandatory Reading Sequence (< 2k tokens total)

### **Step 1: Read the index first** (32 lines)
```bash
cat docs/README.md
```
- This is your navigation map
- Tells you where everything is and what order to read it in
- **Do not explore randomly** or you'll waste 10x tokens

### **Step 2: Read guardrails second** (41 lines)
```bash
cat AGENTS.md
```
- Defines your operating constraints: coding style, commit format, testing approach, security patterns
- **Follow these religiously** to avoid conflicts with other agents' work
- Sets the behavioral contract for all contributors (human and AI)

### **Step 3: Read context only if needed** (selective, based on task)
Based on your specific task, read **exactly one** of these:
- **Bug fix/feature?** → `docs/project_overview.md` (88 lines, architecture context)
- **Science change?** → `docs/science-questions.md` (14 lines) + `fis/v0p9.py` (FIS rules)
- **Experiment?** → `docs/experiments/multi_version_winter.md` (41 lines)
- **Refactor planning?** → `docs/roadmap.md` (152 lines)
- **Environment setup?** → `docs/setup_conda.md` (47 lines)

---

## 2. Token-Saving Rules

### **Never read these (unless explicitly asked):**
- `notebooks/` — Exploratory work, often stale, not source of truth
- `data/` or `figures*/` — Gitignored artifacts, regenerated locally
- Binary files in `notebooks/fis_guide_figures/` — PDFs/PNGs for documentation
- `docs/ml_ideas.md` — Future brainstorming, not current actionable work
- `docs/patches_table.md` — Historical context, rarely needed

### **Use efficient commands instead:**
```bash
# See recent work (10 commits = ~200 tokens vs 5k for full history)
git log --oneline -10

# Find relevant code without reading everything
grep -r "keyword" fis/ preprocessing/ utils/ --include="*.py"

# Check what's in progress
git status --short

# See recent changes by topic
git log --since="1 week ago" --oneline --grep="elevation"
```

### **Smart file reading:**
- Use `head -50` or `tail -50` to preview files before reading entirely
- Use `wc -l` to check file size before opening
- Use `git diff` to see only what changed, not full files

---

## 3. Respecting Other Agents' Work

### **Before making changes:**
1. **Check recent commits** to see what others changed:
   ```bash
   git log --since="1 week ago" --oneline --all
   ```

2. **Read commit messages** to understand *why* changes were made:
   ```bash
   git log --oneline -20 --no-merges
   git show <commit-hash>  # For details on specific changes
   ```

3. **Look for work-in-progress markers:**
   - `# TODO: <agent-name>` — Don't delete, that's their planned work
   - `# FIXME:` — Known issue, may be addressed elsewhere
   - Staged but uncommitted changes — Check `git status`

### **Never do this:**
- ❌ Revert another agent's fix without understanding why they made it
- ❌ Refactor code that was just added (likely has context you're missing)
- ❌ Delete comments or TODOs (they signal intent to other agents)
- ❌ Change core FIS rules (`fis/v0p9.py`) without scientific justification
- ❌ Break parallel processing patterns (spawn context, locking)

### **Always do this:**
- ✅ Explain *why* in commit messages, not just *what* (helps future agents)
- ✅ Make minimal surgical changes (change only what's needed)
- ✅ Run smoke test before committing: `python run_gefs_clyfar.py -i 2024010100 -n 2 -m 2 --testing`
- ✅ Update inline docs if behavior changes
- ✅ Preserve API compatibility for versioned modules (`v0p9.py`)

---

## 4. Philosophy & Custom Instructions Alignment

All agents must align with these principles (defined in `AGENTS.md`):

### **Core Philosophy:**
1. **Minimal changes only** — Surgical edits, not rewrites
2. **Reproducibility first** — Document CLI examples, use deterministic paths
3. **Parallel-safe** — Respect `spawn` multiprocessing, avoid global state
4. **Scientific integrity** — Don't change FIS rules without domain justification
5. **Version discipline** — `v0p9.py` is baseline; maintain API compatibility

### **Coding Conventions:**
- PEP 8, 4-space indentation, type hints where practical
- Modules: `snake_case.py`, Classes: `CamelCase`, Functions/vars: `snake_case`
- Versioned modules: `vXrY` pattern (e.g., `v0p9.py`)
- Docstrings: concise, focus on public API
- Prefer pure functions in `utils/`

### **Commit Style:**
```bash
# Good
git commit -m "Fix elevation mask edge case in mountainous terrain"

# Bad (missing context)
git commit -m "Fix bug"

# Good (with body for non-trivial changes)
git commit -m "Add fasteners dependency for parallel download locking

Prevents race conditions when multiple workers download the same
GEFS member. Uses InterProcessLock in safe_get_CONUS()."
```

### **Testing:**
- No formal CI yet; use `--testing` flag for quick validation
- Smoke test: `python run_gefs_clyfar.py -i 2024010100 -n 2 -m 2 -d ./data -f ./figures --testing`
- Add pytest tests under `tests/` for new utilities
- Name test files `test_*.py`

---

## 5. High-Value vs Low-Value Information

### **High-value (read these first):**
| File | Lines | Purpose | When to read |
|------|-------|---------|--------------|
| `AGENTS.md` | 41 | Behavioral contract | Always (first read) |
| `docs/README.md` | 32 | Navigation map | Always (second read) |
| `git log -10` | ~10 | Recent changes | Every session |
| `fis/v0p9.py` | ~400 | Core scientific logic | Science changes |
| `run_gefs_clyfar.py` | ~200 | Entry point orchestration | Workflow changes |
| `docs/project_overview.md` | 88 | Architecture & theory | Bug fixes, features |

### **Medium-value (read if task-relevant):**
| File | Lines | Purpose | When to read |
|------|-------|---------|--------------|
| `docs/roadmap.md` | 152 | Refactor plan | Planning work |
| `docs/science-questions.md` | 14 | Research priorities | FIS calibration |
| `preprocessing/representative_nwp_values.py` | ~300 | Feature engineering | Data pipeline work |
| `nwp/download_funcs.py` | ~200 | GEFS acquisition | Download issues |
| `utils/geog_funcs.py` | ~100 | Spatial operations | Elevation/masking |

### **Low-value (skip unless explicitly needed):**
| Category | Why to skip |
|----------|-------------|
| `notebooks/` | Exploratory, often stale, not authoritative |
| `docs/ml_ideas.md` | Future concepts, not current implementation |
| `docs/patches_table.md` | Historical trivia, rarely actionable |
| `data/`, `figures*/` | Regenerated locally, gitignored |
| Binary assets | PDFs/PNGs for docs, no code value |

---

## 6. Efficient Workflow Examples

### **Example 1: Fix a bug in elevation smoothing**
```bash
# Entry (100 tokens)
cat docs/README.md
cat AGENTS.md

# Context (200 tokens)
git log --oneline --grep="elevation" -5  # See recent elevation work
grep -rn "smooth" utils/geog_funcs.py preprocessing/  # Find code

# Read only relevant files (500 tokens)
cat utils/geog_funcs.py

# Make minimal fix
# ... edit file ...

# Validate (don't skip!)
python run_gefs_clyfar.py -i 2024010100 -n 2 -m 2 --testing

# Commit with context
git add utils/geog_funcs.py
git commit -m "Fix elevation smoothing NaN handling at domain edges

scipy.ndimage.gaussian_filter propagates NaNs; now pre-mask
invalid cells and restore after smoothing."

# Push
git push origin main
```
**Total tokens: ~800 (vs 50k from reading everything)**

### **Example 2: Add a new FIS rule**
```bash
# Entry
cat docs/README.md
cat AGENTS.md

# Science context (300 tokens)
cat docs/science-questions.md
cat docs/project_overview.md  # Understand possibility theory

# Read current FIS (1k tokens)
cat fis/v0p9.py | grep -A 20 "FUZZY_RULES"  # See existing rules

# Make change
# ... edit fis/v0p9.py ...

# Validate
python run_gefs_clyfar.py -i 2024010100 -n 2 -m 2 --testing

# Commit with scientific justification
git commit -m "Add rule for moderate ozone under stable inversion

New rule: IF mslp is high AND wind is calm AND temp_inversion 
exists THEN ozone is moderate. Addresses observed wintertime events 
where traditional triggers (snow+solar) are absent."
```
**Total tokens: ~1,300**

### **Example 3: Refactor preprocessing module**
```bash
# Entry
cat docs/README.md
cat AGENTS.md

# Architecture context (400 tokens)
cat docs/project_overview.md  # Understand data flow
cat docs/roadmap.md | grep -A 10 "preprocessing"  # Check if planned

# Read current code (800 tokens)
cat preprocessing/representative_nwp_values.py

# Check recent changes to avoid conflicts (100 tokens)
git log --oneline preprocessing/ -10

# Make changes
# ... refactor ...

# Validate
python run_gefs_clyfar.py -i 2024010100 -n 2 -m 2 --testing

# Commit
git commit -m "Extract elevation masking to reusable utility

Moves mask_by_elevation() from representative_nwp_values to
utils/geog_funcs for reuse in postprocessing. No behavior change."
```
**Total tokens: ~1,300**

---

## 7. Emergency Protocols

### **If you're confused:**
1. **Stop** — Don't guess and make changes
2. **Read** `docs/project_overview.md` for big picture
3. **Ask** the user for clarification
4. **Check** `git log` for similar past work

### **If tests fail:**
1. **Check** if it's a pre-existing failure: `git stash && <run test> && git stash pop`
2. **Read** the test file to understand intent
3. **Only fix** if related to your changes
4. **Don't** fix unrelated failures (out of scope per `AGENTS.md`)

### **If you conflict with another agent's work:**
1. **Read** their commit message to understand intent
2. **Preserve** their fix if scientifically sound
3. **Integrate** your change alongside theirs (don't replace)
4. **Document** why both changes are needed in commit message

---

## 8. Maintenance

**Update this document when:**
- New high-value files are added to the repository
- Agent collaboration patterns change
- Token-saving strategies improve
- Philosophy/conventions evolve

**Current maintainer responsibilities:**
- Keep file line counts accurate
- Update examples when CLI changes
- Archive outdated workflow patterns
- Sync with `AGENTS.md` for consistency

---

## Quick Reference Card

```
┌─────────────────────────────────────────────────────────────┐
│ AI AGENT QUICK START                                        │
├─────────────────────────────────────────────────────────────┤
│ 1. cat docs/README.md          # Navigation map             │
│ 2. cat AGENTS.md               # Behavioral contract        │
│ 3. git log --oneline -10       # Recent work                │
│ 4. grep -r "keyword" <modules> # Find relevant code         │
│ 5. Read ONLY task-relevant docs                             │
│ 6. Make minimal changes                                     │
│ 7. Test: python run_gefs_clyfar.py ... --testing            │
│ 8. Commit with 'why', not just 'what'                       │
│ 9. Push and move on                                         │
├─────────────────────────────────────────────────────────────┤
│ NEVER: Read notebooks/, data/, or binaries unless asked     │
│ ALWAYS: Explain reasoning, preserve others' work            │
└─────────────────────────────────────────────────────────────┘
```

---

**Target token budget for typical session:** 1,000–2,000 tokens (vs 20,000+ without this protocol)
