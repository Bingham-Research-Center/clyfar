#!/usr/bin/env python3
"""
Generate an LLM-ready forecast report template for a Clyfar CASE directory.

For a given init time, this script:
- Locates data/json_tests/CASE_YYYYMMDD_HHMMZ/
- Notes which JSON + figs subfolders exist
- Optionally inlines a Q&A file for extra context
- Writes a markdown template in CASE_.../llm_text/ with:
  * 3×5-day summaries (Days 1–5, 6–10, 11–15) at three complexity levels
  * Instructions for a full (~1 page) outlook
  * Guardrails on language, units, and alert level output

Usage (from repo root):
    MPLCONFIGDIR=.mplconfig python scripts/demo_llm_forecast_template.py 2025120412
    # or
    MPLCONFIGDIR=.mplconfig python scripts/demo_llm_forecast_template.py 20251204_1200Z

Optional:
    --qa-file path/to/qa_notes.md   # additional context to paste into the prompt
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

DEFAULT_PROMPT_TEMPLATE = REPO_ROOT / "templates" / "llm" / "prompt_body.md"

def parse_init(init: str) -> str:
    """Normalise init string to 'YYYYMMDD_HHMMZ'."""
    init = init.strip()
    if "_" in init and init.endswith("Z"):
        return init
    if len(init) == 10 and init.isdigit():
        date = init[:8]
        hour = init[8:]
        hhmm = hour.ljust(4, "0")
        return f"{date}_{hhmm}Z"
    raise ValueError(f"Unrecognised init format: {init}")


def case_root_for_init(base: Path, norm_init: str) -> Path:
    """Return CASE_YYYYMMDD_HHMMZ directory for a normalised init."""
    date, hhmmz = norm_init.split("_")
    hhmm = hhmmz.replace("Z", "")
    case_id = f"CASE_{date}_{hhmm}Z"
    return base / case_id


def list_recent_cases(base: Path, limit: int = 8) -> List[str]:
    """
    List up to `limit` most recent CASE_YYYYMMDD_HHMMZ dirs under base.
    Returns their init strings 'YYYYMMDD_HHMMZ'.
    """
    cases: List[Tuple[str, Path]] = []
    for d in base.glob("CASE_*"):
        name = d.name  # CASE_YYYYMMDD_HHMMZ
        if len(name) < 5:
            continue
        try:
            case_init = name.split("CASE_")[1]
        except IndexError:
            continue
        cases.append((case_init, d))

    # Sort by init string lexicographically (works for YYYYMMDD_HHMMZ)
    cases.sort(key=lambda x: x[0])
    recent = [c[0] for c in cases[-limit:]]
    return recent


def render_prompt_template(path: Path, replacements: Dict[str, str]) -> str:
    """Return prompt instructions with {{PLACEHOLDER}} values injected."""
    text = path.read_text()
    for key, value in replacements.items():
        text = text.replace(f"{{{{{key}}}}}", value)
    return text.rstrip()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create multi-tier LLM forecast report template for a Clyfar CASE."
    )
    parser.add_argument(
        "init",
        help="Init time as YYYYMMDDHH or YYYYMMDD_HHMMZ (e.g. 2025120412 or 20251204_1200Z)",
    )
    parser.add_argument(
        "--qa-file",
        type=str,
        default=None,
        help="Optional path to a Q&A markdown/text file with case-specific notes.",
    )
    parser.add_argument(
        "--prompt-template",
        type=str,
        default=os.environ.get("LLM_PROMPT_TEMPLATE", str(DEFAULT_PROMPT_TEMPLATE)),
        help=f"Path to the markdown template used for the prompt body (default: {DEFAULT_PROMPT_TEMPLATE}).",
    )
    args = parser.parse_args()

    data_root = REPO_ROOT / "data" / "json_tests"
    if not data_root.exists():
        raise SystemExit(f"Data directory not found: {data_root}")

    norm_init = parse_init(args.init)
    case_root = case_root_for_init(data_root, norm_init)
    if not case_root.exists():
        raise SystemExit(f"Case directory not found: {case_root}")

    figs_root = case_root / "figs"
    json_subdirs = {
        "percentiles": case_root / "percentiles",
        "probs": case_root / "probs",
        "possibilities": case_root / "possibilities",
    }
    figs_subdirs = {
        "quantities": figs_root / "quantities",
        "probabilities": figs_root / "probabilities",
        "scenarios_percentiles": figs_root / "scenarios_percentiles",
        "scenarios_possibility": figs_root / "scenarios_possibility",
        "possibility_heatmaps": figs_root / "possibility" / "heatmaps",
        "dendrograms_percentiles": figs_root / "dendrograms" / "percentiles",
        "dendrograms_possibilities": figs_root / "dendrograms" / "possibilities",
    }

    qa_text = None
    if args.qa_file:
        qa_path = Path(args.qa_file).expanduser()
        if qa_path.exists():
            qa_text = qa_path.read_text()

    recent_cases = list_recent_cases(data_root, limit=8)

    llm_dir = case_root / "llm_text"
    llm_dir.mkdir(parents=True, exist_ok=True)
    out_path = llm_dir / f"forecast_prompt_{norm_init}.md"

    lines: list[str] = []
    lines.append(f"# Clyfar Forecast – LLM Report Template ({norm_init})")
    lines.append("")
    lines.append("## Case metadata")
    lines.append("")
    lines.append(f"- Init time: `{norm_init}`")
    lines.append(f"- Case root: `{case_root}`")
    for name, path in json_subdirs.items():
        status = "present" if path.exists() else "missing"
        lines.append(f"- JSON · {name}: `{path}` ({status})")

    lines.append("")
    lines.append("## Figure subfolders")
    lines.append("")
    desc = {
        "quantities": "Boxplots, ensemble fan, and histogram for p10/p50/p90 (ozone ppb).",
        "probabilities": "Exceedance probability lines, bar charts, and threshold×day heatmap.",
        "scenarios_percentiles": "Scenario envelopes and medoid percentile fans built from ppb percentiles.",
        "scenarios_possibility": "Scenario‑mean category heatmaps and high‑risk fractions (P(elev+ext) > threshold).",
        "possibility_heatmaps": "Per‑member daily‑max category heatmaps in the same style as operational Clyfar output.",
        "dendrograms_percentiles": "Dendrogram of clustering in percentile space (p50/p90).",
        "dendrograms_possibilities": "Dendrogram of clustering in possibility space (elevated/extreme).",
    }
    for name, path in figs_subdirs.items():
        if path.exists():
            lines.append(f"- `{name}` → `{path}` – {desc[name]}")

    lines.append("")
    lines.append("## Recent cases (for run-to-run context)")
    lines.append("")
    if recent_cases:
        lines.append("| Init | Case path |")
        lines.append("|------|-----------|")
        for c in recent_cases:
            marker = " (this case)" if c == norm_init else ""
            case_dir = case_root_for_init(data_root, c)
            if case_dir.exists():
                lines.append(f"| `{c}`{marker} | `{case_dir}` |")
            else:
                lines.append(f"| `{c}`{marker} | (not present locally) |")
    else:
        lines.append("- (no other CASE_ directories found)")

    if qa_text:
        lines.append("")
        lines.append("## Q&A context (for LLM only)")
        lines.append("")
        lines.append("> The following notes come from forecaster Q&A or diagnostics.")
        lines.append("> You may use them to refine the discussion, but do not echo them verbatim.")
        lines.append("")
        for line in qa_text.splitlines():
            lines.append(f"> {line}")
        lines.append("")
        lines.append("**Directive:** If the Q&A mentions data quality issues or cautions, restate that warning in every section (public, stakeholder, expert, and full outlook).")

    template_path = Path(args.prompt_template).expanduser()
    if not template_path.exists():
        raise SystemExit(f"Prompt template not found: {template_path}")
    replacements = {
        "INIT": norm_init,
        "CASE_ROOT": str(case_root),
        "RECENT_CASE_COUNT": str(len(recent_cases)),
    }
    lines.append("")
    lines.append(render_prompt_template(template_path, replacements))

    out_path.write_text("\n".join(lines))
    print(f"Wrote LLM forecast prompt to {out_path}")


if __name__ == "__main__":
    if "MPLCONFIGDIR" not in os.environ:
        os.environ["MPLCONFIGDIR"] = ".mplconfig"
    main()
