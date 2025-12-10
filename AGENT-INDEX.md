# AI Agent Quick Reference - clyfar

**State (2025-12-05):** Production uploads to BasinWx are running from CHPC cron; Akamai has forecasts/images through 20251129_1800Z. Local repo on `main` at `fa01f09` (Dec 5 fix for incomplete GEFS + PNG upload timeout). CHPC clone still on `integration-clyfar-v0.9.5` (`866e1ea`).

**Version:** Last tag `v0.9.3`. Metadata strings and scripts call this "Clyfar v0.9.5" but no tag yet—decide before preprint/manifest sync.

## Fast Spin-up
- Read `~/WebstormProjects/ubair-website/COMPACT-RESUME-POINT.md` (plan) and `HANDOFF-30NOV2025-S3.md` (station IDs, env fixes) before diving into files.
- Smoke: `python run_gefs_clyfar.py -i 2024010100 -n 2 -m 2 -d ./data -f ./figures --testing --allow-incomplete` (uploads only if `DATA_UPLOAD_API_KEY` is set).
- Env: `conda activate clyfar-nov2025` from `~/software/pkg/miniforge3`; requires editable `brc-tools`.
- Export: `export/to_basinwx.py` writes 63 JSONs + uploads PNGs (60s timeout, shared Session) when `run_gefs_clyfar.py` runs with `save`/`visualise`.

## Operations Snapshot
- CHPC cron (Nov 30 diagnostic `diagnostic-notchpeak1-20251130-2042.txt`): `0 22,4,10,16 * * * sbatch ~/gits/clyfar/scripts/submit_clyfar.sh`; data under `~/basinwx-data/clyfar`, logs in `~/logs/clyfar_submit.log`.
- Akamai diagnostic (Dec 1 `diagnostic-172-234-249-49.ip.linodeusercontent.com-20251201-0342.txt`): observations/meta streaming every 5 min; forecasts/images directories populated (possibility/percentile JSONs + heatmap PNGs).

## Recent Changes
- `fa01f09` (Dec 5, main): safe handling of missing GEFS hours (`safe_loc`), PNG uploads use 60s timeout and explicit Session close.
- `export/to_basinwx.py` now outputs 4-category per-member products + exceedance JSON; integrated into `run_gefs_clyfar.py` default workflow.

## Immediate Actions / Open Questions
- Align deployments: promote `main@fa01f09` to CHPC + Akamai or confirm current branch is desired.
- Update `~/WebstormProjects/ubair-website/DATA_MANIFEST.json` (currently marked [PLANNED]) to reflect operational forecasts (4 categories, 63 files) and current schedule (cron at 22/04/10/16 UTC).
- Decide whether to tag `v0.9.5` and sync preprint (`~/Documents/GitHub/preprint-clyfar-v0p9`) + manifest; prune repo per `docs/bloat_reduction.md` once version is fixed.
