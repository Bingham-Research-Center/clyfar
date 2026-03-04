# Git Commit Guide - Clyfar Integration

**What to commit vs keep local**

---

## ✅ SAFE TO COMMIT (No Personal Info)

### New Files - Commit These:
```bash
git add export/__init__.py
git add export/to_basinwx.py
git add .env.example                    # Template only, no secrets
git add INTEGRATION_GUIDE.md
git add test_integration.py
git add GIT_COMMIT_GUIDE.md             # This file
git add README.md                       # Updated with multi-agent note
```

### Modified Files - Review Then Commit:
```bash
# After you add integration to run_gefs_clyfar.py:
git diff run_gefs_clyfar.py             # Review changes
git add run_gefs_clyfar.py              # If clean
```

---

## ❌ NEVER COMMIT (Personal/Secrets)

### Keep Local Only:
```
.env                           # Your actual secrets - already gitignored
test_output/                   # Test files - add to .gitignore
*.pyc, __pycache__/           # Python cache - should be gitignored
.DS_Store                      # Mac system files - should be gitignored
```

### Check .gitignore Includes:
```bash
# Verify these are in .gitignore
cat .gitignore | grep -E "\.env$|test_output|__pycache__|\.pyc|\.DS_Store"
```

If missing, add:
```bash
echo "" >> .gitignore
echo "# Clyfar integration" >> .gitignore
echo ".env" >> .gitignore
echo "test_output/" >> .gitignore
echo "export/__pycache__/" >> .gitignore
```

---

## 📝 Suggested Commit Message

```bash
git commit -m "Add BasinWx website integration for Clyfar forecasts

- New export module (export/to_basinwx.py) for JSON export and upload
- Uses brc-tools package (installed via pip install -e)
- Ensemble aggregation with mean/std/min/max statistics
- Integration guide and test suite included
- Environment variables via .env (template provided)
- Multi-agent development notes added to README

Integration with run_gefs_clyfar.py pending (see INTEGRATION_GUIDE.md)

Co-developed with Claude Code for multi-agent environment support."
```

---

## 🔍 Pre-Commit Checklist

Before `git add` or `git commit`, verify:

- [ ] No API keys in committed files: `git diff | grep -i "api.*key"`
- [ ] No personal paths: `git diff | grep -i "/Users/johnlawson"`
- [ ] No hardcoded hostnames: `git diff | grep -i "\.local\|localhost"`
- [ ] .env not staged: `git status | grep "\.env$"` (should show nothing or "ignored")
- [ ] .env.example has placeholders only: `cat .env.example | grep -v "your-.*-here"`

---

## 🚀 For CHPC Deployment (After Commit)

On CHPC, after `git pull`:

```bash
# 1. Install brc-tools (not in git)
conda activate clyfar
pip install -e ~/brc-tools

# 2. Create .env with production secrets (not in git)
cp .env.example .env
vim .env  # Fill in real keys

# OR use shell environment (recommended for servers)
echo "export DATA_UPLOAD_API_KEY='production-key'" >> ~/.bashrc_basinwx
source ~/.bashrc_basinwx
```

No code changes needed between local and CHPC!

---

## 👥 For Team Members

After `git pull`:

```bash
# 1. Copy environment template
cp .env.example .env

# 2. Get API keys from team lead (via secure channel)
# Fill into .env file

# 3. Install brc-tools (coordinate with team for location)
conda activate clyfar-2025
pip install -e /path/to/brc-tools  # Team-specific path

# 4. Test setup
python test_integration.py
```

---

## 🤖 For AI Agents (Codex, Claude, etc.)

If integrating this code:
1. Import from `export.to_basinwx` (already committed)
2. Don't modify brc-tools import paths (use as-is)
3. Environment variables via `load_dotenv()` (already in code)
4. See `INTEGRATION_GUIDE.md` for step-by-step integration into `run_gefs_clyfar.py`

All hardcoded paths removed - integration is environment-agnostic.

---

## 📦 Package Dependencies

**Already in requirements.txt:**
- pandas, numpy, etc. (from existing Clyfar deps)

**New dependency (add to requirements.txt):**
```bash
echo "python-dotenv>=1.0.0" >> requirements.txt
```

**External package (not in requirements.txt - installed separately):**
- brc-tools (via `pip install -e /path/to/brc-tools`)

---

## 🔄 Cross-Repo Coordination

**Related commits in other repos:**

**ubair-website repo:**
- CHPC-IMPLEMENTATION.md (deployment guide)
- PYTHON-PACKAGING-DEPLOYMENT.md (packaging guide)
- Updated cron templates
- Standardized DATA_UPLOAD_API_KEY

**brc-tools repo:**
- README.md updated with deployment section
- (No code changes needed - already has upload functionality)

**Coordination:** Share these commit SHAs in team chat or issue tracker.

---

## ⚠️ Common Mistakes to Avoid

1. **Committing .env** - Already gitignored, but double-check
2. **Committing test_output/** - Add to .gitignore
3. **Hardcoded paths in code** - Use relative paths or env vars
4. **Personal info in JSON** - Test suite checks this
5. **API keys in commit messages** - Don't paste keys in commit descriptions

---

**Ready to commit?** Run checklist above, then proceed!
