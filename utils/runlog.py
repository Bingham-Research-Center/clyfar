import json
import os
import subprocess
from typing import Any, Dict, Optional


def _git_commit_hash() -> Optional[str]:
    try:
        out = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True)
        return out.strip()
    except Exception:
        return None


def write_run_summary(
    data_root: str,
    run_id: str,
    summary: Dict[str, Any],
) -> str:
    """Write a compact JSON summary for a run under data/<run_id>/run.json.

    Args:
        data_root: Base data directory for outputs.
        run_id: Unique identifier for the run (e.g., init time stamp).
        summary: Dict containing run metadata and diagnostics.

    Returns:
        The path written to.
    """
    out_dir = os.path.join(data_root, str(run_id))
    os.makedirs(out_dir, exist_ok=True)

    # Attach code commit hash if available
    if "code_commit" not in summary or not summary["code_commit"]:
        summary["code_commit"] = _git_commit_hash()

    out_path = os.path.join(out_dir, "run.json")
    with open(out_path, "w") as f:
        json.dump(summary, f, indent=2, sort_keys=True)
    return out_path

