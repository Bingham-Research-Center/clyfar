# Conda vs Pip: When to Use Which

**TL;DR:** Prefer `conda`/`mamba`, use `pip` only when necessary.

---

## When to Use Conda/Mamba (Preferred)

✅ **Use conda/mamba when package is on conda-forge:**

```bash
# Check if available
mamba search <package-name> -c conda-forge

# Install via conda
mamba install -c conda-forge <package-name>
```

**Why conda is better:**
1. **Better dependency resolution** - handles complex dependencies automatically
2. **Binary packages** - pre-compiled, faster installation
3. **Non-Python dependencies** - can install C/Fortran libraries, system tools
4. **No conflicts** - avoids pip/conda mixing issues
5. **Faster** - mamba is parallel, much faster than pip
6. **Reproducible** - environment.yml locks all dependencies

**Examples that ARE on conda-forge:**
- `synopticpy` ✅ (discovered during testing!)
- `numpy`, `pandas`, `xarray` ✅
- `cfgrib`, `cartopy`, `netcdf4` ✅

---

## When to Use Pip

❌ **Use pip ONLY when:**

1. **Package not on conda-forge**
   ```bash
   # Check first
   mamba search herbie-data -c conda-forge  # Not found
   # Then use pip
   pip install herbie-data
   ```

2. **Need bleeding-edge version** (conda lags behind PyPI by days/weeks)

3. **Pure Python package** with no binary dependencies (less critical)

**Examples that need pip:**
- `herbie-data` ❌ (not on conda-forge)
- Some very new packages ❌

---

## Best Practice: Check Before Installing

**Always search conda-forge first:**

```bash
# Template
mamba search <package> -c conda-forge

# If found: use conda
mamba install -c conda-forge <package>

# If not found: use pip
pip install <package>
```

---

## Why Mixing Can Cause Issues

**Problem:** Pip doesn't know about conda's dependency tracking

**Example:**
```bash
conda install numpy=1.26.4        # Conda installs numpy 1.26.4
pip install some-package          # Pip might upgrade numpy to 2.0!
# Now conda's dependency tracking is broken
```

**Solution:** Use conda for everything possible, pip only as last resort.

---

## Environment File Best Practices

**In `environment-chpc.yml`:**

```yaml
dependencies:
  # All conda-forge packages here
  - numpy=1.26.4
  - synopticpy>=0.4.0  # Found on conda-forge!

  # Pip-only packages at the end
  - pip:
    - herbie-data==2025.6.0  # Not on conda-forge
```

**Why this order matters:**
1. Conda installs all its packages first
2. Then pip installs remaining packages
3. Minimizes conflicts

---

## Quick Reference

| Scenario | Use | Command |
|----------|-----|---------|
| Package on conda-forge | ✅ conda/mamba | `mamba install -c conda-forge pkg` |
| Package only on PyPI | pip | `pip install pkg` |
| Has binary dependencies (C/Fortran) | ✅ conda/mamba | `mamba install -c conda-forge pkg` |
| Pure Python, small package | Either (prefer conda) | `mamba install` or `pip install` |
| Need latest version immediately | pip | `pip install pkg` |
| Production environment | ✅ conda/mamba | Lock versions in environment.yml |

---

## Troubleshooting

**If you mixed conda and pip and things broke:**

```bash
# Nuclear option: rebuild environment from scratch
conda deactivate
conda env remove -n clyfar-dec2025
bash setup-chpc.sh
```

**Check what's installed via pip vs conda:**

```bash
# List conda packages
conda list

# List pip packages
pip list
```

---

**Rule of thumb:** If in doubt, check conda-forge first. It's almost always better when available.

---

**Created:** 2025-11-24
**Lesson learned:** `synopticpy` IS on conda-forge (discovered during CHPC testing)
