### Observations
This is where observation data are downloaded via Synoptic Weather API. In operations, an archive will be build where only the newest observations are saved to disk for quick (and on-the-fly) verification and safe-keeping. 

### Preprocessing
We reduce a variety of station sensor inventories, locations, and elevations to a "representative observation", the methods of which are found in `preprocessing` and discussed in technical papers/reports such as the preprint for the prototype (v0.1) and how the five fuzzy **representative** variables were created.

