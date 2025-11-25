#!/usr/bin/env python3
"""
MSLP Extraction Diagnostic Test
================================
Tests whether Herbie 2025.11.2+ fixes the "invalid index to scalar variable"
error when extracting PRMSL from GEFS atmos.5 product.

The bug manifests as:
- atmos.25 (f000-f240, 0.25° res): WORKS
- atmos.5  (f246-f384, 0.5° res): FAILS with "invalid index to scalar variable"

Root cause hypothesis: cfgrib/Herbie bug when subsetting the last grid in GRIB file.
Fix: Herbie 2025.11.2 "Subset fails when last grid selected" bug fix.

Usage:
    python scripts/test_mslp_fix.py

Created: 2025-11-24
"""

import sys
import traceback
from datetime import datetime, timedelta

# Get a recent initialization time (yesterday 00Z is safest for data availability)
yesterday = datetime.utcnow() - timedelta(days=1)
INIT_TIME = yesterday.strftime("%Y-%m-%d 00:00")


def print_header(text: str):
    """Print a formatted header."""
    print("\n" + "=" * 60)
    print(text)
    print("=" * 60)


def print_result(test_name: str, success: bool, details: str = ""):
    """Print test result with color coding."""
    status = "\033[92mPASS\033[0m" if success else "\033[91mFAIL\033[0m"
    print(f"  [{status}] {test_name}")
    if details:
        print(f"         {details}")


def check_versions():
    """Check installed package versions."""
    print_header("Package Versions")

    packages = [
        ("herbie", "herbie"),
        ("cfgrib", "cfgrib"),
        ("pygrib", "pygrib"),
        ("xarray", "xarray"),
        ("numpy", "numpy"),
        ("eccodes", "eccodes"),
    ]

    for display_name, import_name in packages:
        try:
            mod = __import__(import_name)
            version = getattr(mod, "__version__", "unknown")
            print(f"  {display_name}: {version}")
        except ImportError:
            print(f"  {display_name}: NOT INSTALLED")

    # Check Herbie version specifically
    try:
        import herbie
        version = herbie.__version__
        parts = version.split(".")
        if len(parts) >= 2:
            year_month = f"{parts[0]}.{parts[1]}"
            if year_month >= "2025.11":
                print(f"\n  \033[92mHerbie version {version} includes the fix!\033[0m")
                return True
            else:
                print(f"\n  \033[93mWarning: Herbie {version} may not have the fix.\033[0m")
                print(f"  \033[93mRecommended: >= 2025.11.2\033[0m")
                return False
    except Exception:
        return False
    return True


def test_atmos25_prmsl():
    """Test PRMSL extraction from atmos.25 (should work)."""
    print_header(f"Test 1: atmos.25 PRMSL (init={INIT_TIME}, fxx=006)")

    try:
        from herbie import Herbie

        H = Herbie(
            INIT_TIME,
            model="gefs",
            product="atmos.25",
            member="p01",
            fxx=6
        )

        print(f"  Source: {H.grib_source}")

        # Try to get PRMSL via xarray
        ds = H.xarray(":PRMSL:", remove_grib=True)

        if "prmsl" in ds.data_vars or "PRMSL" in ds.data_vars:
            var_name = "prmsl" if "prmsl" in ds.data_vars else "PRMSL"
            data = ds[var_name].values
            print_result(
                "atmos.25 PRMSL extraction",
                True,
                f"Shape: {data.shape}, Range: {data.min():.0f}-{data.max():.0f} Pa"
            )
            return True
        else:
            print_result("atmos.25 PRMSL extraction", False, f"Variables: {list(ds.data_vars)}")
            return False

    except Exception as e:
        print_result("atmos.25 PRMSL extraction", False, str(e))
        traceback.print_exc()
        return False


def test_atmos5_prmsl():
    """Test PRMSL extraction from atmos.5 (the problematic one)."""
    print_header(f"Test 2: atmos.5 PRMSL (init={INIT_TIME}, fxx=360)")
    print("  This is the test that previously failed with:")
    print("  'invalid index to scalar variable'")
    print()

    try:
        from herbie import Herbie

        H = Herbie(
            INIT_TIME,
            model="gefs",
            product="atmos.5",
            member="p01",
            fxx=360
        )

        print(f"  Source: {H.grib_source}")

        # First check inventory
        print("  Checking inventory for PRMSL...")
        inv = H.inventory()
        prmsl_rows = inv[inv["search_this"].str.contains("PRMSL", case=False, na=False)]
        if len(prmsl_rows) > 0:
            print(f"  Found {len(prmsl_rows)} PRMSL entries in inventory")
        else:
            print("  Warning: No PRMSL in inventory")

        # Try to get PRMSL via xarray (this is what failed before)
        print("  Attempting xarray extraction...")
        ds = H.xarray(":PRMSL:", remove_grib=True)

        if "prmsl" in ds.data_vars or "PRMSL" in ds.data_vars:
            var_name = "prmsl" if "prmsl" in ds.data_vars else "PRMSL"
            data = ds[var_name].values
            print_result(
                "atmos.5 PRMSL extraction",
                True,
                f"Shape: {data.shape}, Range: {data.min():.0f}-{data.max():.0f} Pa"
            )
            return True
        else:
            print_result("atmos.5 PRMSL extraction", False, f"Variables: {list(ds.data_vars)}")
            return False

    except Exception as e:
        error_msg = str(e)
        print_result("atmos.5 PRMSL extraction", False, error_msg)

        # Check if it's the known bug
        if "invalid index to scalar" in error_msg.lower():
            print("\n  \033[91mThis is the known bug!\033[0m")
            print("  The Herbie version may not have the fix.")
            print("  Ensure herbie-data >= 2025.11.2 from conda-forge.")

        traceback.print_exc()
        return False


def test_pygrib_fallback():
    """Test direct pygrib access as a fallback."""
    print_header(f"Test 3: pygrib Direct Access (init={INIT_TIME}, fxx=360)")

    try:
        import pygrib
        from herbie import Herbie

        H = Herbie(
            INIT_TIME,
            model="gefs",
            product="atmos.5",
            member="p01",
            fxx=360
        )

        # Download the GRIB file
        print("  Downloading GRIB file...")
        grib_path = H.download()
        print(f"  Downloaded: {grib_path}")

        # Open with pygrib directly
        print("  Opening with pygrib...")
        with pygrib.open(str(grib_path)) as grbs:
            # Find PRMSL
            prmsl_msgs = grbs.select(shortName="prmsl")
            if prmsl_msgs:
                msg = prmsl_msgs[0]
                data = msg.values
                print_result(
                    "pygrib PRMSL extraction",
                    True,
                    f"Shape: {data.shape}, Range: {data.min():.0f}-{data.max():.0f} Pa"
                )
                return True
            else:
                # Try alternative name
                prmsl_msgs = grbs.select(name="Pressure reduced to MSL")
                if prmsl_msgs:
                    msg = prmsl_msgs[0]
                    data = msg.values
                    print_result(
                        "pygrib PRMSL extraction",
                        True,
                        f"Shape: {data.shape}, Range: {data.min():.0f}-{data.max():.0f} Pa"
                    )
                    return True

        print_result("pygrib PRMSL extraction", False, "PRMSL not found in GRIB")
        return False

    except ImportError:
        print_result("pygrib PRMSL extraction", False, "pygrib not installed")
        return False
    except Exception as e:
        print_result("pygrib PRMSL extraction", False, str(e))
        traceback.print_exc()
        return False


def main():
    """Run all diagnostic tests."""
    print("\n" + "=" * 60)
    print("MSLP EXTRACTION DIAGNOSTIC TEST")
    print(f"Init time: {INIT_TIME}")
    print("=" * 60)

    # Check versions first
    version_ok = check_versions()

    # Run tests
    results = {
        "atmos.25": test_atmos25_prmsl(),
        "atmos.5": test_atmos5_prmsl(),
    }

    # Only run pygrib test if atmos.5 failed
    if not results["atmos.5"]:
        results["pygrib_fallback"] = test_pygrib_fallback()

    # Summary
    print_header("SUMMARY")

    all_critical_pass = results["atmos.25"] and results["atmos.5"]

    if all_critical_pass:
        print("\n  \033[92m*** ALL TESTS PASSED ***\033[0m")
        print("\n  The Herbie update fixed the MSLP extraction issue!")
        print("  You can now run the full clyfar test.")
        return 0
    else:
        print("\n  \033[91m*** SOME TESTS FAILED ***\033[0m")

        if results["atmos.25"] and not results["atmos.5"]:
            print("\n  atmos.25 works but atmos.5 fails.")
            print("  This is the known bug pattern.")

            if "pygrib_fallback" in results and results["pygrib_fallback"]:
                print("\n  \033[93mWORKAROUND: pygrib direct access works.\033[0m")
                print("  The clyfar code has a pygrib fallback that should work.")
                print("  Consider forcing pygrib-only mode in gefsdata.py.")
            else:
                print("\n  Options:")
                print("  1. Ensure herbie-data >= 2025.11.2 is installed")
                print("  2. Force pygrib-only extraction in gefsdata.py")
                print("  3. Limit forecast to f240 (skip atmos.5 hours)")

        return 1


if __name__ == "__main__":
    sys.exit(main())
