# Herbie API Cheatsheet (GEFS PRMSL Focus)

Quick reference for agents (human/AI) touching the pressure download path.

## Inventory / Metadata
```python
from herbie import Herbie
H = Herbie("2025-01-25 00:00", model="gefs", product="atmos.25", member="c00", fxx=24)
inv = H.inventory()
inv[inv["search_this"].str.contains(":PRMSL:", case=False, na=False)]
```
- PRMSL metadata: `discipline=0`, `parameterCategory=3`, `parameterNumber=1`, `typeOfLevel='meanSea'`, `stepType='instant'`.

## Structured download
```python
ds = H.xarray(
    ":PRMSL:",
    backend_kwargs={
        "filter_by_keys": {
            "shortName": "prmsl",
            "typeOfLevel": "meanSea",
            "discipline": 0,
            "parameterCategory": 3,
            "parameterNumber": 1,
            "stepType": "instant",
        },
        "indexpath": "data/herbie_cache/cfgrib_indexes/gefs_c00_atmos25_2025012500_f024.idx",
        "errors": "raise",
    },
)
```
- If cfgrib raises “cannot convert float NaN to integer”, the repo’s helper (`GEFSData.fetch_pressure`) automatically falls back to pygrib. Keep both paths until cfgrib fixes the upstream bug.

## Point extraction and conversion
```python
field = ds["prmsl"].sel(latitude=lat, longitude=lon, method="nearest")
value_hpa = (field.values * units.pascal).to(units.hectopascal).magnitude
```

## Diagnostics
- `scripts/check_mslp.py -i <init> -f 0 6 12 24 48 -m c00 -p atmos.25` prints per-hour min/max/NaN counts and surfaces cfgrib vs pygrib usage.
- `data/herbie_cache/gefs/<init>/` holds the GRIB/idx files; delete between tests to force fresh downloads.

## When editing
- Only PRMSL uses this helper today—other variables still load via `load_variable`. Don’t rip out the legacy path until each variable has a structured equivalent.
- Keep regression guard in `save_forecast_data` intact whenever touching MSLP: parquet writes must fail if `prmsl` is all NaN (operational safety net).
