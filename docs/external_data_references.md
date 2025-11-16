# External Data and Model References

Authoritative links for GEFS/Herbie work (pressure fixes now) plus future HRRR/RRFS/AQM hooks. Keep them handy for system admin + science review.

## GEFS inventories
- https://www.nco.ncep.noaa.gov/pmb/products/gens/gep01.t00z.pgrb2a.0p50.f003.shtml  
  Official NCO page for a single GEFS perturbation member (here `gep01`, 00Z init, 0.5° grid, 3-h forecast). Shows the exact GRIB2 message inventory (discipline/category/parameter, typeOfLevel, units). Use this to cross-check cfgrib `filter_by_keys` when PRMSL lookups fail.
- https://www.nco.ncep.noaa.gov/pmb/products/gens/  
  Root directory listing all GEFS public products. Helpful to verify which grids (0.25° vs 0.5°) and forecast cycles are currently published.

## Herbie references
- https://github.com/blaylockbk/Herbie  
  Upstream source with release notes and usage examples. Check here when we suspect a version regression; current env runs `herbie-data==2025.11.1` (`python -m pip show herbie-data`).
- https://herbie.readthedocs.io/en/stable/gallery/noaa_models/gefs.html  
  Official Herbie gallery notebook for GEFS. Documents the structured `filter_by_keys` patterns we should mirror in `GEFSData.fetch_pressure`.

## HRRR / RRFS / AQM for future versions
- https://registry.opendata.aws/noaa-hrrr-pds/  
  AWS Open Data registry for HRRR (v1.0 target). Contains bucket layout and sample queries.
- https://www.nco.ncep.noaa.gov/pmb/products/aqm/ and https://www.nco.ncep.noaa.gov/pmb/products/aqm/aqm.t06z.ave_8hr_o3.227.grib2.shtml  
  NCO AQMs (ozone, PM) inventory pages; use when we integrate NAQFC products into downstream verification.
- https://registry.opendata.aws/noaa-nws-naqfc-pds/ and https://noaa-nws-naqfc-pds.s3.amazonaws.com/index.html#AQMv7/CS/20250407/12/  
  AWS buckets for NAQFC (AQMv7). Capture the path anatomy we’ll need for automated downloads.
- https://github.com/NOAA-EMC/rrfs-workflow  
  RRFS workflow repository (successor to HRRR). Track here for v1.1+ planning when we extend beyond GEFS/HRRR.
