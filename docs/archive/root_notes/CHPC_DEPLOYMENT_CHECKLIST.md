# CHPC Deployment Checklist - Clyfar v0.9.5

**Goal**: Deploy and test Clyfar→BasinWx integration on CHPC compute nodes

## Pre-Deployment: Local → CHPC Transfer

### 1. SSH to CHPC
```bash
ssh <username>@notchpeak.chpc.utah.edu
# Or your specific login node
```

### 2. Clone/Update Repositories
```bash
# If first time:
cd ~
git clone https://github.com/Bingham-Research-Center/clyfar.git
git clone https://github.com/Bingham-Research-Center/brc-tools.git

# If updating:
cd ~/clyfar
git fetch origin
git checkout integration-clyfar-v0.9.5
git pull

cd ~/brc-tools
git fetch origin
git checkout integration-clyfar-v0.9.5
git pull
```

### 3. Setup Conda Environment
```bash
# Load conda
module load miniconda3

# Create environment (if not exists)
conda create -n clyfar-2025 python=3.11 -y
conda activate clyfar-2025

# Install dependencies
cd ~/clyfar
pip install -r requirements.txt  # If exists
pip install pandas numpy xarray herbie-data scikit-fuzzy

# Install brc-tools (editable)
pip install -e ~/brc-tools
```

### 4. Setup Environment Variables
```bash
# Create environment file
cat > ~/.bashrc_basinwx << 'EOF'
# BasinWx Environment Variables
export DATA_UPLOAD_API_KEY='YOUR_API_KEY_HERE'
export BASINWX_API_URL='https://basinwx.com'
export SYNOPTIC_API_TOKEN='YOUR_SYNOPTIC_TOKEN'  # If needed

# Add to PATH if needed
export PATH="$HOME/clyfar/scripts:$PATH"
EOF

# Load it
source ~/.bashrc_basinwx

# Add to .bashrc for persistence
echo "source ~/.bashrc_basinwx" >> ~/.bashrc
```

**⚠️ SECURITY**: Never commit ~/.bashrc_basinwx to git!

### 5. Create Log Directories
```bash
mkdir -p ~/logs/basinwx
mkdir -p ~/basinwx-data/clyfar/{figures,basinwx_export}
```

### 6. Test Python Environment
```bash
cd ~/clyfar
conda activate clyfar-2025

# Run integration test (local, no GEFS data)
python test_integration.py
```

**Expected**: All tests should pass (same as local)

## Phase 1: Manual Test Run (Interactive)

### 1. Request Interactive Node

**Option A: Use your owner node (recommended for testing/debugging)**
```bash
salloc \
  --account=lawson-np \
  --partition=lawson-np \
  --nodes=1 \
  --ntasks=1 \
  --cpus-per-task=8 \
  --mem=32G \
  --time=02:00:00
```

**Option B: Use shared partition (must be efficient with CPU usage)**
```bash
salloc \
  --account=notchpeak-shared-short \
  --partition=notchpeak-shared-short \
  --nodes=1 \
  --ntasks=1 \
  --cpus-per-task=4 \
  --mem=8G \
  --time=01:00:00
```

**Note:** For debugging/testing, use **lawson-np** (no complaints about idle time).

### 2. Activate Environment
```bash
module load miniconda3
conda activate clyfar-2025
source ~/.bashrc_basinwx
cd ~/clyfar
```

### 3. Test GEFS Data Download (Herbie)
```bash
# Test if GEFS data is accessible
python -c "
from herbie import Herbie
import datetime as dt

# Try to get latest GEFS data
H = Herbie(
    dt.datetime.utcnow() - dt.timedelta(hours=6),
    model='gefs',
    product='pgrb2a',
    member=0,
    fxx=0
)
print('GEFS data accessible:', H.inventory())
"
```

**Expected**: Should list GEFS variables without error

### 4. Run Clyfar with Recent GEFS Cycle
```bash
# Use a recent cycle (e.g., today's 00Z run)
# Format: YYYYMMDDHH
INIT_TIME=$(date -u -d "6 hours ago" +%Y%m%d%H)
echo "Testing with init time: $INIT_TIME"

# Run Clyfar (small test - 3 members, no save)
python run_gefs_clyfar.py \
  --dt $INIT_TIME \
  --clyfar_data_root ~/basinwx-data/clyfar \
  --clyfar_fig_root ~/basinwx-data/clyfar/figures \
  --ncpus 4 \
  --nmembers 3 \
  --no-save \
  --no-visualise \
  --log_fis
```

**Expected**:
- Downloads GEFS data
- Runs Clyfar inference
- Prints FIS diagnostics
- No errors

**⏱️ Time**: ~10-20 minutes for 3 members

### 5. Test Export Module (No Upload)
```bash
python << 'EOF'
import os
import sys
from datetime import datetime
from pathlib import Path
import pandas as pd

# Mock daily max data (since we ran with --no-save above)
# In production, this will be loaded from parquet files
dates = pd.date_range('2025-01-15', periods=5, freq='D')

dailymax_df_dict = {}
for i in range(3):
    member = f"clyfar{i:03d}"
    df = pd.DataFrame({
        'background': [0.7, 0.6, 0.5, 0.4, 0.3],
        'moderate': [0.2, 0.3, 0.4, 0.4, 0.4],
        'elevated': [0.1, 0.1, 0.1, 0.2, 0.3],
        'extreme': [0.0, 0.0, 0.0, 0.0, 0.0],
        'ozone_10pc': [35, 40, 45, 50, 55],
        'ozone_50pc': [40, 45, 50, 55, 60],
        'ozone_90pc': [45, 50, 55, 60, 65]
    }, index=dates)
    dailymax_df_dict[member] = df

# Test export (upload=False)
from export.to_basinwx import export_all_products

results = export_all_products(
    dailymax_df_dict=dailymax_df_dict,
    init_dt=datetime(2025, 1, 15, 12, 0),
    output_dir='./test_export',
    upload=False  # Don't upload yet
)

print(f"✓ Generated {len(results['possibility']) + len(results['exceedance']) + len(results['percentiles'])} files")
EOF
```

**Expected**: Creates test_export/ directory with JSON files

### 6. Verify JSON Files
```bash
ls -lh test_export/
head -20 test_export/forecast_possibility_heatmap_clyfar000_*.json
```

### 7. Exit Interactive Session
```bash
exit  # Exit salloc
```

## Phase 2: Slurm Batch Job Test

### 1. Review Slurm Script
```bash
cat ~/clyfar/scripts/submit_clyfar.sh
```

**Check**:
- Account name matches your allocation
- Paths are correct
- Email notifications (optional)

### 2. Submit Test Job (3 Members)
```bash
# Edit script to use nmembers=3 for testing
cd ~/clyfar
sbatch scripts/submit_clyfar.sh $(date -u -d "6 hours ago" +%Y%m%d%H)
```

**Note job ID**: `Submitted batch job 12345678`

### 3. Monitor Job
```bash
# Check queue
squeue -u $USER

# Watch output (live)
tail -f ~/logs/basinwx/clyfar_12345678.out

# Check for errors
tail -f ~/logs/basinwx/clyfar_12345678.err
```

### 4. Verify Completion
```bash
# Check job status
sacct -j 12345678 --format=JobID,JobName,Elapsed,State,ExitCode

# Should show:
# State: COMPLETED
# ExitCode: 0:0
```

### 5. Verify Output Files
```bash
# Check exported JSON files
ls -lh ~/basinwx-data/clyfar/basinwx_export/
# Should have 63 files (or fewer if testing with 3 members)

# Check one file
head -50 ~/basinwx-data/clyfar/basinwx_export/forecast_possibility_heatmap_clyfar000_*.json
```

## Phase 3: Test Upload to Website

### 1. Verify Environment Variables
```bash
echo "API Key set: ${DATA_UPLOAD_API_KEY:0:8}..."
echo "API URL: $BASINWX_API_URL"
```

### 2. Test Single File Upload
```bash
cd ~/clyfar
python << EOF
import os
import json
from brc_tools.download.push_data import send_json_to_server

# Pick one file to test
test_file = '~/basinwx-data/clyfar/basinwx_export/forecast_exceedance_probabilities_*.json'

with open(test_file, 'r') as f:
    data = json.load(f)

send_json_to_server(
    server_address=os.getenv('BASINWX_API_URL'),
    fpath=test_file,
    file_data=data,
    API_KEY=os.getenv('DATA_UPLOAD_API_KEY')
)
print("✓ Upload successful")
EOF
```

**Expected**: No errors, server returns 200 OK

### 3. Test Full Export with Upload
```bash
# Run with upload=True
sbatch scripts/submit_clyfar.sh $(date -u -d "6 hours ago" +%Y%m%d%H)

# Monitor job
tail -f ~/logs/basinwx/clyfar_*.out | grep -i upload
```

**Expected**: Sees "Successfully exported 63 forecast files" and upload messages

## Phase 4: Production Deployment

### 1. Setup Cron (4× Daily)
```bash
crontab -e
```

Add:
```cron
# Clyfar forecasts - 4× daily at 03:30, 09:30, 15:30, 21:30 UTC
30 3,9,15,21 * * * source ~/.bashrc && cd ~/clyfar && sbatch ~/clyfar/scripts/submit_clyfar.sh >> ~/logs/basinwx/cron.log 2>&1
```

### 2. Test Cron (Optional)
```bash
# Trigger manually to test cron setup
cd ~/clyfar && sbatch ~/clyfar/scripts/submit_clyfar.sh >> ~/logs/basinwx/cron.log 2>&1

# Check log
tail ~/logs/basinwx/cron.log
```

### 3. Monitor First Automated Run
```bash
# Wait for next scheduled time (03:30, 09:30, 15:30, or 21:30 UTC)
# Check cron log
tail -f ~/logs/basinwx/cron.log

# Check Slurm queue
watch -n 30 'squeue -u $USER'
```

## Verification & Monitoring

### Daily Checks (First Week)
```bash
# Check job history
sacct -u $USER -S $(date -d "1 day ago" +%Y-%m-%d) --format=JobID,JobName,Elapsed,State,ExitCode

# Check logs for errors
grep -i error ~/logs/basinwx/clyfar_*.err

# Verify uploads
ls -lt ~/basinwx-data/clyfar/basinwx_export/ | head -20

# Check website for new forecasts
curl https://basinwx.com/api/static/ | grep forecast
```

### Performance Optimization
After 1 week, review:
```bash
# Average job time
sacct -u $USER --format=JobName,Elapsed -X | grep clyfar

# Resource usage
sacct -u $USER --format=JobID,MaxRSS,MaxVMSize,CPUTime -X | grep clyfar
```

**Optimize**: Adjust `--cpus-per-task` and `--mem` based on actual usage

## Troubleshooting

### Job Failed
```bash
# Check exit code
sacct -j <JOBID> --format=State,ExitCode

# Check error log
cat ~/logs/basinwx/clyfar_<JOBID>.err

# Common issues:
# - GEFS data not available yet (wait 30 min)
# - API key not set (check ~/.bashrc_basinwx)
# - Network issue (retry)
```

### Upload Failed
```bash
# Check API connectivity from compute node
curl -I https://basinwx.com

# Check logs for HTTP errors
grep -A5 "Upload failed" ~/logs/basinwx/clyfar_*.out
```

### Out of Quota
```bash
# Check quota
quota -s

# Clean old files
find ~/basinwx-data/clyfar -type f -mtime +30 -delete
```

## Success Criteria

- [x] Interactive job runs without errors
- [x] Batch job completes (ExitCode 0:0)
- [x] 63 JSON files generated
- [x] Files upload to website successfully
- [x] Cron job triggers automatically
- [x] 4× daily runs complete successfully for 3 days
- [x] Website displays forecast data

---

**Once stable**: Update PR #12 with production metrics and merge to main!
