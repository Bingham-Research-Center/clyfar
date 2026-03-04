# CHPC Resource Inventory - 27 Dec 2024

## User Identity
```
uid=808826(u0737349) gid=4001165(lawson)
groups: lawson, usu
```

## SLURM Account Associations

| Account | Cluster | Partition | QOS |
|---------|---------|-----------|-----|
| smithp-guest | ash | - | ash-guest, ash-guest-res |
| horel | ember | - | ember |
| owner-guest | ember | - | ember-guest |
| lawson | granite | - | granite-freecycle, granite-gpu |
| **lawson** | **kingspeak** | - | kingspeak |
| **lawson-kp** | **kingspeak** | - | lawson-kp |
| kingspeak-gpu | kingspeak | - | kingspeak-gpu |
| owner-gpu-guest | kingspeak | - | kingspeak-gpu-guest |
| owner-guest | kingspeak | - | kingspeak-guest |
| **lawson** | **lonepeak** | - | lonepeak |
| lonepeak-gpu | lonepeak | - | lonepeak-gpu |
| owner-guest | lonepeak | - | lonepeak-guest |
| dtn | notchpeak | - | notchpeak-dtn |
| **lawson-np** | **notchpeak** | - | lawson-np |
| lawson | notchpeak | - | notchpeak-freecycle |
| notchpeak-gpu | notchpeak | - | notchpeak-gpu |
| notchpeak-shared-short | notchpeak | - | notchpeak-shared-short |
| notchpeak-shared | notchpeak | - | notchpeak-shared |
| owner-gpu-guest | notchpeak | - | notchpeak-gpu-guest |
| owner-guest | notchpeak | - | notchpeak-guest |

## Allocation Summary (from myallocation)

### Kingspeak
- **General**: Account `lawson`, Partitions: `kingspeak`, `kingspeak-shared`
- **Owner**: Account `lawson-kp`, Partitions: `lawson-kp`, `lawson-shared-kp`
- **GPU**: Account `kingspeak-gpu`, Partition: `kingspeak-gpu`
- **Preemptable GPU**: Account `owner-gpu-guest`, Partition: `kingspeak-gpu-guest`
- **Preemptable**: Account `owner-guest`, Partitions: `kingspeak-guest`, `kingspeak-shared-guest`

### Notchpeak
- **Owner**: Account `lawson-np`, Partitions: `lawson-np`, `lawson-shared-np`
- **General**: Account `dtn`, Partition: `notchpeak-dtn`
- **General**: Account `notchpeak-shared-short`, Partition: `notchpeak-shared-short`
- **GPU**: Account `notchpeak-gpu`, Partition: `notchpeak-gpu`
- **Preemptable Freecycle**: Account `lawson`, Partitions: `notchpeak-freecycle`, `notchpeak-shared-freecycle`
- **Preemptable GPU**: Account `owner-gpu-guest`, Partition: `notchpeak-gpu-guest`
- **Preemptable**: Account `owner-guest`, Partitions: `notchpeak-guest`, `notchpeak-shared-guest`

### Lonepeak
- **General**: Account `lawson`, Partitions: `lonepeak`, `lonepeak-shared`
- **GPU**: Account `lonepeak-gpu`, Partition: `lonepeak-gpu`
- **Preemptable**: Account `owner-guest`, Partitions: `lonepeak-guest`, `lonepeak-shared-guest`

## Storage

| Filesystem | Size | Used | Avail | Use% | Mount |
|------------|------|------|-------|------|-------|
| Home (VAST) | 2.0T | 1.7T | 319G | 85% | /uufs/chpc.utah.edu/common/home/u0737349 |

**Note**: No dedicated scratch space (vast/lustre) detected for this user.

## Key Partitions Available

### Owner Nodes (Priority Access)
| Partition | Cluster | Nodes | Time Limit |
|-----------|---------|-------|------------|
| lawson-kp | kingspeak | owner | 14 days |
| lawson-np | notchpeak | 2 nodes (notch137, notch392) | 14 days |

### General Access
| Partition | Time Limit | Notes |
|-----------|------------|-------|
| notchpeak | 3 days | Default partition |
| notchpeak-shared | 3 days | Shared node access |
| notchpeak-shared-short | 8 hours | Quick jobs |
| kingspeak | 3 days | General |
| lonepeak | 3 days | General |

### GPU Access
| Partition | Type | Notes |
|-----------|------|-------|
| notchpeak-gpu | Dedicated | 10 nodes |
| kingspeak-gpu | Dedicated | Available |
| lonepeak-gpu | Dedicated | Available |
| *-gpu-guest | Preemptable | Lower priority, may be killed |

### Preemptable/Freecycle
| Partition | Notes |
|-----------|-------|
| notchpeak-freecycle | Uses idle owner nodes |
| notchpeak-guest | Preemptable on owner nodes |
| kingspeak-guest | Preemptable on owner nodes |
| lonepeak-guest | Preemptable on owner nodes |

## Interactive CLI Agent Sessions (Claude Code, aider, etc.)

**Workload profile**: Low CPU, low memory (4-8GB), long duration, needs stable TTY.

### Recommended Approach by Scenario

| Scenario | Account | Partition | Command |
|----------|---------|-----------|---------|
| **Typical session (<8hr)** | notchpeak-shared-short | notchpeak-shared-short | See below |
| **Longer session (8-24hr)** | lawson | lonepeak-shared | See below |
| **Owner nodes idle + need stability** | lawson-np | lawson-np | See below |

### Why NOT default to owner nodes?
- Owner nodes are a **limited group resource** (only 2 on notchpeak)
- Claude Code is **low-CPU, I/O-bound** (waiting on API calls)
- Using owner nodes for light work **blocks** group members needing heavy compute
- Shared partitions are **designed for this workload**

### Recommended Commands

```bash
# INSTANT (lawson owner node, no queue): salloc -A lawson-np -p lawson-np -t4:00:00 --mem=4G

# BEST FOR MOST SESSIONS: shared-short (quick queue, 8hr max)
salloc --account=notchpeak-shared-short --partition=notchpeak-shared-short \
  --time=8:00:00 --ntasks=1 --mem=4G

# LONGER SESSIONS: lonepeak-shared (may queue briefly, 3-day max)
salloc --account=lawson --partition=lonepeak-shared \
  --time=24:00:00 --ntasks=1 --mem=4G

# OWNER NODES: only when idle AND need guaranteed stability
salloc --account=lawson-np --partition=lawson-np \
  --time=8:00:00 --ntasks=1 --mem=4G
```

### Session Management with screen/tmux

```bash
# Start persistent session (survives SSH disconnect)
screen -S claude
salloc --account=notchpeak-shared-short --partition=notchpeak-shared-short \
  --time=8:00:00 --ntasks=1 --mem=4G
claude  # or your CLI agent

# Detach: Ctrl-A D
# Reattach later: screen -r claude
```

## Other Quick Reference

```bash
# GPU session (for LLM inference, not typical Claude Code use)
salloc --account=notchpeak-gpu --partition=notchpeak-gpu --time=2:00:00 --gres=gpu:1

# Check your jobs
squeue -u $USER

# Check allocation status
myallocation

# Check what's available now
sinfo -s
```
