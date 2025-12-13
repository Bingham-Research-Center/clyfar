#!/usr/bin/env python3
"""
Run the full CASE pipeline for a given Clyfar forecast init.

This orchestrates:
 - Optional fetch from BasinWx API into CASE_YYYYMMDD_HHMMZ/
 - Plot generation:
     * Quantities (ppb)
     * Exceedance probabilities
     * Percentile-based scenarios
     * Possibility-based scenarios
     * Daily-max category heatmaps
 - LLM forecast prompt template

Usage (from repo root):
    MPLCONFIGDIR=.mplconfig python scripts/run_case_pipeline.py --init 2025121200 --from-api --base-url https://basinwx.com

You can also run it purely on local data by omitting --from-api.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the full CASE pipeline (fetch JSON, plots, LLM prompt) for a Clyfar init."
    )
    parser.add_argument(
        "--init",
        required=True,
        help="Init time as YYYYMMDDHH or YYYYMMDD_HHMMZ (e.g. 2025121200 or 20251212_0000Z)",
    )
    parser.add_argument(
        "--from-api",
        action="store_true",
        help="Fetch JSON from BasinWx API before generating plots/text.",
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("BASINWX_API_URL", "https://basinwx.com"),
        help="Base URL for BasinWx when using --from-api.",
    )
    parser.add_argument(
        "--history",
        type=int,
        default=5,
        help="Number of 6-hour inits (current + past) to ensure exist (default 5).",
    )
    parser.add_argument(
        "--qa-file",
        help="Optional path to a Q&A markdown file to include in the LLM prompt.",
    )
    args = parser.parse_args()

    # Ensure MPLCONFIGDIR is set
    env = os.environ.copy()
    if "MPLCONFIGDIR" not in env:
        env["MPLCONFIGDIR"] = ".mplconfig"

    # 1) Optionally fetch JSON from API into CASE_ dir
    if args.from_api:
        cmd = [
            sys.executable,
            str(REPO_ROOT / "scripts" / "fetch_case_from_api.py"),
            "--init",
            args.init,
            "--base-url",
            args.base_url,
            "--history",
            str(args.history),
        ]
        print("Running:", " ".join(cmd))
        subprocess.run(cmd, check=True, env=env, cwd=str(REPO_ROOT))

    # 2) Generate plots and LLM prompt
    script_cmds = [
        ["scripts/demo_quantities.py", args.init],
        ["scripts/demo_probabilities.py", args.init],
        ["scripts/demo_scenarios_clusters.py", args.init],
        ["scripts/demo_scenarios_possibility.py", args.init],
        ["scripts/demo_heatmaps_from_json.py", args.init],
    ]

    for rel_script, init_arg in script_cmds:
        cmd = [sys.executable, str(REPO_ROOT / rel_script), init_arg]
        print("Running:", " ".join(cmd))
        subprocess.run(cmd, check=True, env=env, cwd=str(REPO_ROOT))

    # LLM prompt template (handle optional QA file)
    llm_cmd = [sys.executable, str(REPO_ROOT / "scripts" / "demo_llm_forecast_template.py"), args.init]
    if args.qa_file:
        llm_cmd.extend(["--qa-file", args.qa_file])
    print("Running:", " ".join(llm_cmd))
    subprocess.run(llm_cmd, check=True, env=env, cwd=str(REPO_ROOT))

    print("CASE pipeline complete.")


if __name__ == "__main__":
    main()
