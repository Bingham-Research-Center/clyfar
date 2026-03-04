# Clyfar → BasinWx Website Integration Guide

> **Multi-Agent Development Note:**
> This document was created collaboratively by John Lawson and Claude Code to support a multi-agent development environment. We encourage RAs and team members to use different AI assistants (Claude, Codex, Cursor, etc.) as needed. Cross-repo coordination happens through shared documentation and clean package boundaries.
>
> **For AI Agents:** This repo (clyfar) imports from brc-tools (separate repo) via proper Python packaging. See PYTHON-PACKAGING-DEPLOYMENT.md in ubair-website for architecture details.

**Status:** Ready to integrate
**Created:** 2025-11-22
**Authors:** John Lawson + Claude Code

---

## What Was Set Up

1. ✅ brc-tools installed in clyfar-2025 conda env (editable mode)
2. ✅ `.env` files configured with API keys
3. ✅ Export module created: `export/to_basinwx.py`
4. ✅ Clean imports (no hardcoded paths!)

---

## How to Use in run_gefs_clyfar.py

### Step 1: Add Import

**At the top of `run_gefs_clyfar.py`** (around line 50, with other imports):

```python
from export.to_basinwx import export_and_upload
```

### Step 2: Load Environment Variables

**At the top of `run_gefs_clyfar.py`** (before other code, around line 60):

```python
from dotenv import load_dotenv
load_dotenv()  # Loads DATA_UPLOAD_API_KEY from .env
```

### Step 3: Add Upload After Clyfar Inference

**In the `main()` function**, find where Clyfar saves results (around line 762):

```python
# EXISTING CODE (around line 762):
if save:
    subdir = clyfar_data_root
    utils.try_create(subdir)
    for clyfar_member, df in clyfar_df_dict.items():
        df.to_parquet(os.path.join(
            subdir, f"{clyfar_member}_df.parquet"))
    dailymax_dir = os.path.join(subdir, "dailymax")
    utils.try_create(dailymax_dir)
    for clyfar_member, df in dailymax_df_dict.items():
        df.to_parquet(os.path.join(
            dailymax_dir, f"{clyfar_member}_dailymax.parquet"))
    print("Saved Clyfar dataframes to ", subdir)
    print("Saved daily-max ozone tables to ", dailymax_dir)

    # NEW CODE - ADD AFTER THE ABOVE:
    # Upload to website
    print("\nUploading Clyfar forecast to BasinWx website...")
    json_path, upload_success = export_and_upload(
        clyfar_df_dict=clyfar_df_dict,
        dailymax_df_dict=dailymax_df_dict,
        init_dt=init_dt_dict['naive'],
        output_dir=subdir,
        upload=True  # Set to False to skip upload during testing
    )

    if upload_success:
        print(f"✓ Forecast uploaded successfully")
    else:
        print(f"✗ Upload failed (JSON saved locally at {json_path})")
```

### Step 4: Add Command-Line Flag (Optional)

**In argument parser** (around line 840):

```python
# EXISTING CODE:
parser.add_argument('--no-clyfar', action='store_true',
                    help='Skip Clyfar inference')

# NEW CODE - ADD:
parser.add_argument('--no-upload', action='store_true',
                    help='Skip website upload (save JSON locally only)')
```

**In main() call** (around line 905):

```python
# EXISTING CODE:
main(dt, clyfar_fig_root=args.fig_root, clyfar_data_root=args.data_root,
     ncpus=args.ncpus, nmembers=args.nmembers,
     visualise=True, save=True,
     verbose=args.verbose, testing=args.testing,
     no_clyfar=args.no_clyfar, no_gefs=args.no_gefs,
     log_fis=args.log_fis)

# MODIFY THE ABOVE to pass upload flag:
main(dt, clyfar_fig_root=args.fig_root, clyfar_data_root=args.data_root,
     ncpus=args.ncpus, nmembers=args.nmembers,
     visualise=True, save=True,
     verbose=args.verbose, testing=args.testing,
     no_clyfar=args.no_clyfar, no_gefs=args.no_gefs,
     log_fis=args.log_fis, no_upload=args.no_upload)  # NEW
```

**In main() signature** (around line 625):

```python
# EXISTING:
def main(dt, clyfar_fig_root, clyfar_data_root,
         maxhr='all', ncpus='auto', nmembers=None, visualise=True,
         save=True, verbose=False, testing=False, no_clyfar=False,
         no_gefs=False, log_fis=False):

# MODIFY TO:
def main(dt, clyfar_fig_root, clyfar_data_root,
         maxhr='all', ncpus='auto', nmembers=None, visualise=True,
         save=True, verbose=False, testing=False, no_clyfar=False,
         no_gefs=False, log_fis=False, no_upload=False):  # NEW
```

**Then use the flag** (in the upload code from Step 3):

```python
json_path, upload_success = export_and_upload(
    clyfar_df_dict=clyfar_df_dict,
    dailymax_df_dict=dailymax_df_dict,
    init_dt=init_dt_dict['naive'],
    output_dir=subdir,
    upload=not no_upload  # Skip upload if --no-upload flag set
)
```

---

## Testing Locally

### Test 1: Module Import

```bash
conda activate clyfar-2025
cd ~/PycharmProjects/clyfar
python -c "from export.to_basinwx import export_and_upload; print('OK')"
```

### Test 2: Environment Variables

```bash
conda activate clyfar-2025
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('API Key set:', bool(os.environ.get('DATA_UPLOAD_API_KEY')))"
```

### Test 3: Run Clyfar Without Upload

```bash
conda activate clyfar-2025
python run_gefs_clyfar.py -i 2024010100 -n 2 -m 2 --testing --no-upload
```

Should:
- Run Clyfar inference
- Generate JSON file in `./data/clyfar_output/`
- NOT upload to website

### Test 4: Manual Upload of JSON

```bash
conda activate clyfar-2025
python export/to_basinwx.py ./data/clyfar_output/clyfar_forecast_YYYYMMDD_HHMMZ.json
```

Should:
- Upload existing JSON to website
- Print success/failure message

### Test 5: Full Pipeline With Upload

```bash
conda activate clyfar-2025
python run_gefs_clyfar.py -i 2024010100 -n 2 -m 2 --testing
# (without --no-upload, should upload automatically)
```

---

## CHPC Deployment

### Setup on CHPC

```bash
# SSH to CHPC
ssh username@chpc.utah.edu

# Set up conda environment
conda create -n clyfar python=3.11
conda activate clyfar
cd ~/clyfar
pip install -r requirements.txt

# Install brc-tools in editable mode
pip install -e ~/brc-tools

# Test import
python -c "from export.to_basinwx import export_and_upload; print('OK')"

# Set environment variables (don't use .env on server)
echo "export DATA_UPLOAD_API_KEY='your-key'" >> ~/.bashrc_basinwx
echo "export SYNOPTIC_API_TOKEN='your-token'" >> ~/.bashrc_basinwx
source ~/.bashrc_basinwx

# Verify
echo $DATA_UPLOAD_API_KEY
```

### Cron Setup

**From ubair-website repo**, use the cron template at:
`ubair-website/chpc-deployment/cron_templates/crontab_full.txt`

Clyfar cron entry (twice daily, 6am and 6pm Mountain Time):

```cron
0 6,18 * * * source ~/.bashrc && cd ~/clyfar && ~/clyfar/venv/bin/python3 ~/clyfar/run_gefs_clyfar.py >> ~/logs/basinwx/clyfar.log 2>&1
```

**Note:** Uncomment this line in crontab_full.txt once integration is tested.

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'export'"

**Cause:** Running from wrong directory or Python path issue.

**Solution:**
```bash
cd ~/PycharmProjects/clyfar  # Must be in clyfar root
python run_gefs_clyfar.py ...
```

### "ModuleNotFoundError: No module named 'brc_tools'"

**Cause:** brc-tools not installed in current conda env.

**Solution:**
```bash
conda activate clyfar-2025
pip install -e ~/PycharmProjects/brc-tools
```

### "DATA_UPLOAD_API_KEY not set"

**Cause:** Environment variable not loaded.

**Solution (local):**
```bash
# Check .env exists
ls ~/PycharmProjects/clyfar/.env

# Load manually
conda activate clyfar-2025
python -c "from dotenv import load_dotenv; load_dotenv(); import os; print(os.environ.get('DATA_UPLOAD_API_KEY'))"
```

**Solution (CHPC):**
```bash
# Check bashrc
grep DATA_UPLOAD_API_KEY ~/.bashrc_basinwx
source ~/.bashrc_basinwx
echo $DATA_UPLOAD_API_KEY
```

### Upload Fails with 401/403 Error

**Cause:** API key invalid or hostname not CHPC.

**Check:**
1. Verify API key matches website configuration
2. On CHPC, verify hostname: `hostname` should show `*.chpc.utah.edu`
3. Test health endpoint: `curl https://basinwx.com/api/health`

### JSON Saved But Not Uploaded

**Check logs:**
```bash
# Look for error messages
grep -i "upload" ~/logs/basinwx/clyfar.log | tail -20
```

**Common causes:**
- Network connectivity (firewall, VPN)
- Website down (check basinwx.com)
- API endpoint not accepting 'forecasts' data type yet

---

## Next Steps After Integration

1. **Test locally** - Run with --no-upload first
2. **Test manual upload** - Use CLI to upload JSON file
3. **Test full pipeline** - Run without --no-upload
4. **Verify on website** - Check if forecast appears (need frontend support)
5. **Deploy to CHPC** - Follow CHPC setup steps above
6. **Monitor logs** - Check ~/logs/basinwx/clyfar.log for issues
7. **Update schema** - Add forecast format to DATA_MANIFEST.json (next todo)

---

## Schema Documentation

The JSON format exported by `export/to_basinwx.py` needs to be added to:
- `ubair-website/DATA_MANIFEST.json` (for validation)
- `ubair-website/docs/DATA-SCHEMA.md` (for documentation)

See next todo: "Define Clyfar forecast schema in DATA_MANIFEST.json"

---

## Notes for Tech Report

**For Clyfar v0.9.5 technical report:**

- Package: brc-tools v0.1.0 (editable install)
- Integration: export/to_basinwx.py (2025-11-22)
- Upload method: Secure POST to basinwx.com/api/upload/forecasts
- Authentication: API key via DATA_UPLOAD_API_KEY
- Format: JSON with ensemble statistics (mean, std, min, max)
- Frequency: Twice daily (6am, 6pm MT) via cron
- Logging: ~/logs/basinwx/clyfar.log

Git tag suggestion:
```bash
cd ~/PycharmProjects/brc-tools
git tag v0.1.0-clyfar-integration -m "Version used for Clyfar v0.9.5 website integration"
git push origin v0.1.0-clyfar-integration
```

---

## Files Modified/Created

**New files:**
- `clyfar/export/__init__.py`
- `clyfar/export/to_basinwx.py`
- `clyfar/.env.example`
- `clyfar/.env` (copied from brc-tools)
- `clyfar/INTEGRATION_GUIDE.md` (this file)

**To modify:**
- `clyfar/run_gefs_clyfar.py` (add import, load_dotenv, upload call)

**Dependencies installed:**
- brc-tools==0.1.0 (editable, in clyfar-2025 conda env)

**Configuration:**
- `.env` file with DATA_UPLOAD_API_KEY
- `~/.config/ubair-website/website_url` (optional, defaults to basinwx.com)

---

**Ready to integrate!** Follow Steps 1-4 above to add to run_gefs_clyfar.py.
