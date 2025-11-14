# clyfar
Bingham Research Center's (Utah State University) Ozone Prediction Model Clyfar

Written for Python 3.11.9. Using anaconda with conda-forge. Package requirements information should be updated in `requirements.txt`.

Lawson, Lyman, Davies, 2024 

## Environment setup
1. Install/initialize Miniforge or Conda (see [docs/setup_conda.md](docs/setup_conda.md) for platform specifics).
2. Create the env: `conda create -n clyfar python=3.11.9 -y` then `conda activate clyfar`.
3. Install packages: `pip install -r requirements.txt`.
4. Run the smoke test to validate: `python run_gefs_clyfar.py -i 2024010100 -n 2 -m 2 -d ./data -f ./figures --testing`.

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
  - Linux: `script -f docs/session_log.md`; macOS uses `script -F docs/session_log.md` because `/usr/bin/script` lacks `-f`.
  - In tmux: `tmux pipe-pane -o 'cat >> docs/session_log.md'` (enable where you want streaming, disable afterward).
  - Per-command: `yourcmd 2>&1 | tee -a docs/session_log.md` keeps the transcript on screen while persisting it.
- For Vim tailing, install the dotfiles (`~/dotfiles/install.sh`) so `vim-dispatch` is available; then run `:Dispatch tail -f docs/session_log.md` or `<leader>tl` while editing to keep a live tail inside the editor (see `~/dotfiles/README.md` for more detail).
