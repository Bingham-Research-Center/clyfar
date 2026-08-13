# Preprocessing Boundary

This package converts observations and NWP fields into the representative
predictors consumed by the production FIS. The accepted four-input contract is
defined by `fis/v0p9.py`; preprocessing must preserve its names, units, time
meaning, and missing-data behavior.

Pseudo-lapse-rate estimation and source-bias correction are experimental
treatments, not silent replacements for the accepted inputs. Develop each on a
separate branch, retain raw and transformed values together, and fit every
learned transform strictly out of sample. A fifth FIS input requires an explicit
matching FIS treatment and provenance; adding a column alone is not sufficient.
