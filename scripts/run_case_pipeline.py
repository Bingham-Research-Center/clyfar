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
DATA_ROOT = REPO_ROOT / "data" / "json_tests"


def normalise_init(init: str) -> str:
    """Return init as YYYYMMDD_HHMMZ."""
    init = init.strip()
    if "_" in init and init.endswith("Z"):
        return init
    if len(init) == 10 and init.isdigit():
        date = init[:8]
        hour = init[8:]
        hhmm = hour.ljust(4, "0")
        return f"{date}_{hhmm}Z"
    raise ValueError(f"Unrecognised init format: {init}")


def case_root_for_init(norm_init: str) -> Path:
    """Return CASE_YYYYMMDD_HHMMZ directory path."""
    date, hhmmz = norm_init.split("_")
    hhmm = hhmmz.replace("Z", "")
    case_id = f"CASE_{date}_{hhmm}Z"
    return DATA_ROOT / case_id


def check_case_complete(norm_init: str) -> bool:
    """Check if CASE directory exists and has required JSON files."""
    case_root = case_root_for_init(norm_init)
    if not case_root.exists():
        return False

    checks = {
        "percentiles": f"forecast_percentile_scenarios_*_{norm_init}.json",
        "probs": f"forecast_exceedance_probabilities*{norm_init}.json",
        "possibilities": f"forecast_possibility_heatmap_*_{norm_init}.json",
    }
    for subdir, pattern in checks.items():
        folder = case_root / subdir
        if not folder.exists() or not any(folder.glob(pattern)):
            return False
    clustering_file = case_root / f"forecast_clustering_summary_{norm_init}.json"
    if not clustering_file.exists():
        return False
    return True


def ensure_case_present(norm_init: str) -> None:
    """Ensure the CASE directory (and JSON subfolders) exist for the init."""
    case_root = case_root_for_init(norm_init)
    if not case_root.exists():
        raise SystemExit(
            f"CASE directory not found for {norm_init}: {case_root}\n"
            "Fetch it first via scripts/fetch_case_from_api.py (or run with --from-api / LLM_FROM_API=1)."
        )

    missing: list[str] = []
    checks = {
        "percentiles": f"forecast_percentile_scenarios_*_{norm_init}.json",
        "probs": f"forecast_exceedance_probabilities*{norm_init}.json",
        "possibilities": f"forecast_possibility_heatmap_*_{norm_init}.json",
    }
    for subdir, pattern in checks.items():
        folder = case_root / subdir
        if not folder.exists():
            missing.append(f"{subdir} (directory missing)")
            continue
        if not any(folder.glob(pattern)):
            missing.append(f"{subdir} (no files matching {pattern})")
    if missing:
        details = "; ".join(missing)
        raise SystemExit(
            f"CASE {case_root} is incomplete: {details}.\n"
            "Refetch the init or verify the JSON placement before rerunning."
        )

    clustering_file = case_root / f"forecast_clustering_summary_{norm_init}.json"
    if not clustering_file.exists():
        print(
            "Warning: clustering summary not found in CASE payload; "
            "it will be regenerated locally before LLM prompt rendering."
        )

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

    norm_init = normalise_init(args.init)

    # 1) Check if local data exists; fetch from API only if missing or explicitly requested
    local_complete = check_case_complete(norm_init)
    if local_complete and not args.from_api:
        print(f"Local CASE data found and complete for {norm_init}, skipping API fetch.")
    elif args.from_api or not local_complete:
        if not local_complete:
            print(f"Local CASE data missing or incomplete for {norm_init}, fetching from API...")
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

    # Ensure the CASE exists (should be present now)
    ensure_case_present(norm_init)

    # 2) Generate plots and LLM prompt
    script_cmds = [
        ["scripts/demo_quantities.py", args.init],
        ["scripts/demo_probabilities.py", args.init],
        ["scripts/demo_scenarios_clusters.py", args.init],
        ["scripts/demo_scenarios_possibility.py", args.init],
        ["scripts/demo_heatmaps_from_json.py", args.init],
        ["scripts/generate_clustering_summary.py", args.init],  # GEFS↔Clyfar linkage for LLM
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
