#!/usr/bin/env python3
"""
Generate an LLM-ready forecast report template for a Clyfar CASE directory.

For a given init time, this script:
- Locates data/json_tests/CASE_YYYYMMDD_HHMMZ/
- Notes which JSON + figs subfolders exist
- Optionally inlines operator notes
- Optionally includes relevance-gated short-term bias notes
- Writes a markdown template in CASE_.../llm_text/ with:
  * 3×5-day summaries (Days 1–5, 6–10, 11–15) at three complexity levels
  * Instructions for a full (~1 page) outlook
  * Guardrails on language, units, and alert level output

Usage (from repo root):
    MPLCONFIGDIR=.mplconfig python scripts/demo_llm_forecast_template.py 2025120412
    # or
    MPLCONFIGDIR=.mplconfig python scripts/demo_llm_forecast_template.py 20251204_1200Z

Optional:
    --qa-file path/to/qa_notes.md     # optional operator notes
    --bias-file path/to/biases.json   # optional short-term bias entries
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.extract_outlook_summary import extract_outlook_summary
from utils.ffion_bundle import resolve_ffion_bundle, sha256_file
from utils.versioning import get_clyfar_version, get_ffion_version

DEFAULT_PROMPT_TEMPLATE = REPO_ROOT / "templates" / "llm" / "prompt_body.md"
DEFAULT_BIAS_FILE = REPO_ROOT / "templates" / "llm" / "short_term_biases.json"
DEFAULT_CLYFAR_VERSION = "1.0.5"
DEFAULT_FFION_VERSION = "1.1.3"

# Previous outlook configuration
MAX_PREVIOUS_OUTLOOKS = 2
MAX_OUTLOOK_AGE_HOURS = 18  # 18h = 3 prior 6-hourly runs

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


def format_ffion_bundle_lines(
    ffion_bundle,
    *,
    prompt_template_path: Path,
    bias_path: Optional[Path],
    qa_path: Optional[Path],
) -> List[str]:
    """Return prompt metadata lines for the resolved Ffion bundle."""
    lines: List[str] = []
    lines.append("## Ffion Bundle")
    lines.append("")
    lines.append("> Versioned editable Ffion file set used for this render and future reforecasting.")
    lines.append(f"- Ffion version: `{ffion_bundle.ffion_version}`")
    lines.append(f"- Label: `{ffion_bundle.label}`")
    lines.append(f"- Manifest: `{ffion_bundle.manifest_path}`")
    lines.append(f"- Bundle prompt template: `{ffion_bundle.prompt_template}`")
    lines.append(f"- Bundle prompt sha256: `{ffion_bundle.prompt_sha256}`")
    if prompt_template_path.exists():
        lines.append(f"- Prompt template in use: `{prompt_template_path}`")
        lines.append(f"- Prompt sha256 in use: `{sha256_file(prompt_template_path)}`")
    if ffion_bundle.bias_file:
        lines.append(f"- Bundle bias file: `{ffion_bundle.bias_file}`")
        lines.append(f"- Bundle bias sha256: `{ffion_bundle.bias_sha256}`")
    else:
        lines.append("- Bundle bias file: (none)")
    if bias_path and bias_path.exists():
        lines.append(f"- Bias file in use: `{bias_path}`")
        lines.append(f"- Bias sha256 in use: `{sha256_file(bias_path)}`")
    elif bias_path is None:
        lines.append("- Bias file in use: (none)")
    if qa_path:
        lines.append(f"- QA file in use: `{qa_path}`")
    else:
        lines.append("- QA file in use: (none)")
    if ffion_bundle.qa_file:
        lines.append(f"- Bundle QA source: `{ffion_bundle.qa_file}`")
        lines.append(f"- Bundle QA sha256: `{ffion_bundle.qa_sha256}`")
        lines.append(f"- QA enabled by default: `{ffion_bundle.qa_enabled_by_default}`")
    else:
        lines.append("- Bundle QA source: (none)")
    if ffion_bundle.notes:
        lines.append(f"- Notes: {ffion_bundle.notes}")
    lines.append("")
    return lines


def load_bias_entries(path: Path) -> List[Dict]:
    """Load short-term bias entries from JSON file."""
    if not path.exists():
        return []
    data = json.loads(path.read_text())
    if isinstance(data, dict):
        entries = data.get("biases", [])
    elif isinstance(data, list):
        entries = data
    else:
        entries = []
    if not isinstance(entries, list):
        return []
    return [e for e in entries if isinstance(e, dict)]


def extract_cluster_metrics(summary: Dict) -> Dict[str, float]:
    """Extract compact metrics used to gate short-term bias notes."""
    clusters = summary.get("clusters", []) if isinstance(summary, dict) else []
    if not isinstance(clusters, list):
        clusters = []

    null_fraction = 0.0
    max_non_null_high = 0.0
    non_null_fraction = 0.0
    for c in clusters:
        if not isinstance(c, dict):
            continue
        frac = float(c.get("fraction", 0.0) or 0.0)
        kind = str(c.get("kind", ""))
        if kind == "null" or int(c.get("id", -1)) == 0:
            null_fraction += frac
            continue
        non_null_fraction += frac
        risk_profile = c.get("risk_profile", {})
        if isinstance(risk_profile, dict):
            max_non_null_high = max(
                max_non_null_high,
                float(risk_profile.get("weighted_high", 0.0) or 0.0),
            )
    return {
        "null_fraction": float(null_fraction),
        "non_null_fraction": float(non_null_fraction),
        "max_non_null_high": float(max_non_null_high),
    }


def select_relevant_biases(entries: List[Dict], metrics: Dict[str, float]) -> List[Dict]:
    """Return bias entries that pass optional relevance thresholds."""
    relevant: List[Dict] = []
    for entry in entries:
        min_non_null = entry.get("min_non_null_fraction")
        max_null = entry.get("max_null_fraction")
        min_high = entry.get("min_max_non_null_high")

        if min_non_null is not None and metrics["non_null_fraction"] < float(min_non_null):
            continue
        if max_null is not None and metrics["null_fraction"] > float(max_null):
            continue
        if min_high is not None and metrics["max_non_null_high"] < float(min_high):
            continue
        relevant.append(entry)
    return relevant


def format_clustering_diagnostics(summary: Dict) -> List[str]:
    """Return compact diagnostic bullets for prompt conditioning."""
    stage1 = summary.get("method", {}).get("stage_1", {}) if isinstance(summary, dict) else {}
    stage2 = summary.get("method", {}).get("stage_2", {}) if isinstance(summary, dict) else {}
    quality = summary.get("quality_flags", {}) if isinstance(summary, dict) else {}
    active_window = stage1.get("active_window", {}) if isinstance(stage1, dict) else {}
    distance = stage2.get("distance_diagnostics", {}) if isinstance(stage2, dict) else {}
    combined = distance.get("combined", {}) if isinstance(distance, dict) else {}
    nearest = distance.get("nearest_neighbor", {}) if isinstance(distance, dict) else {}

    lines: List[str] = []
    lines.append(
        f"- Active non-background days: {active_window.get('active_days', 'n/a')}/"
        f"{active_window.get('total_days', 'n/a')}"
    )
    lines.append(
        f"- Strict null members: {quality.get('strict_null_members', 'n/a')} | "
        f"Non-null members: {quality.get('non_null_members', 'n/a')}"
    )
    lines.append(
        f"- Stage-2 selected k: {stage2.get('selected_k', 'n/a')} | "
        f"Fallback used: {stage2.get('fallback_used', 'n/a')} | "
        f"Min-size guard relaxed: {stage2.get('min_size_guard_relaxed', 'n/a')}"
    )
    lines.append(
        "- Combined distance spread "
        f"(min/p25/median/p75/max): {combined.get('min', 'n/a')}/"
        f"{combined.get('p25', 'n/a')}/{combined.get('median', 'n/a')}/"
        f"{combined.get('p75', 'n/a')}/{combined.get('max', 'n/a')}"
    )
    lines.append(
        f"- Nearest-neighbor distance (median/p75/max): "
        f"{nearest.get('median', 'n/a')}/{nearest.get('p75', 'n/a')}/{nearest.get('max', 'n/a')}"
    )
    return lines


def gather_previous_outlooks(
    data_root: Path,
    norm_init: str,
    recent_cases: List[str],
    max_outlooks: int = MAX_PREVIOUS_OUTLOOKS,
    max_age_hours: float = MAX_OUTLOOK_AGE_HOURS,
) -> Tuple[List[Dict], List[Path], List[Path]]:
    """
    Gather summaries from previous LLM outlooks within the age window.

    Args:
        data_root: Base path containing CASE_* directories
        norm_init: Current init time (YYYYMMDD_HHMMZ)
        recent_cases: List of recent init strings from list_recent_cases()
        max_outlooks: Maximum number of previous outlooks to include
        max_age_hours: Skip outlooks older than this (hours)

    Returns:
        Tuple of:
        1) parsed outlook summaries,
        2) paths successfully used for comparison,
        3) paths that existed but failed parsing.
    """
    current_dt = datetime.strptime(norm_init, "%Y%m%d_%H%MZ")
    previous_outlooks = []
    parse_failures: List[Path] = []
    used_paths: List[Path] = []

    # Iterate through recent cases in reverse order (newest first), excluding current
    for prev_init in reversed(recent_cases):
        if prev_init == norm_init:
            continue  # Skip current case

        try:
            prev_dt = datetime.strptime(prev_init, "%Y%m%d_%H%MZ")
        except ValueError:
            continue

        age_hours = (current_dt - prev_dt).total_seconds() / 3600
        if age_hours <= 0:
            continue  # Skip future cases (shouldn't happen)
        if age_hours > max_age_hours:
            continue  # Skip stale outlooks

        prev_case = case_root_for_init(data_root, prev_init)
        outlook_path = prev_case / "llm_text" / f"LLM-OUTLOOK-{prev_init}.md"

        if outlook_path.exists():
            summary = extract_outlook_summary(outlook_path)
            if summary:
                previous_outlooks.append({
                    "init": prev_init,
                    "age_hours": int(age_hours),
                    "summary": summary,
                })
                used_paths.append(outlook_path)
                if len(previous_outlooks) >= max_outlooks:
                    break
            else:
                parse_failures.append(outlook_path)

    for failed_path in parse_failures:
        print(f"Warning: could not parse previous outlook summary: {failed_path}")

    return previous_outlooks, used_paths, parse_failures


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
        help="Optional path to freeform operator notes for the LLM context (overrides bundle/default QA).",
    )
    parser.add_argument(
        "--bias-file",
        type=str,
        default=None,
        help="Path to short-term bias JSON used for relevance-gated caution notes (overrides Ffion bundle).",
    )
    parser.add_argument(
        "--prompt-template",
        type=str,
        default=None,
        help="Path to the markdown template used for the prompt body (overrides Ffion bundle).",
    )
    parser.add_argument(
        "--ffion-version",
        type=str,
        default=None,
        help="Ffion version to use when resolving the versioned outlook bundle.",
    )
    parser.add_argument(
        "--ffion-manifest",
        type=str,
        default=os.environ.get("FFION_MANIFEST") or os.environ.get("LLM_FFION_MANIFEST"),
        help="Explicit Ffion manifest path to use.",
    )
    args = parser.parse_args()

    data_root = REPO_ROOT / "data" / "json_tests"
    if not data_root.exists():
        raise SystemExit(f"Data directory not found: {data_root}")

    clyfar_version = get_clyfar_version(default=DEFAULT_CLYFAR_VERSION)
    requested_ffion_version = args.ffion_version
    if requested_ffion_version is None and args.ffion_manifest is None:
        requested_ffion_version = get_ffion_version(default=DEFAULT_FFION_VERSION)
    ffion_bundle = resolve_ffion_bundle(
        ffion_version=requested_ffion_version,
        manifest_path=args.ffion_manifest,
    )
    ffion_version = ffion_bundle.ffion_version

    norm_init = parse_init(args.init)
    case_root = case_root_for_init(data_root, norm_init)
    if not case_root.exists():
        raise SystemExit(f"Case directory not found: {case_root}")

    figs_root = case_root / "figs"
    json_subdirs = {
        "percentiles": case_root / "percentiles",
        "probs": case_root / "probs",
        "possibilities": case_root / "possibilities",
        "weather": case_root / "weather",
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

    prompt_template_value = (
        args.prompt_template
        or os.environ.get("LLM_PROMPT_TEMPLATE")
        or str(ffion_bundle.prompt_template)
        or str(DEFAULT_PROMPT_TEMPLATE)
    )
    prompt_template_path = Path(prompt_template_value).expanduser()

    bias_value = (
        args.bias_file
        or os.environ.get("LLM_BIAS_FILE")
        or (str(ffion_bundle.bias_file) if ffion_bundle.bias_file else None)
        or str(DEFAULT_BIAS_FILE)
    )
    bias_path = Path(bias_value).expanduser() if bias_value else None

    qa_value = args.qa_file or os.environ.get("LLM_QA_FILE")
    if not qa_value and ffion_bundle.qa_enabled_by_default and ffion_bundle.qa_file:
        qa_value = str(ffion_bundle.qa_file)

    qa_path: Optional[Path] = None
    qa_text = None
    if qa_value:
        qa_path = Path(qa_value).expanduser()
        if qa_path.exists():
            qa_text = qa_path.read_text()
            print(f"Using Q&A context file: {qa_path}")
        else:
            print(f"Warning: Q&A file not found: {qa_path}")
    else:
        print("No Q&A context file found or specified.")

    bias_entries: List[Dict] = []
    if bias_path is not None:
        if bias_path.exists():
            bias_entries = load_bias_entries(bias_path)
        else:
            print(f"Warning: bias file not found: {bias_path}")

    clustering_file = case_root / f"forecast_clustering_summary_{norm_init}.json"
    clustering_summary: Dict = {}
    if clustering_file.exists():
        try:
            clustering_summary = json.loads(clustering_file.read_text())
        except Exception:
            clustering_summary = {}

    relevant_biases: List[Dict] = []
    if bias_entries:
        metrics = extract_cluster_metrics(clustering_summary)
        relevant_biases = select_relevant_biases(bias_entries, metrics)

    recent_cases = list_recent_cases(data_root, limit=8)

    # Gather previous outlook summaries for comparison
    previous_outlooks, previous_used_paths, previous_parse_failures = gather_previous_outlooks(
        data_root, norm_init, recent_cases
    )

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
    lines.append(f"- Clyfar version: `{clyfar_version}`")
    lines.append(f"- Ffion version: `{ffion_version}`")
    lines.append(f"- Ffion manifest: `{ffion_bundle.manifest_path}`")

    # List JSON files (Claude reads them via file access, no embedding)
    for name, path in json_subdirs.items():
        if path.exists():
            json_files = sorted(path.glob("*.json"))
            lines.append(f"- JSON · {name}: {len(json_files)} files at `{path.relative_to(case_root)}/`")
        else:
            lines.append(f"- JSON · {name}: (missing)")

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

    lines.append("")
    lines.append("## Local File Index")
    lines.append("")
    lines.append("> Canonical local paths for this run context. Reference these in Data Logger output.")
    lines.append(f"- Current CASE root: `{case_root}`")
    if clustering_file.exists():
        lines.append(f"- Clustering summary: `{clustering_file}`")
    else:
        lines.append("- Clustering summary: (missing)")
    for name, path in json_subdirs.items():
        if path.exists():
            lines.append(f"- JSON dir ({name}): `{path}`")
    if previous_used_paths:
        for prev_path in previous_used_paths:
            lines.append(f"- Previous outlook used for comparison: `{prev_path}`")
    else:
        lines.append("- Previous outlook used for comparison: (none)")
    if previous_parse_failures:
        for failed_path in previous_parse_failures:
            lines.append(f"- Previous outlook parse failed: `{failed_path}`")

    lines.extend(
        format_ffion_bundle_lines(
            ffion_bundle,
            prompt_template_path=prompt_template_path,
            bias_path=bias_path,
            qa_path=qa_path,
        )
    )

    if bias_entries:
        lines.append("")
        lines.append("## Short-Term Bias Context (for LLM only)")
        lines.append("")
        lines.append("> Integrate only where relevant to affected lead windows or scenarios.")
        lines.append("> Do not repeat unchanged cautions in every section.")
        lines.append("")
        if relevant_biases:
            for entry in relevant_biases:
                bias_id = str(entry.get("bias_id", "bias"))
                summary = str(entry.get("summary", "")).strip()
                lead_start = entry.get("lead_day_start")
                lead_end = entry.get("lead_day_end")
                if lead_start is not None and lead_end is not None:
                    window = f"Days {int(lead_start)}-{int(lead_end)}"
                else:
                    window = "Lead window: unspecified"
                lines.append(f"- `{bias_id}` ({window}): {summary}")
                confidence_impact = str(entry.get("confidence_impact", "")).strip()
                if confidence_impact:
                    lines.append(f"  Confidence guidance: {confidence_impact}")
        else:
            lines.append("- No short-term bias entries met relevance criteria for this run.")

    if qa_text:
        lines.append("")
        lines.append("## Operator Notes (optional, for LLM only)")
        lines.append("")
        lines.append("> Use only when relevant to the specific day window/scenario being discussed.")
        lines.append("> Do not echo notes verbatim.")
        lines.append("")
        for line in qa_text.splitlines():
            lines.append(f"> {line}")

    # Add previous outlook summaries section
    lines.append("")
    lines.append("## Previous Outlook Summaries (for comparison)")
    lines.append("")
    if previous_outlooks:
        lines.append("> Use these summaries to compare your current assessment against prior outlooks.")
        lines.append("> Explicitly note how your AlertLevel/Confidence differs from the previous run(s).")
        lines.append("> Prefer block-level comparisons (Days 1–5, 6–10, 11–15) when available.")
        lines.append("")
        for po in previous_outlooks:
            summary = po["summary"]
            lines.append(f"### Previous: {po['init']} ({po['age_hours']}h ago)")
            if summary.get("alert_confidence_days_1_5"):
                lines.append(
                    f"- **Days 1-5 Alert/Confidence:** {summary.get('alert_confidence_days_1_5', 'N/A')}"
                )
                lines.append(
                    f"- **Days 6-10 Alert/Confidence:** {summary.get('alert_confidence_days_6_10', 'N/A')}"
                )
                lines.append(
                    f"- **Days 11-15 Alert/Confidence:** {summary.get('alert_confidence_days_11_15', 'N/A')}"
                )
            else:
                lines.append(f"- **Alert Level:** {summary.get('alert_level', 'N/A')}")
                lines.append(f"- **Confidence:** {summary.get('confidence', 'N/A')}")
            if summary.get("days_1_5_expert"):
                lines.append(f"- **Days 1-5 (expert):** {summary['days_1_5_expert']}")
            if summary.get("days_6_10_expert"):
                lines.append(f"- **Days 6-10 (expert):** {summary['days_6_10_expert']}")
            if summary.get("days_11_15_expert"):
                lines.append(f"- **Days 11-15 (expert):** {summary['days_11_15_expert']}")
            if summary.get("key_drisk_statement"):
                lines.append(f"- **dRisk/dt trend:** {summary['key_drisk_statement']}")
            lines.append("")
    else:
        if previous_parse_failures:
            lines.append("> Previous outlook files exist but could not be parsed into structured summaries.")
            lines.append("> Mention this limitation explicitly in the final outlook.")
        else:
            lines.append("> No previous outlook files found within the last 18 hours for comparison.")
            lines.append("> Note in your outlook: \"This is the first outlook in this sequence.\"")
        lines.append("")

    # Embed clustering summary if available (small, critical context for Claude)
    lines.append("## Ensemble Clustering Summary")
    lines.append("")
    if clustering_file.exists() and clustering_summary:
        lines.append("> Cluster assignments showing GEFS weather → Clyfar ozone linkage.")
        lines.append("> Use the diagnostics snapshot to calibrate confidence language.")
        lines.append("")
        lines.append("### Clustering Diagnostics Snapshot")
        for diag_line in format_clustering_diagnostics(clustering_summary):
            lines.append(diag_line)
        lines.append("")
        lines.append("```json")
        lines.append(json.dumps(clustering_summary, indent=2))
        lines.append("```")
    else:
        lines.append(
            "> No clustering summary found. Run "
            "`scripts/generate_clustering_summary.py` before prompting the LLM."
        )
    lines.append("")

    if not prompt_template_path.exists():
        raise SystemExit(f"Prompt template not found: {prompt_template_path}")
    replacements = {
        "INIT": norm_init,
        "CASE_ROOT": str(case_root),
        "RECENT_CASE_COUNT": str(len(recent_cases)),
        "CLYFAR_VERSION": clyfar_version,
        "FFION_VERSION": ffion_version,
        "FFION_SCIENCE_VERSION": ffion_bundle.ffion_version,
        "FFION_SCIENCE_LABEL": ffion_bundle.label,
    }
    lines.append("")
    lines.append(render_prompt_template(prompt_template_path, replacements))

    out_path.write_text("\n".join(lines))
    print(f"Wrote LLM forecast prompt to {out_path}")


if __name__ == "__main__":
    if "MPLCONFIGDIR" not in os.environ:
        os.environ["MPLCONFIGDIR"] = ".mplconfig"
    main()
