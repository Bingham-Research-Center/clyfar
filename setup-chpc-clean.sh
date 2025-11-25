#!/bin/bash
# =============================================================================
# Clyfar Clean Environment Setup for CHPC
# Created: 2025-11-24
#
# This script creates a fresh conda environment with 100% conda-forge packages.
# Run this on CHPC (login node or interactive session).
#
# Usage:
#   chmod +x setup-chpc-clean.sh
#   ./setup-chpc-clean.sh
# =============================================================================

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Clyfar Clean Environment Setup${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Configuration
ENV_NAME="clyfar-nov2025"
ENV_FILE="environment-chpc-clean.yml"
CLYFAR_DIR="${HOME}/gits/clyfar"

# Check we're on CHPC
if [[ ! $(hostname) =~ "chpc.utah.edu" ]] && [[ ! $(hostname) =~ "notchpeak" ]]; then
    echo -e "${YELLOW}Warning: Not detected as CHPC system. Proceeding anyway...${NC}"
fi

# Check if environment file exists
if [[ ! -f "${CLYFAR_DIR}/${ENV_FILE}" ]]; then
    echo -e "${RED}Error: ${ENV_FILE} not found in ${CLYFAR_DIR}${NC}"
    echo "Make sure you've pulled the latest clyfar code."
    exit 1
fi

# Step 1: Load conda/mamba
echo -e "${GREEN}[1/6] Loading conda module...${NC}"
if command -v module &> /dev/null; then
    module load miniconda3/latest 2>/dev/null || module load anaconda3/latest 2>/dev/null || true
fi

# Check for mamba (preferred) or conda
if command -v mamba &> /dev/null; then
    CONDA_CMD="mamba"
    echo -e "  Using mamba (faster solver)"
else
    CONDA_CMD="conda"
    echo -e "  Using conda"
fi

# Step 2: Remove old environment if it exists
echo -e "${GREEN}[2/6] Checking for existing environment...${NC}"
if conda env list | grep -q "^${ENV_NAME} "; then
    echo -e "  ${YELLOW}Environment '${ENV_NAME}' exists. Removing...${NC}"
    conda env remove -n "${ENV_NAME}" -y
    echo -e "  Removed."
else
    echo -e "  No existing environment found."
fi

# Also check for old clyfar-dec2025 environment
if conda env list | grep -q "^clyfar-dec2025 "; then
    echo -e "  ${YELLOW}Found old 'clyfar-dec2025' environment.${NC}"
    read -p "  Remove it? (y/n): " remove_old
    if [[ "$remove_old" == "y" ]]; then
        conda env remove -n "clyfar-dec2025" -y
        echo -e "  Removed clyfar-dec2025."
    fi
fi

# Step 3: Create new environment
echo -e "${GREEN}[3/6] Creating environment from ${ENV_FILE}...${NC}"
echo -e "  This may take 5-10 minutes..."
cd "${CLYFAR_DIR}"
$CONDA_CMD env create -f "${ENV_FILE}"

# Step 4: Activate and verify
echo -e "${GREEN}[4/6] Verifying installation...${NC}"
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate "${ENV_NAME}"

echo -e "  Python: $(python --version)"
echo -e "  NumPy: $(python -c 'import numpy; print(numpy.__version__)')"
echo -e "  Herbie: $(python -c 'import herbie; print(herbie.__version__)')"
echo -e "  cfgrib: $(python -c 'import cfgrib; print(cfgrib.__version__)')"
echo -e "  pygrib: $(python -c 'import pygrib; print(pygrib.__version__)')"
echo -e "  synopticpy: $(python -c 'import synopticpy; print(synopticpy.__version__)')"

# Step 5: Quick sanity check - can we import clyfar?
echo -e "${GREEN}[5/6] Testing clyfar imports...${NC}"
export PYTHONPATH="${PYTHONPATH}:${CLYFAR_DIR}"
python -c "
import sys
sys.path.insert(0, '${CLYFAR_DIR}')
try:
    from clyfar import ClyfarEngine
    print('  ClyfarEngine: OK')
except ImportError as e:
    print(f'  ClyfarEngine: FAILED ({e})')

try:
    from nwp.gefsdata import GEFSData
    print('  GEFSData: OK')
except ImportError as e:
    print(f'  GEFSData: FAILED ({e})')

try:
    from preprocessing.representative_nwp_values import extract_representative_nwp
    print('  extract_representative_nwp: OK')
except ImportError as e:
    print(f'  extract_representative_nwp: FAILED ({e})')
"

# Step 6: Print next steps
echo -e "${GREEN}[6/6] Setup complete!${NC}"
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Next Steps${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "1. Activate the environment:"
echo -e "   ${YELLOW}conda activate ${ENV_NAME}${NC}"
echo ""
echo "2. Set PYTHONPATH:"
echo -e "   ${YELLOW}export PYTHONPATH=\"\$PYTHONPATH:${CLYFAR_DIR}\"${NC}"
echo ""
echo "3. Run the MSLP diagnostic test:"
echo -e "   ${YELLOW}python ${CLYFAR_DIR}/scripts/test_mslp_fix.py${NC}"
echo ""
echo "4. If MSLP test passes, run the full test:"
echo -e "   ${YELLOW}python ${CLYFAR_DIR}/run_gefs_clyfar.py -i \"2025112400\" -n 8 -m 3 \\
     -d \"/scratch/general/vast/clyfar_test/v0p9/2025112400\" \\
     -f \"/scratch/general/vast/clyfar_test/figs/2025112400\"${NC}"
echo ""
echo -e "${GREEN}Environment '${ENV_NAME}' is ready.${NC}"
