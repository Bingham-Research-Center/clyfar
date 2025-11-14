# clyfar
Bingham Research Center's (Utah State University) Ozone Prediction Model Clyfar

Written for Python 3.11.9. Using anaconda with conda-forge. Package requirements information should be updated in `requirements.txt`.

Lawson, Lyman, Davies, 2024 

## TODOs and notes
* We may need a custom install of scikit-fuzz rather than conda version
* We need to add a `requirements.txt` file for the package
* We need a command line interface for running the FIS (with flags etc)

### Scope of Clyfar
Clyfar is the name of the prediction system itself - at least the point-of-access label of information. The fuzzy inference system, coupled with the pre-processing of observation and numerical weather prediction (NWP) data, and some post-processing (TBD!) will be part of the Clyfar system. Future work, such as a larger-scale modular approach within which Clyfar is a part, will be put in a separate package and repository.

## Related Repositories and Knowledge Base
- Technical report (LaTeX, local path): `/Users/johnlawson/Documents/GitHub/preprint-clyfar-v0p9`
- Knowledge base (local path): `/Users/johnlawson/Documents/GitHub/brc-knowledge`
- BRC operational tools (local path): `../brc-tools` (sibling to this repo)

Notes
- These are referenced for documentation and operations; clone or mount as needed.
- Keep them out of the token working set unless required for a task.

## Live session logging
- Append notes with `scripts/livelog` or `echo` to `docs/session_log.md`; PyCharm (or any editor) will follow that file as it changes.
- Capture full terminal output (AI agents or CLI apps) with standard tools:
  - `script -f docs/session_log.md` (records everything until you exit) works on both macOS Tahoe and Ubuntu.
  - In tmux: `tmux pipe-pane -o 'cat >> docs/session_log.md'` (enable where you want streaming, disable afterward).
  - Per-command: `yourcmd 2>&1 | tee -a docs/session_log.md` keeps the transcript on screen while persisting it.
- For Vim tailing, install the dotfiles (`~/dotfiles/install.sh`) so `vim-dispatch` is available; then run `:Dispatch tail -f docs/session_log.md` or `<leader>tl` while editing to keep a live tail inside the editor (see `~/dotfiles/README.md` for more detail).
