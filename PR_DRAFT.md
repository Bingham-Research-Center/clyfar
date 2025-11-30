# PR: Clyfar v0.9.5 BasinWx Integration - Ready for CHPC Deployment

## Overview
Integrates Clyfar v0.9.5 ozone forecasts with BasinWx website, preparing for **automated 4×daily CHPC production runs**.

## What's New

### Export Module (3 Data Products, 63 Files Per Run)
- **`export/to_basinwx.py`**: Complete export pipeline
  - Possibility heatmaps (31 files): Per-member 4×N grids
  - Exceedance probabilities (1 file): Ensemble consensus
  - Percentile scenarios (31 files): Defuzzified ppb values
- **4 ozone categories**: background, moderate, elevated, extreme ✓
- Uploads via brc-tools to `POST /api/upload/forecasts`

### CHPC Automation
- **`scripts/submit_clyfar.sh`**: Slurm submission script
  - Auto-detects GEFS cycle or accepts manual init time
  - Runs on compute nodes (16 CPUs, 32GB RAM, 2hr limit)
  - Exports + uploads all 63 files automatically
- **Schedule**: 4× daily at 03:30, 09:30, 15:30, 21:30 UTC
  - Aligned with GEFS runs (00Z, 06Z, 12Z, 18Z) + 3.5hr latency buffer

### Testing & Documentation
- **`test_integration.py`**: Full test suite (ALL TESTS PASSING ✓)
- **`INTEGRATION_GUIDE.md`**: Step-by-step implementation guide
- **`GIT_COMMIT_GUIDE.md`**: Safe commit procedures (no secrets)
- **`CONTRADICTIONS-REPORT.md`**: Tech report alignment review
  - ⚠️ Found MSLP unit mismatch (Pa vs hPa) - needs resolution
- **`CROSS-REPO-SYNC.md`**: Multi-agent coordination protocol

### Environment & Packaging
- **`.env.example`**: Template for required env vars
- **`.gitignore`**: Protected .env, test outputs
- **README**: Multi-agent development notes

## Testing Status

### Local Tests ✓
```bash
$ python test_integration.py
ALL TESTS PASSED ✓
- 4 categories correct
- 63 JSON files generated
- All schemas valid
- No personal info leaked
```

### Integration Points
- ✓ brc-tools package import (editable install)
- ✓ Environment variables loaded
- ✓ JSON export working
- ⚠️ Upload tested with mock data (not real API yet)

## Deployment Plan (CHPC)

### Pre-Deployment Checklist
- [ ] Verify CHPC specs (see `ubair-website/DEPLOYMENT-SPECS-TODO.md`)
  - [ ] Slurm partition limits
  - [ ] Storage quotas
  - [ ] Network bandwidth to Akamai
- [ ] Test ONE forecast cycle in staging
- [ ] Measure upload time for 63 files
- [ ] Optimize based on measurements

### Deployment Steps
1. **Clone repos on CHPC**: `~/clyfar`, `~/brc-tools`
2. **Install packages**: `pip install -e ~/brc-tools` in clyfar env
3. **Set environment**: Add to `~/.bashrc_basinwx`
   ```bash
   export DATA_UPLOAD_API_KEY='...'
   export BASINWX_API_URL='https://basinwx.com'
   ```
4. **Test manually**: `sbatch scripts/submit_clyfar.sh 2025011512`
5. **Enable cron**: `30 3,9,15,21 * * * sbatch ~/clyfar/scripts/submit_clyfar.sh`

### Monitoring
- Check logs: `~/logs/basinwx/clyfar_*.{out,err}`
- View job: `sacct -j <JOBID> --format=JobID,Elapsed,State,ExitCode`
- Verify uploads: Check website `/api/static/` for new files

## Cross-Repo Coordination

This PR is part of **3-repo integration**:
- **clyfar** (this repo): Export module + Slurm script
- **ubair-website**: Forecast schema (v1.1.0) + analytics middleware
- **brc-tools**: Cross-repo documentation

All PRs use branch: `integration-clyfar-v0.9.5`

## Known Issues

1. **MSLP unit mismatch** (tech report vs code): Pa vs hPa - 100× difference
   - See `CONTRADICTIONS-REPORT.md`
   - Does not affect current deployment (code is correct)
   - Tech report needs update

2. **CHPC specs unknown**: Need to verify before production
   - Slurm resource limits
   - Upload bandwidth
   - See `DEPLOYMENT-SPECS-TODO.md`

## Breaking Changes
None - this is a new feature (exports were not previously operational)

## Migration Notes
N/A - fresh deployment

## Post-Merge Actions
1. Deploy to CHPC staging environment
2. Run test forecast cycle
3. Measure and optimize
4. Update CHPC docs with actual measurements
5. Enable production cron

## Questions for Reviewers
1. Should we batch uploads (1 tarball) or sequential (63 POSTs)?
2. Approve Slurm resource allocation (16 CPUs, 32GB)?
3. Any security concerns with API uploads?

---

**Related Issues**: N/A (new feature)
**Documentation**: All guides included in PR
**Tests**: ✓ Passing (see test_integration.py output)

**Ready for CHPC deployment after review and staging tests.**
