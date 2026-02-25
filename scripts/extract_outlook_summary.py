#!/usr/bin/env python3
"""
Extract structured summary from LLM-OUTLOOK-*.md files.

Returns a dict with:
- alert_level: BACKGROUND | MODERATE | ELEVATED | EXTREME
- confidence: LOW | MEDIUM | HIGH
- alert_level_days_1_5 / confidence_days_1_5 (if block-level markers are present)
- alert_level_days_6_10 / confidence_days_6_10 (if block-level markers are present)
- alert_level_days_11_15 / confidence_days_11_15 (if block-level markers are present)
- days_1_5_expert: First 2 sentences from Days 1-5 Expert section
- days_6_10_expert: First 2 sentences from Days 6-10 Expert section
- days_11_15_expert: First 2 sentences from Days 11-15 Expert section
- key_drisk_statement: Extracted dRisk/dt trend statement

Usage:
    from scripts.extract_outlook_summary import extract_outlook_summary
    summary = extract_outlook_summary(Path("...LLM-OUTLOOK-*.md"))
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, Optional


_ALERT_RE = r"(BACKGROUND|MODERATE|ELEVATED|EXTREME)"
_CONFIDENCE_RE = r"(LOW|MEDIUM|HIGH)"
_BLOCK_LABELS = (
    ("D1_5", "days_1_5"),
    ("D6_10", "days_6_10"),
    ("D11_15", "days_11_15"),
)


def _extract_first_n_sentences(text: str, n: int = 2) -> str:
    """Extract first N sentences from text, handling common abbreviations."""
    # Split on sentence-ending punctuation followed by space or end
    # Be careful with abbreviations like "e.g.", "i.e.", "approx."
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    result = " ".join(sentences[:n])
    # Truncate if too long (safety valve)
    if len(result) > 500:
        result = result[:497] + "..."
    return result


def _extract_expert_section(content: str, section_header: str) -> Optional[str]:
    """Extract Expert Summary paragraph from a Days section."""
    # Handle either:
    # - **Expert Summary:**
    # - **c) Expert Summary**
    # followed by one or more paragraph lines until the next bold subsection/header.
    pattern = (
        rf"{re.escape(section_header)}.*?"
        r"\*\*(?:c\)\s*)?Expert Summary\*{2}:?\s*\n"
        r"(.+?)(?=\n\*\*|\n##|\n---|\Z)"
    )
    match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
    if match:
        expert_text = match.group(1).strip()
        return _extract_first_n_sentences(expert_text, 2)
    return None


def _extract_drisk_statement(content: str) -> Optional[str]:
    """Find a sentence containing dRisk/dt or trend language."""
    # Look for sentences mentioning dRisk/dt, strengthening, weakening, trend
    # Search in the Full Outlook section preferentially
    full_outlook_match = re.search(
        r'## Full Outlook\s*\n(.+?)(?=\n---|\n##|\Z)',
        content,
        re.DOTALL | re.IGNORECASE
    )
    search_text = full_outlook_match.group(1) if full_outlook_match else content

    # Find sentences with dRisk/dt or trend keywords
    sentences = re.split(r'(?<=[.!?])\s+', search_text)
    for sentence in sentences:
        if re.search(r'dRisk/dt|strengthening|weakening|positive trend|negative trend|run-to-run', sentence, re.IGNORECASE):
            # Clean up and truncate if needed
            clean = sentence.strip()
            if len(clean) > 300:
                clean = clean[:297] + "..."
            return clean
    return None


def _extract_block_alert_confidence(content: str) -> Dict[str, str]:
    """Extract block-level AlertLevel_D*_ and Confidence_D*_ markers."""
    out: Dict[str, str] = {}
    for suffix, label in _BLOCK_LABELS:
        alert_match = re.search(
            rf"AlertLevel_{suffix}:\s*{_ALERT_RE}",
            content,
            re.IGNORECASE,
        )
        conf_match = re.search(
            rf"Confidence_{suffix}:\s*{_CONFIDENCE_RE}",
            content,
            re.IGNORECASE,
        )
        if alert_match:
            out[f"alert_level_{label}"] = alert_match.group(1).upper()
        if conf_match:
            out[f"confidence_{label}"] = conf_match.group(1).upper()
        if alert_match and conf_match:
            out[f"alert_confidence_{label}"] = (
                f"{alert_match.group(1).upper()}/{conf_match.group(1).upper()}"
            )
    return out


def _select_fallback_pair(block_values: Dict[str, str]) -> Optional[Dict[str, str]]:
    """Pick a stable fallback alert/confidence from block-level fields."""
    for _, label in _BLOCK_LABELS:
        alert = block_values.get(f"alert_level_{label}")
        confidence = block_values.get(f"confidence_{label}")
        if alert and confidence:
            return {"alert_level": alert, "confidence": confidence}
    return None


def extract_outlook_summary(path: Path) -> Optional[Dict[str, str]]:
    """
    Extract structured summary from an LLM outlook file.

    Args:
        path: Path to LLM-OUTLOOK-*.md file

    Returns:
        Dict with alert_level, confidence, expert summaries, and dRisk statement.
        Returns None if file cannot be parsed or critical fields missing.
    """
    if not path.exists():
        return None

    try:
        content = path.read_text()
    except Exception:
        return None

    block_values = _extract_block_alert_confidence(content)

    # Legacy single-level markers (kept for backward compatibility).
    alert_match = re.search(
        rf"AlertLevel:\s*{_ALERT_RE}",
        content,
        re.IGNORECASE,
    )
    conf_match = re.search(
        rf"Confidence:\s*{_CONFIDENCE_RE}",
        content,
        re.IGNORECASE,
    )

    has_legacy_pair = bool(alert_match and conf_match)
    has_block_pair = any(
        block_values.get(f"alert_level_{label}") and block_values.get(f"confidence_{label}")
        for _, label in _BLOCK_LABELS
    )
    if not has_legacy_pair and not has_block_pair:
        return None  # Critical fields missing.

    result: Dict[str, str] = {}
    if has_legacy_pair:
        result["alert_level"] = alert_match.group(1).upper()
        result["confidence"] = conf_match.group(1).upper()
    else:
        fallback = _select_fallback_pair(block_values)
        if fallback is not None:
            result.update(fallback)

    result.update(block_values)
    if has_legacy_pair and has_block_pair:
        result["summary_format"] = "mixed"
    elif has_block_pair:
        result["summary_format"] = "block"
    else:
        result["summary_format"] = "legacy"

    # Extract expert summaries for each period
    # Handle both en-dash (–) and regular dash (-)
    days_1_5 = _extract_expert_section(content, "## Days 1–5") or \
               _extract_expert_section(content, "## Days 1-5")
    days_6_10 = _extract_expert_section(content, "## Days 6–10") or \
                _extract_expert_section(content, "## Days 6-10")
    days_11_15 = _extract_expert_section(content, "## Days 11–15") or \
                 _extract_expert_section(content, "## Days 11-15")

    if days_1_5:
        result["days_1_5_expert"] = days_1_5
    if days_6_10:
        result["days_6_10_expert"] = days_6_10
    if days_11_15:
        result["days_11_15_expert"] = days_11_15

    # Extract dRisk/dt trend statement
    drisk = _extract_drisk_statement(content)
    if drisk:
        result["key_drisk_statement"] = drisk

    return result


if __name__ == "__main__":
    # Quick test with existing outlook
    import sys
    if len(sys.argv) > 1:
        test_path = Path(sys.argv[1])
    else:
        # Default to a known outlook for testing
        test_path = Path(__file__).parent.parent / "data" / "json_tests" / \
                    "CASE_20251230_1200Z" / "llm_text" / "LLM-OUTLOOK-20251230_1200Z.md"

    summary = extract_outlook_summary(test_path)
    if summary:
        print(f"File: {test_path}")
        print(f"Alert Level: {summary.get('alert_level')}")
        print(f"Confidence: {summary.get('confidence')}")
        print(f"Format: {summary.get('summary_format', 'unknown')}")
        print(f"D1-5: {summary.get('alert_confidence_days_1_5', 'N/A')}")
        print(f"D6-10: {summary.get('alert_confidence_days_6_10', 'N/A')}")
        print(f"D11-15: {summary.get('alert_confidence_days_11_15', 'N/A')}")
        print(f"Days 1-5: {summary.get('days_1_5_expert', 'N/A')[:100]}...")
        print(f"Days 6-10: {summary.get('days_6_10_expert', 'N/A')[:100]}...")
        print(f"Days 11-15: {summary.get('days_11_15_expert', 'N/A')[:100]}...")
        print(f"dRisk/dt: {summary.get('key_drisk_statement', 'N/A')[:150]}...")
    else:
        print(f"Failed to parse: {test_path}")
