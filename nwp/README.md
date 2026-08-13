# Numerical Weather Prediction Boundary

`nwp/` retrieves the GEFS fields required by the accepted forecast and keeps
cache/locking behavior isolated from inference. `preprocessing/` owns the
conversion from gridded fields to basin-representative predictors; `fis/` owns
their interpretation.

Keep Herbie data and indexes outside the checkout according to
`docs/STORAGE-GUIDE.md`. Source changes and learned bias correction require an
experiment branch and must preserve source, cycle, member, lead, units, raw
value, transformed value, and model-artifact identity. Do not hide a data-source
change inside an FIS treatment.
