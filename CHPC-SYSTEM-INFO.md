# CHPC System Information

**Last Updated**: 2025-11-23

## Operating System

**From**: `cat /etc/os-release`

```
NAME="Rocky Linux"
VERSION="8.10 (Green Obsidian)"
ID="rocky"
ID_LIKE="rhel centos fedora"
VERSION_ID="8.10"
PLATFORM_ID="platform:el8"
PRETTY_NAME="Rocky Linux 8.10 (Green Obsidian)"
ANSI_COLOR="0;32"
LOGO="fedora-logo-icon"
CPE_NAME="cpe:/o:rocky:rocky:8:GA"
HOME_URL="https://rockylinux.org/"
BUG_REPORT_URL="https://bugs.rockylinux.org/"
SUPPORT_END="2029-05-31"
ROCKY_SUPPORT_PRODUCT="Rocky-Linux-8"
ROCKY_SUPPORT_PRODUCT_VERSION="8.10"
REDHAT_SUPPORT_PRODUCT="Rocky Linux"
REDHAT_SUPPORT_PRODUCT_VERSION="8.10"
```

## Key Details

- **Distribution**: Rocky Linux 8.10 (RHEL clone)
- **Base**: RedHat Enterprise Linux 8
- **Support End**: 2029-05-31
- **Platform**: el8 (Enterprise Linux 8)

## Implications for Deployment

### Python/Conda
- Rocky Linux 8 uses system Python 3.6 by default
- **Use Miniconda/Anaconda** for modern Python (3.11+)
- System package manager: `dnf` (not `apt`)

### Package Management
```bash
# System packages (if needed)
sudo dnf install gcc  # For compiling Python packages

# But prefer conda for Python dependencies
conda install <package>
```

### Compatibility Notes
- Rocky Linux 8.10 is binary-compatible with RHEL 8.10
- Standard scientific Python stack (numpy, pandas, etc.) works well
- cfgrib/eccodes may need conda install (not pip)

### Troubleshooting Commands

**Check kernel version:**
```bash
uname -r
# Expected: 4.18.x or 5.x
```

**Check available modules:**
```bash
module avail
# Look for: miniconda3, python, gcc, etc.
```

**Check Python version:**
```bash
python --version  # System Python (usually 3.6)
which python

# After loading conda
module load miniconda3
python --version  # Should be 3.11+
```

**Check storage filesystem:**
```bash
df -Th ~
# Usually: NFS or Lustre for home directories
```

**Check GLIBC version** (important for compiled packages):
```bash
ldd --version
# Rocky 8 uses GLIBC 2.28
```

### Known Issues on Rocky Linux 8

1. **Old default Python**: Always use conda
2. **SSL/TLS certificates**: Usually up to date, but check if HTTPS fails:
   ```bash
   curl -I https://nomads.ncep.noaa.gov
   ```
3. **Locale settings**: May need to set:
   ```bash
   export LC_ALL=en_US.UTF-8
   export LANG=en_US.UTF-8
   ```

## System Resources

**To check your allocation:**
```bash
# Partition info
scontrol show partition notchpeak-shared-short

# Your limits
sacctmgr show user $USER -s

# Current usage
squeue -u $USER
```

## Updating This File

When you discover new system details, add them here:

```bash
cd ~/clyfar
cat >> CHPC-SYSTEM-INFO.md << 'EOF'

## New Section
[Your findings here]
EOF

git add CHPC-SYSTEM-INFO.md
git commit -m "docs: Update CHPC system info"
git push
```

---

**See also:**
- CHPC_DEPLOYMENT_CHECKLIST.md - Deployment steps
- DEPLOYMENT-SPECS-TODO.md (in ubair-website) - Resource limits to verify
