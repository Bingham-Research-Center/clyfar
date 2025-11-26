#!/usr/bin/env python
"""
Bottom-up MSLP pipeline test.
Run from clyfar root: python scripts/test_mslp_pipeline.py

Tests each step of the MSLP data flow to isolate failures.
"""
import sys
import traceback
from datetime import datetime
from multiprocessing import get_context


def test_step(name, fn):
    """Run test, print result, return success."""
    try:
        result = fn()
        print(f"✓ {name}: {result}")
        return True
    except Exception as e:
        print(f"✗ {name}: {e}")
        traceback.print_exc()
        return False


def main():
    init_dt = datetime(2025, 11, 24, 0)
    print(f"Testing MSLP pipeline for init={init_dt}\n")

    # Step 1: Raw Herbie - does the basic download work?
    def step1():
        from herbie import Herbie
        H = Herbie(init_dt, model='gefs', product='atmos.5', member='p01', fxx=360)
        ds = H.xarray(':PRMSL:', remove_grib=True)
        var = list(ds.data_vars.values())[0]
        return f"shape={var.shape}, time.shape={ds.time.shape}, time.ndim={ds.time.values.ndim}"

    # Step 2: GEFSData.fetch_pressure - does our wrapper work?
    def step2():
        from nwp.gefsdata import GEFSData
        ds = GEFSData.fetch_pressure(init_dt, fxx=360, product='atmos.5', member='p01')
        return f"prmsl.shape={ds.prmsl.shape}, range={float(ds.prmsl.min()):.0f}-{float(ds.prmsl.max()):.0f} Pa"

    # Step 3: Time extraction - test both scalar and array handling
    def step3():
        from nwp.gefsdata import GEFSData
        import pandas as pd
        import numpy as np
        ds = GEFSData.fetch_pressure(init_dt, fxx=360, product='atmos.5', member='p01')
        time_val = ds.time.values

        # Check what we're dealing with
        is_scalar = hasattr(time_val, 'ndim') and time_val.ndim == 0

        # Robust extraction that handles both cases
        if is_scalar:
            valid_time = pd.to_datetime(time_val.item())
        else:
            valid_time = pd.to_datetime(time_val[0])

        return f"time.ndim={getattr(time_val, 'ndim', 'N/A')}, is_scalar={is_scalar}, valid_time={valid_time}"

    # Step 4: Point extraction - does sel() work correctly?
    def step4():
        from nwp.gefsdata import GEFSData
        ds = GEFSData.fetch_pressure(init_dt, fxx=360, product='atmos.5', member='p01')
        lat, lon = 40.0891, -109.6774  # Ouray coordinates
        field = ds.prmsl.sel(latitude=lat, longitude=lon, method="nearest")
        value = float(field.squeeze().values)
        return f"value={value:.0f} Pa at ({lat}, {lon})"

    # Step 5: do_nwpval_mslp with single hour (to minimize time)
    def step5():
        from preprocessing.representative_nwp_values import do_nwpval_mslp
        # Use delta_h=384 to only fetch f0 and f384 (2 points)
        df = do_nwpval_mslp(init_dt, lat=40.0891, lon=-109.6774, delta_h=240, member='p01')
        first_val = df.iloc[0]['prmsl']
        last_val = df.iloc[-1]['prmsl']
        return f"len={len(df)}, first={first_val:.1f} hPa, last={last_val:.1f} hPa"

    # Step 6: In spawn worker - does multiprocessing break anything?
    def step6():
        def worker_fn():
            from datetime import datetime
            from nwp.gefsdata import GEFSData
            ds = GEFSData.fetch_pressure(datetime(2025, 11, 24, 0), fxx=360, product='atmos.5', member='p01')
            return f"{float(ds.prmsl.min()):.0f}-{float(ds.prmsl.max()):.0f} Pa"

        with get_context('spawn').Pool(1) as pool:
            result = pool.apply(worker_fn)
        return f"spawn worker returned: {result}"

    steps = [
        ("1. Raw Herbie xarray", step1),
        ("2. GEFSData.fetch_pressure", step2),
        ("3. Time extraction (robust)", step3),
        ("4. Point extraction with sel()", step4),
        ("5. do_nwpval_mslp (limited hours)", step5),
        ("6. Spawn worker context", step6),
    ]

    print("-" * 60)
    passed = 0
    for name, fn in steps:
        if test_step(name, fn):
            passed += 1
        print()

    print("-" * 60)
    print(f"\n{passed}/{len(steps)} tests passed")

    if passed < len(steps):
        print("\nFirst failing step indicates where the bug is.")

    return 0 if passed == len(steps) else 1


if __name__ == "__main__":
    sys.exit(main())
