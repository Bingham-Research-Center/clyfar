# clyfar
Bingham Research Center's (Utah State University) Ozone Prediction Model Clyfar

Lawson Lyman Davies 2024 

## TODOs and notes
* We may need a custom install of scikit-fuzz rather than conda version
* We need to add a `requirements.txt` file for the package
* We need a command line interface for running the FIS (with flags etc)

### Scope of Clyfar
Clyfar is the name of the prediction system itself - at least the point-of-access label of information. The fuzzy inference system, coupled with the pre-processing of observation and numerical weather prediction (NWP) data, and some post-processing (TBD!) will be part of the Clyfar system. Future work, such as a larger-scale modular approach within which Clyfar is a part, will be put in a separate package and repository.