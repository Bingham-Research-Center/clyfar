# CHPC Quick Reference - Clyfar

> **Canonical CHPC reference:** `brc-tools/docs/CHPC-REFERENCE.md`
> This file contains Clyfar-specific shortcuts only.

---

## Clyfar salloc (I/O-bound workload)

```bash
salloc -n 4 -N 1 --mem=16G -t 2:00:00 -p lawson-np -A lawson-np
```

## Environment

```bash
conda activate clyfar-nov2025
export PYTHONPATH="$PYTHONPATH:~/gits/clyfar"
export POLARS_ALLOW_FORKING_THREAD=1
```

## Test Run

```bash
python ~/gits/clyfar/run_gefs_clyfar.py \
  -i "2025-11-24 00:00" \
  -n 4 \
  -m 3 \
  -d "/scratch/general/vast/clyfar_test/v0p9/$(date +%Y%m%d%H)" \
  -f "/scratch/general/vast/clyfar_test/figs/$(date +%Y%m%d%H)"
```

## Export + Upload

```bash
python ~/gits/clyfar/export/upload_batch.py \
  --json-dir /scratch/general/vast/clyfar_test/json/YYYYMMDD
```

## Clyfar-Specific Notes

- **Resource usage:** I/O bound (GRIB downloads), not CPU intensive
- **Memory:** 16GB for 3 members, 32GB for 31 members
- **Runtime:** ~30 min for 3 members, ~2 hr for full ensemble

## See Also

- `brc-tools/docs/CHPC-REFERENCE.md` - **Canonical** group resources, partitions, storage
- `CHPC_DEPLOYMENT_CHECKLIST.md` - Full deployment phases
- `CHPC-SETUP-GUIDE.md` - First-time environment setup
