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
from typing import List, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


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

    lines.append("")
    lines.append("## Prompt for the language model")
    lines.append("")
    lines.append("Use American English and U.S. units (°F, mph, feet, etc.).")
    lines.append("Assume the reader already understands basic ozone / air quality concepts.")
    lines.append("")
    lines.append("```text")
    lines.append("You are helping explain a Clyfar ozone forecast for the Uintah Basin.")
    lines.append(f"The forecast init is {norm_init}.")
    lines.append(f"The case directory on disk is `{case_root}`.")
    lines.append(f"The previous {len(recent_cases)} cases are listed in the metadata table above; use them for run-to-run consistency checks if needed.")
    lines.append("")
    lines.append("You have three main data sources:")
    lines.append("1) Quantities in ppb (p10/p50/p90) with ensemble distributions.")
    lines.append("2) Exceedance probabilities for thresholds (e.g., >30, >50, >60, >75 ppb).")
    lines.append("3) Possibility‑based scenarios (background/moderate/elevated/extreme) and clustering outputs.")
    lines.append("")
    lines.append("If any Q&A context above warns about data quality or known issues, you must repeat that warning in every section you produce.")
    lines.append("")
    lines.append("### Task 1 – Three 5-day summaries at three complexity levels")
    lines.append("")
    lines.append("For each block (Days 1–5, Days 6–10, Days 11–15), write:")
    lines.append("a) A 3-sentence summary for the general public (field workers, residents).")
    lines.append("b) A 3-sentence summary for mid-tier stakeholders (policy, general scientists, industry).")
    lines.append("c) A 3-sentence summary for experts (forecasters, ozone specialists).")
    lines.append("")
    lines.append("Guidance:")
    lines.append("- Keep all text concise and concrete; avoid repetition across levels.")
    lines.append("- Do *not* explain what ozone is; assume the audience already knows.")
    lines.append("- Use ppb ranges and probabilities to differentiate typical vs higher-ozone scenarios.")
    lines.append("- Refer to scenarios qualitatively (e.g., “most model runs”, “a small minority of runs”).")
    lines.append("")
    lines.append("### Task 2 – Full-length (~1 page) outlook")
    lines.append("")
    lines.append("Write a single, cohesive outlook (~1 printed page) that:")
    lines.append("- Explains the overall pattern across Days 1–15.")
    lines.append("- Describes the scenario logic: dominant clusters vs tail/high-ozone clusters, in plain terms.")
    lines.append("- Summarises accessible ranges of daily maximum ozone at one or more key sites.")
    lines.append("- Notes any consistency or shifts compared with recent runs (if that information was provided).")
    lines.append("- Uses U.S. units and terminology appropriate for professional but time-constrained readers.")
    lines.append("")
    lines.append("Structure:")
    lines.append("- Start with the big picture (most likely outcome).")
    lines.append("- Then describe less likely but higher-impact scenarios.")
    lines.append("- End with a brief statement about confidence and what to watch in upcoming runs.")
    lines.append("")
    lines.append("### Task 3 – Alert level for the website")
    lines.append("")
    lines.append("Based on all of the above, assign a single alert level for the forecast period as a whole:")
    lines.append("- LOW – background ozone, no meaningful high-ozone risk expected.")
    lines.append("- MODERATE – some chance of higher ozone on a few days, but not strongly signaled.")
    lines.append("- HIGH – strong signal for one or more high-ozone days.")
    lines.append("- EXTREME – persistent or widespread high-ozone conditions likely.")
    lines.append("")
    lines.append("Output this in a machine-readable form *at the very end* of your response as a single line:")
    lines.append("AlertLevel: LOW | MODERATE | HIGH | EXTREME")
    lines.append("")
    lines.append("### Output formatting")
    lines.append("")
    lines.append("1) First, three sections for Days 1–5, 6–10, 11–15, each containing:")
    lines.append("   - Public paragraph")
    lines.append("   - Stakeholder paragraph")
    lines.append("   - Expert paragraph")
    lines.append("2) Second, a full-length outlook section (~1 page).")
    lines.append("3) Finally, the single alert level line as specified above.")
    lines.append("```")

    lines.append("")
    lines.append("## Notes for the forecaster / operator")
    lines.append("")
    lines.append("- Before sending this prompt to an LLM, you may want to:")
    lines.append("  * Edit in any specific day/threshold highlights you care about.")
    lines.append("  * Trim sections that are not relevant for a particular event.")
    lines.append("- For high-ozone but uncertain events, focus the expert text on how many members occupy tail clusters and how often they exceed key thresholds.")
    lines.append("- You can reuse this template across cases by re-running the script with a different init and, optionally, a different Q&A file.")

    out_path.write_text("\n".join(lines))
    print(f"Wrote LLM forecast prompt to {out_path}")


if __name__ == "__main__":
    if "MPLCONFIGDIR" not in os.environ:
        os.environ["MPLCONFIGDIR"] = ".mplconfig"
    main()
