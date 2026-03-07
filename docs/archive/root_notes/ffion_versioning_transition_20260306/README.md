# Ffion Versioning Transition Archive
Date archived: 2026-03-06

Archived here during the cleanup that collapsed the old `ffion_science` naming layer into the single `FFION_VERSION` axis.

Archived items:
- `scripts/resolve_ffion_science.py`
- `utils/ffion_science.py`
- `templates/llm/short_term_biases.json`

Canonical replacements in the live tree:
- resolver module: `utils/ffion_bundle.py`
- resolver CLI: `scripts/resolve_ffion_bundle.py`
- versioned bundle registry: `templates/llm/ffion_registry.json`
- active bias file for current Ffion release: `templates/llm/biases/ffion_biases_v1.1.3.json`

Reason:
- keep only two live version axes: repo-wide Clyfar and Ffion
- remove duplicate live aliases that could drift or confuse reforecast provenance
- preserve the old transition files in a dated archive rather than deleting them outright
