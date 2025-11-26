#!/bin/bash
# Quick test run for Clyfar on CHPC owner node
# Usage: ./test_run.sh [YYYYMMDDHH]

INIT=${1:-$(date -u -d '1 day ago' +%Y%m%d)00}

echo "=== Clyfar Test Run ==="
echo "Init time: $INIT"
echo ""

# Activate environment
source ~/software/pkg/miniforge3/etc/profile.d/conda.sh
conda activate clyfar-nov2025
export PYTHONPATH="$PYTHONPATH:~/gits/clyfar"
export POLARS_ALLOW_FORKING_THREAD=1

# Clear stale cfgrib indexes
rm -rf ~/gits/clyfar/data/herbie_cache/cfgrib_indexes/*

# Run with 16 CPUs, 3 members
python ~/gits/clyfar/run_gefs_clyfar.py \
  -i "$INIT" \
  -n 16 \
  -m 3 \
  -d "/scratch/general/vast/clyfar_test/v0p9/$INIT" \
  -f "/scratch/general/vast/clyfar_test/figs/$INIT"

echo ""
echo "=== Done ==="
ls -la /scratch/general/vast/clyfar_test/v0p9/$INIT/*.parquet 2>/dev/null | wc -l
echo "parquet files created"
