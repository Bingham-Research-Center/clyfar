## Numerical Weather Prediction data
We focus mainly on GEFS 0.25 degree (about 25km) grid spacing. We can obtain the cells over the Basin and combine them with methods in `preprocessing` and generate representative forecast values similarly to those created by representative observations (e.g., 99th percentile of all stations' median value for a given day).

### Preprocessing
To get the forecast values into the best proxy for observations, we error-correct. The method of this error correction is a topic of research (e.g., neural networks). 

### Future
* Most efficient way of downloading GEFS data for each ensemble member without storing huge files on disk.
* Might consider RRFS and HRRR data for higher resolution forecasts.
* 