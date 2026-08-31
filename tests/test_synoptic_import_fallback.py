import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest


def test_representative_nwp_values_imports_without_synoptic_side_effect(tmp_path):
    fake_pkg = tmp_path / "synoptic"
    fake_pkg.mkdir()
    (fake_pkg / "__init__.py").write_text("")
    (fake_pkg / "services.py").write_text("raise RuntimeError('synoptic import should not run')\n")

    repo_root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join([str(tmp_path), str(repo_root)])

    result = subprocess.run(
        [sys.executable, "-c", "import preprocessing.representative_nwp_values"],
        cwd=str(repo_root),
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert result.returncode == 0, result.stderr


def test_do_nwpval_snow_falls_back_when_recent_obs_fail(monkeypatch):
    pytest.importorskip("xarray")

    import datetime as dt
    import xarray as xr

    from preprocessing import representative_nwp_values as mod

    def fake_process_nwp_timeseries(*args, **kwargs):
        times = [dt.datetime(2026, 1, 6, 18, 0), dt.datetime(2026, 1, 7, 0, 0)]
        return xr.Dataset(
            {"sde": ("time", np.array([1.0, 1.5], dtype=float))},
            coords={"time": times},
        )

    def fake_download_most_recent(*args, **kwargs):
        raise RuntimeError("synoptic unavailable")

    monkeypatch.setattr(mod, "process_nwp_timeseries", fake_process_nwp_timeseries)
    monkeypatch.setattr(mod, "download_most_recent", fake_download_most_recent)

    snow_ts = mod.do_nwpval_snow(
        dt.datetime(2026, 1, 6, 18, 0),
        start_h=0,
        max_h=3,
        masks={"0p25": None, "0p5": None},
        delta_h=3,
        initialise_with_obs=True,
    )

    assert float(snow_ts.isel(time=0).sde.values.squeeze()) == 0.0
    assert float(snow_ts.isel(time=1).sde.values.squeeze()) == 500.0
