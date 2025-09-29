#!/bin/bash
#SBATCH --job-name=clyfar_smoke
#SBATCH --account=<ACCOUNT>
#SBATCH --partition=<PARTITION>
#SBATCH --time=00:45:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --output=clyfar_test.log

set -euo pipefail

module load miniconda || true
source "$(conda info --base 2>/dev/null)/etc/profile.d/conda.sh" || true
conda activate clyfar

cd $SLURM_SUBMIT_DIR

python run_gefs_clyfar.py \
  -i 2024010100 \
  -n 16 \
  -m 10 \
  -d ./data \
  -f ./figures \
  --testing \
  --log-fis
