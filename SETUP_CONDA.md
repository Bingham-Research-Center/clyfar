# Environment Setup with Miniforge3
Date updated: 2025-09-25

Follow these steps to reproduce the `clyfar` Conda environment using Miniforge3.

## 1. Install Miniforge3 (if needed)
```bash
# macOS / Linux
going to https://github.com/conda-forge/miniforge and download Miniforge3 installer
bash Miniforge3-MacOSX-arm64.sh  # or appropriate installer

# Windows (PowerShell)
# Download Miniforge3-Windows-x86_64.exe and run the installer
```
After installation:
```bash
# Initialise Conda
conda init
# Restart your shell to load changes
```

## 2. Create the `clyfar` Environment
```bash
conda create -n clyfar python=3.11.9 -y
conda activate clyfar
```

## 3. Install Dependencies
```bash
pip install -r requirements.txt
```
> Note: requirements install may need internet access; see `requirements.txt` for packages (numpy, pandas, scikit-fuzzy, matplotlib, xarray, cartopy, etc.).

## 4. Optional: Local Configuration
- Set `MPLCONFIGDIR=/path/to/writable/cache` if matplotlib warns about cache permissions.
- You may create `constraints/` files (e.g., `constraints/baseline-0.9.txt`) to pin package versions for experiments.

## 5. Validation
```bash
python - <<'PY'
from fis.v0p9 import Clyfar
print("Loaded FIS version:", Clyfar.__name__)
PY
```
If the import succeeds, the environment is ready.

Keep this document updated when Python or dependency versions change.
