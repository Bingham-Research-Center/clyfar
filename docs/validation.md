# Validation Playbook

## Local Smoke Test
- Activate the Conda env (`conda activate clyfar`).
- Run `python run_gefs_clyfar.py -i 2024010100 -n 2 -m 2 -d ./data -f ./figures --testing --log-fis` to exercise the parallel path, cache reuse, and diagnostics on a small workload.
- Inspect `performance_log.txt` if `--verbose` was set and review logged FIS means in the console.

## CHPC SLURM Template
- Upload `docs/slurm/clyfar_test.sbatch` to the cluster and adjust the account/partition walltime fields.
- Submit with `sbatch docs/slurm/clyfar_test.sbatch` after loading the Conda module or activating the virtual env in the script prologue.
- Monitor progress via `squeue -u $USER` and download the generated `clyfar_test.log` plus dated outputs under the configured data/figure roots.
