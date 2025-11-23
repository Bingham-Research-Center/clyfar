"""Integration test for Clyfar → BasinWx export pipeline.

Tests the export module without running full Clyfar inference.
Uses mock data to validate:
- Import from brc-tools works
- Environment variables are set
- 4 ozone categories (background, moderate, elevated, extreme)
- All 3 data products generate correctly (63 files)
- No personal information in output
- JSON schema is valid

Created by: John Lawson & Claude
"""

import os
import sys
import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import numpy as np


def test_imports():
    """Test that required packages are importable."""
    print("Testing imports...")

    try:
        from brc_tools.download.push_data import send_json_to_server
        print("✓ brc_tools import successful")
    except ImportError as e:
        print(f"✗ brc_tools import failed: {e}")
        print("  Run: pip install -e ~/PycharmProjects/brc-tools")
        sys.exit(1)

    try:
        from export.to_basinwx import (
            export_possibility_heatmaps,
            export_exceedance_probabilities,
            export_percentile_scenarios,
            export_all_products,
            OZONE_CATEGORIES
        )
        print("✓ export.to_basinwx import successful")
    except ImportError as e:
        print(f"✗ export.to_basinwx import failed: {e}")
        sys.exit(1)

    return True


def test_environment():
    """Test that required environment variables are set."""
    print("\nTesting environment variables...")

    required_vars = ['DATA_UPLOAD_API_KEY', 'BASINWX_API_URL']
    missing = []

    for var in required_vars:
        if os.getenv(var):
            print(f"✓ {var} is set")
        else:
            print(f"⚠ {var} not set (upload will be skipped)")
            missing.append(var)

    if missing:
        print(f"  Optional: Set in .env file for upload functionality")

    return True


def test_categories():
    """Test that Clyfar uses 4 ozone categories (not 5)."""
    print("\nTesting ozone categories...")

    from export.to_basinwx import OZONE_CATEGORIES

    expected_categories = ["background", "moderate", "elevated", "extreme"]
    actual_categories = list(OZONE_CATEGORIES.keys())

    if actual_categories == expected_categories:
        print(f"✓ Correct 4 categories: {actual_categories}")
    else:
        print(f"✗ Category mismatch!")
        print(f"  Expected: {expected_categories}")
        print(f"  Got: {actual_categories}")
        sys.exit(1)

    # Check threshold structure
    for cat, thresholds in OZONE_CATEGORIES.items():
        if all(k in thresholds for k in ['min', 'peak_start', 'peak_end', 'max']):
            print(f"✓ {cat}: {thresholds['min']}-{thresholds['max']} ppb")
        else:
            print(f"✗ {cat} missing threshold keys")
            sys.exit(1)

    return True


def create_mock_data(n_members=31, n_days=15):
    """Create mock dailymax_df_dict for testing.

    Args:
        n_members: Number of ensemble members (default 31)
        n_days: Number of forecast days (default 15)

    Returns:
        Dict mapping member names to DataFrames
    """
    print(f"\nCreating mock data ({n_members} members, {n_days} days)...")

    dailymax_df_dict = {}

    # Generate date range
    start_date = pd.Timestamp("2025-01-15", tz=None)
    dates = pd.date_range(start_date, periods=n_days, freq='D')

    # Categories
    categories = ["background", "moderate", "elevated", "extreme"]

    # Create control member
    member_names = ["clyfarcontrol"] + [f"clyfar{i:03d}" for i in range(1, n_members)]

    for member in member_names:
        # Create DataFrame with realistic mock data
        df = pd.DataFrame(index=dates)

        # Possibility values (0-1) for each category
        for cat in categories:
            # Add some variation across members and time
            base_value = np.random.uniform(0.1, 0.9, size=n_days)
            df[cat] = base_value

        # Percentile ozone values (ppb)
        df['ozone_10pc'] = np.random.uniform(25, 45, size=n_days)
        df['ozone_50pc'] = np.random.uniform(40, 70, size=n_days)
        df['ozone_90pc'] = np.random.uniform(60, 90, size=n_days)

        # Input variables (for completeness)
        df['snow'] = np.random.uniform(0, 100, size=n_days)
        df['mslp'] = np.random.uniform(1010, 1030, size=n_days)
        df['wind'] = np.random.uniform(1, 5, size=n_days)
        df['solar'] = np.random.uniform(100, 600, size=n_days)
        df['temp'] = np.random.uniform(-10, 10, size=n_days)

        dailymax_df_dict[member] = df

    print(f"✓ Created mock data for {len(dailymax_df_dict)} members")
    return dailymax_df_dict


def test_export_products():
    """Test all 3 export products with mock data."""
    print("\nTesting export products...")

    from export.to_basinwx import (
        export_possibility_heatmaps,
        export_exceedance_probabilities,
        export_percentile_scenarios,
        export_all_products
    )

    # Create mock data
    dailymax_df_dict = create_mock_data(n_members=31, n_days=15)
    init_dt = datetime(2025, 1, 15, 12, 0, 0)  # 2025-01-15 12:00Z

    # Create temporary output directory
    with tempfile.TemporaryDirectory() as tmpdir:
        print(f"  Output directory: {tmpdir}")

        # Export all products (upload=False for testing)
        results = export_all_products(
            dailymax_df_dict=dailymax_df_dict,
            init_dt=init_dt,
            output_dir=tmpdir,
            upload=False
        )

        # Verify file counts
        n_possibility = len(results["possibility"])
        n_exceedance = len(results["exceedance"])
        n_percentiles = len(results["percentiles"])
        total = n_possibility + n_exceedance + n_percentiles

        print(f"\n  Files created:")
        print(f"    Possibility heatmaps: {n_possibility}")
        print(f"    Exceedance probabilities: {n_exceedance}")
        print(f"    Percentile scenarios: {n_percentiles}")
        print(f"    Total: {total}")

        # Expected: 31 possibility + 1 exceedance + 31 percentiles = 63
        if total == 63:
            print(f"  ✓ Correct total: 63 files")
        else:
            print(f"  ✗ Expected 63 files, got {total}")
            sys.exit(1)

        # Validate JSON structure
        print("\n  Validating JSON structure...")

        # Check possibility heatmap
        sample_file = results["possibility"][0]
        with open(sample_file, 'r') as f:
            data = json.load(f)

        assert "metadata" in data, "Missing metadata"
        assert "forecast_dates" in data, "Missing forecast_dates"
        assert "heatmap" in data, "Missing heatmap"
        assert set(data["heatmap"].keys()) == {"background", "moderate", "elevated", "extreme"}, \
            "Heatmap should have 4 categories"
        print("    ✓ Possibility heatmap structure valid")

        # Check exceedance probabilities
        exc_file = results["exceedance"][0]
        with open(exc_file, 'r') as f:
            data = json.load(f)

        assert "metadata" in data, "Missing metadata"
        assert "forecast_dates" in data, "Missing forecast_dates"
        assert "exceedance_probabilities" in data, "Missing exceedance_probabilities"
        assert data["metadata"]["num_members"] == 31, "Should have 31 members"
        print("    ✓ Exceedance probabilities structure valid")

        # Check percentile scenarios
        pct_file = results["percentiles"][0]
        with open(pct_file, 'r') as f:
            data = json.load(f)

        assert "metadata" in data, "Missing metadata"
        assert "forecast_dates" in data, "Missing forecast_dates"
        assert "scenarios" in data, "Missing scenarios"
        assert set(data["scenarios"].keys()) == {"p10", "p50", "p90"}, \
            "Should have 3 percentiles"
        print("    ✓ Percentile scenarios structure valid")

    return True


def test_no_personal_info():
    """Test that exported JSON contains no personal information."""
    print("\nTesting for personal information...")

    from export.to_basinwx import export_all_products

    dailymax_df_dict = create_mock_data(n_members=3, n_days=5)  # Small for speed
    init_dt = datetime(2025, 1, 15, 12, 0, 0)

    # Sensitive patterns to check for
    sensitive_patterns = [
        "johnlawson",
        "/Users/",
        "/home/",
        "PycharmProjects",
        "WebstormProjects"
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        results = export_all_products(
            dailymax_df_dict=dailymax_df_dict,
            init_dt=init_dt,
            output_dir=tmpdir,
            upload=False
        )

        # Check all files
        all_files = results["possibility"] + results["exceedance"] + results["percentiles"]

        for filepath in all_files:
            with open(filepath, 'r') as f:
                content = f.read()

            for pattern in sensitive_patterns:
                if pattern in content:
                    print(f"  ✗ Found '{pattern}' in {os.path.basename(filepath)}")
                    sys.exit(1)

        print(f"  ✓ No personal information found in {len(all_files)} files")

    return True


def main():
    """Run all integration tests."""
    print("=" * 60)
    print("Clyfar → BasinWx Integration Test")
    print("=" * 60)

    test_imports()
    test_environment()
    test_categories()
    test_export_products()
    test_no_personal_info()

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED ✓")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Test with real Clyfar data: python test_integration.py")
    print("2. Add export call to run_gefs_clyfar.py")
    print("3. Update website DATA_MANIFEST.json schema")
    print("4. Deploy to CHPC and test upload")


if __name__ == "__main__":
    main()
