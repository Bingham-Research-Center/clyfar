#!/bin/bash
#####################################################################
# Clyfar Environment Setup - Source this before running
#####################################################################
# Usage: source scripts/setup_env.sh
#        (then run salloc or scripts/run_clyfar.sh)
#####################################################################

# Change to clyfar directory
CLYFAR_DIR="${CLYFAR_DIR:-$HOME/gits/clyfar}"
cd "$CLYFAR_DIR" || { echo "ERROR: Cannot cd to $CLYFAR_DIR"; return 1; }

# Activate conda
CONDA_BASE="${CONDA_BASE:-$HOME/software/pkg/miniforge3}"
source "$CONDA_BASE/etc/profile.d/conda.sh"
conda activate clyfar-nov2025 || { echo "ERROR: Failed to activate clyfar-nov2025"; return 1; }

# Set PYTHONPATH
export PYTHONPATH="$PYTHONPATH:$CLYFAR_DIR"

# Load API keys if available
if [ -f ~/.bashrc_basinwx ]; then
    source ~/.bashrc_basinwx
fi

echo "Environment ready:"
echo "  Directory: $(pwd)"
echo "  Conda env: $CONDA_DEFAULT_ENV"
echo "  Python: $(which python)"
echo ""
echo "Next steps:"
echo "  1. salloc -n 32 -N 1 -t 4:00:00 -A lawson-np -p lawson-np"
echo "  2. scripts/run_clyfar.sh 2025112612"
