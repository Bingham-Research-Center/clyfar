# External Data and Model References

Authoritative links for the frozen fork's GEFS/Herbie data path.

## GEFS inventories
- https://www.nco.ncep.noaa.gov/pmb/products/gens/gep01.t00z.pgrb2a.0p50.f003.shtml  
  Official NCO page for a single GEFS perturbation member (here `gep01`, 00Z init, 0.5° grid, 3-h forecast). Shows the exact GRIB2 message inventory (discipline/category/parameter, typeOfLevel, units). Use this to cross-check cfgrib `filter_by_keys` when PRMSL lookups fail.
- https://www.nco.ncep.noaa.gov/pmb/products/gens/  
  Root directory listing all GEFS public products. Helpful to verify which grids (0.25° vs 0.5°) and forecast cycles are currently published.

## Herbie references
- https://github.com/blaylockbk/Herbie  
  Upstream source with release notes and usage examples. Resolve the deployed
  version from the active environment rather than this document.
- https://herbie.readthedocs.io/en/stable/gallery/noaa_models/gefs.html  
  Official Herbie gallery notebook for GEFS. Documents the structured `filter_by_keys` patterns we should mirror in `GEFSData.fetch_pressure`.
