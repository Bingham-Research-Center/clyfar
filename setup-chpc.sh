#!/bin/bash
# CHPC Environment Setup - Clyfar v0.9.5
# Automated deployment script for production environment
# Usage: bash setup-chpc.sh

set -e  # Exit on any error

echo "========================================="
echo "Clyfar CHPC Setup - Dec 2025"
echo "========================================="

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 1. Load miniforge module
echo -e "${YELLOW}[1/8] Loading miniforge3 module...${NC}"
module use "$HOME/MyModules" 2>/dev/null || true
module load miniforge3/latest
source "$HOME/software/pkg/miniforge3/bin/activate"
echo -e "${GREEN}✓ Miniforge loaded${NC}"

# 2. Check if environment exists
echo -e "${YELLOW}[2/8] Checking for existing environment...${NC}"
if conda env list | grep -q "clyfar-dec2025"; then
    echo -e "${YELLOW}Environment 'clyfar-dec2025' exists. Removing...${NC}"
    conda env remove -n clyfar-dec2025 -y
fi
echo -e "${GREEN}✓ Ready for fresh install${NC}"

# 3. Create environment from lock file
echo -e "${YELLOW}[3/8] Creating conda environment (this takes ~5-10 min)...${NC}"
cd ~/gits/clyfar
mamba env create -f environment-chpc.yml
echo -e "${GREEN}✓ Environment created${NC}"

# 4. Activate environment
echo -e "${YELLOW}[4/8] Activating environment...${NC}"
conda activate clyfar-dec2025
echo -e "${GREEN}✓ Environment activated${NC}"

# 5. Install brc-tools (editable)
echo -e "${YELLOW}[5/8] Installing brc-tools...${NC}"
pip install -e ~/gits/brc-tools --no-deps
echo -e "${GREEN}✓ brc-tools installed${NC}"

# 6. Set environment variables
echo -e "${YELLOW}[6/8] Configuring environment variables...${NC}"
mkdir -p ~/.config/clyfar

# Check if .env exists
if [ ! -f ~/gits/clyfar/.env ]; then
    echo -e "${YELLOW}Creating .env from template...${NC}"
    cp ~/gits/clyfar/.env.example ~/gits/clyfar/.env
    echo -e "${RED}⚠ IMPORTANT: Edit ~/gits/clyfar/.env and add your API keys!${NC}"
fi

# Create activation script
cat > ~/.config/clyfar/activate.sh << 'ACTIVATE_EOF'
#!/bin/bash
# Auto-load Clyfar environment

# Load miniforge
module use "$HOME/MyModules" 2>/dev/null || true
module load miniforge3/latest
source "$HOME/software/pkg/miniforge3/bin/activate"

# Activate conda env
conda activate clyfar-dec2025

# Set environment variables
export POLARS_ALLOW_FORKING_THREAD=1
export PYTHONPATH="$PYTHONPATH:$HOME/gits/clyfar"

# Load secrets from .env
if [ -f "$HOME/gits/clyfar/.env" ]; then
    set -a
    source "$HOME/gits/clyfar/.env"
    set +a
fi

echo "✓ Clyfar environment activated (clyfar-dec2025)"
ACTIVATE_EOF

chmod +x ~/.config/clyfar/activate.sh
echo -e "${GREEN}✓ Environment variables configured${NC}"

# 7. Verify installation
echo -e "${YELLOW}[7/8] Verifying installation...${NC}"
python << 'VERIFY_EOF'
import sys
try:
    import numpy
    import pandas
    import xarray
    import herbie
    import cfgrib
    from brc_tools.download.push_data import send_json_to_server

    print(f"✓ Python: {sys.version.split()[0]}")
    print(f"✓ numpy: {numpy.__version__} (expected 1.26.x)")
    print(f"✓ pandas: {pandas.__version__}")
    print(f"✓ xarray: {xarray.__version__}")
    print(f"✓ herbie: {herbie.__version__}")
    print(f"✓ cfgrib: {cfgrib.__version__}")
    print(f"✓ brc-tools: imported successfully")

    # Verify numpy < 2.0
    major = int(numpy.__version__.split('.')[0])
    if major >= 2:
        print(f"⚠ WARNING: numpy {numpy.__version__} is >= 2.0 (compatibility issues possible)")
        sys.exit(1)
    else:
        print(f"✓ numpy version OK (< 2.0)")

except ImportError as e:
    print(f"✗ Import failed: {e}")
    sys.exit(1)
VERIFY_EOF

echo -e "${GREEN}✓ Installation verified${NC}"

# 8. Create quick-start alias
echo -e "${YELLOW}[8/8] Setting up quick-start command...${NC}"
if ! grep -q "alias clyfar-activate" ~/.bashrc; then
    echo "alias clyfar-activate='source ~/.config/clyfar/activate.sh'" >> ~/.bashrc
    echo -e "${GREEN}✓ Added 'clyfar-activate' alias to ~/.bashrc${NC}"
fi

# Final instructions
echo ""
echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}Setup Complete!${NC}"
echo -e "${GREEN}=========================================${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Edit API keys: nano ~/gits/clyfar/.env"
echo "2. Activate environment: source ~/.config/clyfar/activate.sh"
echo "   (or just run: clyfar-activate)"
echo "3. Test MSLP: python ~/gits/clyfar/scripts/check_mslp.py -i 2025112300 -m p01 -f 0 6 12"
echo "4. Run Clyfar: python ~/gits/clyfar/run_gefs_clyfar.py -i YYYYMMDDHH -m 3 -n 8"
echo ""
echo -e "${YELLOW}To activate in future sessions:${NC}"
echo "  source ~/.config/clyfar/activate.sh"
echo ""
