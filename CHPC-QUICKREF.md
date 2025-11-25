# CHPC Quick Reference - Lawson Group

## Partitions (Use Owner Nodes First)

| Partition | Nodes | Use Case |
|-----------|-------|----------|
| `lawson-np` | 2 | **Primary** - Notchpeak owner nodes |
| `lawson-kp` | 4 | **Secondary** - Kingspeak owner nodes |
| `notchpeak-shared` | shared | Fallback when owner nodes busy |

## Optimal salloc Commands

### Clyfar Forecast (I/O + inference)
```bash
# Owner partition (preferred) - modest resources, I/O bound workload
salloc -n 4 -N 1 --mem=16G -t 2:00:00 -p lawson-np -A lawson-np
```

### Heavy Computation (rare)
```bash
# Full node when truly needed
salloc -n 16 -N 1 --mem=64G -t 4:00:00 -p lawson-np -A lawson-np
```

### Fallback (owner nodes busy)
```bash
salloc -n 4 -N 1 --mem=16G -t 2:00:00 -p notchpeak-shared -A notchpeak-shared-short
```

## Storage Locations

| Path | Type | Capacity | Use |
|------|------|----------|-----|
| `/scratch/general/vast/` | Scratch | Large | Temp data, GRIB cache |
| `lawson-group5` | Cottonwood | 16 TiB | Persistent datasets |
| `lawson-group6` | Cottonwood | 16 TiB | Persistent datasets |
| `~/` | Home/Vast | 7 GiB | Code, configs only |

## Environment Activation

```bash
conda activate clyfar-nov2025
export PYTHONPATH="$PYTHONPATH:~/gits/clyfar"
export POLARS_ALLOW_FORKING_THREAD=1
```

## Common Pitfalls

1. **Over-allocation**: Clyfar is I/O bound (downloads), not CPU bound. Use 4 cores, not 8+.
2. **Wrong partition**: Use `lawson-np` (owner) not `notchpeak` (shared).
3. **Memory**: 16GB sufficient for 3-member runs, 32GB for full 31-member.

## See Also

- `brc-tools/AGENT-INDEX.md` - Full CHPC deployment guide
- `brc-tools/docs/PIPELINE-ARCHITECTURE.md` - System design
- `clyfar/CHPC_DEPLOYMENT_CHECKLIST.md` - Deployment steps
