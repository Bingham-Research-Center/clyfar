### Observations
This is where observation data are downloaded via Synoptic Weather API. In operations, an archive will be build where only the newest observations are saved to disk for quick (and on-the-fly) verification and safe-keeping. 

### Preprocessing
We reduce a variety of station sensor inventories, locations, and elevations to a "representative observation", the methods of which are found in `preprocessing` and discussed in technical papers/reports such as the preprint for the prototype (v0.1) and how the five fuzzy **representative** variables were created.

Daily reducers do not shift observations to the following day.  The ozone
verification target is different from the other daily predictors: it uses
fixed Mountain Standard Time (UTC-07:00), even after the civil clock changes
to daylight time.  For each station it forms the 17 eight-hour windows
beginning 07:00--23:00 standard time, applies the declared completeness rules,
and retains the earliest unrounded maximum daily 8-hour average (MDA8) on a
tie.  An independent whole-ppb truncation audit likewise selects its own
earliest maximum, so a precision-induced change of peak window remains
visible.  The Basin value is the declared cross-station quantile of eligible
station MDA8 values.  Window counts, selected times, truncation diagnostics,
and absent
requested stations remain audit data.  This is EPA-aligned data handling from
Synoptic observations, not an AQS compliance or design-value calculation.
