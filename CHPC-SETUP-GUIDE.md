# CHPC Production Environment Setup

**One-command deployment for Clyfar v0.9.5**

## Quick Start (TL;DR)

```bash
# SSH to CHPC
ssh <username>@notchpeak.chpc.utah.edu

# Clone/update repo
cd ~/gits
git clone https://github.com/Bingham-Research-Center/clyfar.git  # If first time
cd clyfar
git fetch origin
git checkout integration-clyfar-v0.9.5
git pull

# Run automated setup
bash setup-chpc.sh

# Edit API keys
nano .env

# Activate environment
source ~/.config/clyfar/activate.sh

# Test
python scripts/check_mslp.py -i 2025112300 -m p01 -f 0 6 12
```

**That's it!** The script handles everything.

---

## What the Setup Script Does

1. ✅ Loads miniforge3 module
2. ✅ Removes old environment (if exists)
3. ✅ Creates `clyfar-dec2025` conda environment with **stable, locked versions**
4. ✅ Installs brc-tools (editable mode)
5. ✅ Configures environment variables
6. ✅ Creates activation script (`~/.config/clyfar/activate.sh`)
7. ✅ Verifies installation
8. ✅ Adds quick-start alias to `.bashrc`

**Time:** ~5-10 minutes (conda install is slow)

---

## Stable Version Lock

**Why locked versions?**
- Bleeding-edge packages (numpy 2.x, xarray 2024.11) have compatibility issues
- Stable versions (6-12 months old) are battle-tested
- Reproducible environment across dev/staging/prod

**Locked versions (in `environment-chpc.yml`):**
- **Python:** 3.11.10
- **numpy:** 1.26.4 (pre-2.0, stable - avoiding 2.x breaking changes)
- **pandas:** 2.2.3 (stable 2025 release)
- **xarray:** 2024.10.0 (modern - was 2023.12, too old!)
- **herbie-data:** 2025.6.0 (mid-2025 release - was 2024.3, 20 months old!)
- **cfgrib:** 0.9.15.0
- **polars:** 1.12.0 (1.x series stable by 2025)

---

## Daily Usage

### First time each session:

```bash
# Activate environment
source ~/.config/clyfar/activate.sh
# Or use alias:
clyfar-activate
```

This auto-loads:
- Miniforge module
- Conda environment (clyfar-dec2025)
- Environment variables (PYTHONPATH, POLARS_ALLOW_FORKING_THREAD)
- API keys from `.env`

### Request compute node:

```bash
# For debugging/testing (owner node - no restrictions)
salloc \
  --account=lawson-np \
  --partition=lawson-np \
  --cpus-per-task=8 \
  --mem=32G \
  --time=02:00:00

# Once on compute node, reactivate:
clyfar-activate
```

### Run Clyfar:

```bash
# Test with 3 members
python ~/gits/clyfar/run_gefs_clyfar.py \
  -i "2025112300" \
  -n "8" \
  -m "3" \
  -d "/scratch/general/vast/clyfar_test/v0p9/2025112300" \
  -f "/scratch/general/vast/clyfar_test/figs/2025112300"

# Production (all 30 members)
python ~/gits/clyfar/run_gefs_clyfar.py \
  -i "$(date -u +%Y%m%d%H)" \
  -n "16" \
  -m "all" \
  -d "/scratch/general/vast/clyfar/v0p9/$(date -u +%Y%m%d%H)" \
  -f "/scratch/general/vast/clyfar/figs/$(date -u +%Y%m%d%H)"
```

---

## Troubleshooting

### Environment not activating?

```bash
# Manual activation
module use "$HOME/MyModules"
module load miniforge3/latest
source "$HOME/software/pkg/miniforge3/bin/activate"
conda activate clyfar-dec2025
export PYTHONPATH="$PYTHONPATH:$HOME/gits/clyfar"
export POLARS_ALLOW_FORKING_THREAD=1
```

### Verify versions:

```bash
python -c "
import numpy, pandas, xarray, herbie
print(f'numpy: {numpy.__version__}')    # Should be 1.26.4
print(f'pandas: {pandas.__version__}')   # Should be 2.2.3
print(f'xarray: {xarray.__version__}')   # Should be 2024.10.0
print(f'herbie: {herbie.__version__}')   # Should be 2025.6.0
"
```

### Rebuild environment:

```bash
# Just re-run the setup script
cd ~/gits/clyfar
bash setup-chpc.sh
```

### Check API keys:

```bash
# View (sanitized)
echo "API_KEY: ${DATA_UPLOAD_API_KEY:0:8}..."
```

---

## Deployment Workflow

**Branches:**
- `integration-clyfar-v0.9.5` → testing on CHPC
- `dev` → beta testing
- `ops` → production (4× daily cron)
- `main` → stable release

**Process:**
1. Test on `integration-clyfar-v0.9.5` with 3 members
2. If successful, merge to `dev`
3. Test full 30-member run on `dev`
4. If stable, merge to `ops`
5. Deploy cron on `ops` branch
6. After 1 week stable, merge to `main`

---

## File Locations

**Environment:**
- Conda env: `~/software/pkg/miniforge3/envs/clyfar-dec2025/`
- Activation script: `~/.config/clyfar/activate.sh`
- Environment spec: `~/gits/clyfar/environment-chpc.yml`

**Data:**
- Herbie cache: `~/gits/clyfar/data/herbie_cache/`
- Scratch output: `/scratch/general/vast/clyfar_test/`
- Production output: `/scratch/general/vast/clyfar/`

**Logs:**
- Slurm logs: `~/logs/basinwx/`
- Application logs: `~/gits/clyfar/logs/`

---

## Updating Dependencies

**To update to newer (still stable) versions:**

1. Edit `environment-chpc.yml`
2. Update version pins (test compatibility first!)
3. Commit changes
4. Re-run `bash setup-chpc.sh`

**Never blindly upgrade to latest versions** - test locally first, then CHPC.

---

## Support

**Issues?**
1. Check this guide first
2. Check `CHPC-SYSTEM-INFO.md` for system details
3. Check `CHPC_DEPLOYMENT_CHECKLIST.md` for step-by-step testing
4. Contact: [Your contact info]

---

**Last Updated:** 2025-11-24
**Environment:** clyfar-dec2025 (stable)
**Tested On:** CHPC notchpeak (Rocky Linux 8.10)
