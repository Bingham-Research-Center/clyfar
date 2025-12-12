#!/usr/bin/env python3
"""
Create an LLM-ready summary template for a Clyfar forecast CASE_* directory.

For a given init time, this script:
 - Locates the case root under data/json_tests/CASE_YYYYMMDD_HHMMZ/
 - Detects which JSON + figs subfolders exist
 - Writes a markdown file under CASE_.../llm_text/ with:
     * Case metadata and paths
     * A concise description of each figs subfolder
     * A prompt template instructing an LLM to produce 3-tier explanations

Usage (from repo root):
    MPLCONFIGDIR=.mplconfig python scripts/demo_llm_text_template.py 2025120412
    # or
    MPLCONFIGDIR=.mplconfig python scripts/demo_llm_text_template.py 20251204_1200Z
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure repo root is on sys.path
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def parse_init(init: str) -> str:
    """
    Normalise init string to 'YYYYMMDD_HHMMZ'.

    Accepts either 'YYYYMMDD_HHMMZ' or 'YYYYMMDDHH'.
    """
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


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Create LLM summary markdown template for a Clyfar CASE directory."
    )
    parser.add_argument(
        "init",
        help="Init time as YYYYMMDDHH or YYYYMMDD_HHMMZ (e.g. 2025120412 or 20251204_1200Z)",
    )
    args = parser.parse_args()

    data_root = REPO_ROOT / "data" / "json_tests"
    if not data_root.exists():
        raise SystemExit(f"Data directory not found: {data_root}")

    norm_init = parse_init(args.init)
    case_root = case_root_for_init(data_root, norm_init)
    if not case_root.exists():
        raise SystemExit(f"Case directory not found: {case_root}")

    # Figure directories
    figs_root = case_root / "figs"
    figs_subdirs = {
        "quantities": figs_root / "quantities",
        "probabilities": figs_root / "probabilities",
        "scenarios_percentiles": figs_root / "scenarios_percentiles",
        "scenarios_possibility": figs_root / "scenarios_possibility",
        "possibility_heatmaps": figs_root / "possibility" / "heatmaps",
    }

    # JSON product directories
    json_subdirs = {
        "percentiles": case_root / "percentiles",
        "probs": case_root / "probs",
        "possibilities": case_root / "possibilities",
    }

    llm_dir = case_root / "llm_text"
    llm_dir.mkdir(parents=True, exist_ok=True)
    out_path = llm_dir / f"summary_{norm_init}.md"

    lines: list[str] = []
    lines.append(f"# LLM Summary Template – Clyfar forecast {norm_init}")
    lines.append("")
    lines.append("## Case metadata")
    lines.append("")
    lines.append(f"- Init time: `{norm_init}`")
    lines.append(f"- Case root: `{case_root}`")
    for name, path in json_subdirs.items():
        status = "present" if path.exists() else "missing"
        lines.append(f"- JSON · {name}: `{path}` ({status})")

    lines.append("")
    lines.append("## Available figure subfolders")
    lines.append("")
    desc = {
        "quantities": "Boxplots, ensemble fan, and histogram for p10/p50/p90 (ozone ppb).",
        "probabilities": "Exceedance probability time series, bar charts, and threshold×day heatmap.",
        "scenarios_percentiles": "Scenario envelopes and medoid percentile fans built from ppb percentiles.",
        "scenarios_possibility": "Scenario‑mean category heatmaps and high‑risk fractions (P(elev+ext) > threshold).",
        "possibility_heatmaps": "Per‑member daily‑max category heatmaps in the same style as the operational Clyfar plots.",
    }
    for name, path in figs_subdirs.items():
        if path.exists():
            lines.append(f"- `{name}` → `{path}` – {desc[name]}")

    lines.append("")
    lines.append("## Suggested LLM prompt")
    lines.append("")
    lines.append("You can copy/paste and edit this prompt for each case:")
    lines.append("")
    lines.append("```text")
    lines.append(f"You are helping explain a Clyfar ozone forecast for the Uintah Basin.")
    lines.append(f"The forecast init is {norm_init}.")
    lines.append(f"The case directory on disk is `{case_root}`.")
    lines.append("")
    lines.append("You have three types of information:")
    lines.append("1) Quantities in ppb (p10/p50/p90) with ensemble distributions.")
    lines.append("2) Exceedance probabilities for thresholds (e.g. >30, >50, >60, >75 ppb).")
    lines.append("3) Possibility‑based scenarios (background/moderate/elevated/extreme) and cluster summaries.")
    lines.append("")
    lines.append("Task A – Public summary (layperson):")
    lines.append("- Write 2–3 short paragraphs in plain language for field workers and residents.")
    lines.append("- Avoid acronyms; define ppb as “parts per billion” and probabilities as a simple chance out of 100.")
    lines.append("- Focus on: what most likely happens, whether any days stand out as more polluted, and how confident we are.")
    lines.append("")
    lines.append("Task B – Stakeholder bullets (mid tier):")
    lines.append("- Write a concise bullet list for policy makers / general scientists / industry decision‑makers.")
    lines.append("- Include: percent of ensemble members in each scenario, approximate ppb ranges for typical vs higher‑ozone scenarios, and which days show any meaningful risk (e.g. probability of >50 ppb).")
    lines.append("- Mention uncertainty explicitly, especially when small clusters suggest higher ozone but with low probability.")
    lines.append("")
    lines.append("Task C – Technical note (expert tier):")
    lines.append("- Write one dense paragraph aimed at forecasters and ozone specialists.")
    lines.append("- Refer to the scenario structure (dominant vs tail scenarios), percentile ranges (p50/p90), and exceedance probabilities by threshold.")
    lines.append("- Keep it concise but information‑dense; this will live in a technical appendix or forecast discussion.")
    lines.append("")
    lines.append("Output format:")
    lines.append("1) Layperson text (one block).")
    lines.append("2) Mid‑tier bullet list.")
    lines.append("3) Expert paragraph.")
    lines.append("```")

    lines.append("")
    lines.append("## Notes for the forecaster / operator")
    lines.append("")
    lines.append("- Edit the prompt above to reference any specific days or thresholds you care about before sending to an LLM.")
    lines.append("- You can delete any fig subfolders you decide are overkill; the prompt only needs to describe what you actually plan to use.")
    lines.append("- For high‑ozone but uncertain events, emphasise the fraction of members in tail scenarios and how often they exceed key thresholds.")
    lines.append("- Keep the layperson text short, concrete, and focused on actions or expectations (e.g., “no special precautions”, “keep an eye on updates later this week”).")

    out_path.write_text("\n".join(lines))
    print(f"Wrote LLM template to {out_path}")


if __name__ == "__main__":
    if "MPLCONFIGDIR" not in os.environ:
        os.environ["MPLCONFIGDIR"] = ".mplconfig"
    main()

