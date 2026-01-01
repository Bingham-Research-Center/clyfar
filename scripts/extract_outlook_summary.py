#!/usr/bin/env python3
"""
Extract structured summary from LLM-OUTLOOK-*.md files.

Returns a dict with:
- alert_level: BACKGROUND | MODERATE | ELEVATED | EXTREME
- confidence: LOW | MEDIUM | HIGH
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
    # Pattern: find the section, then look for **Expert Summary:** paragraph
    # Section headers like "## Days 1–5" or "## Days 6–10"
    pattern = rf'{re.escape(section_header)}.*?\*\*Expert Summary:\*\*\s*\n(.+?)(?=\n\n|\*\*Solar caveat|\Z)'
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

    # Extract AlertLevel from code block at end
    # Pattern: ```\nAlertLevel: MODERATE\nConfidence: MEDIUM\n```
    alert_match = re.search(
        r'AlertLevel:\s*(BACKGROUND|MODERATE|ELEVATED|EXTREME)',
        content,
        re.IGNORECASE
    )
    conf_match = re.search(
        r'Confidence:\s*(LOW|MEDIUM|HIGH)',
        content,
        re.IGNORECASE
    )

    if not alert_match or not conf_match:
        return None  # Critical fields missing

    result = {
        "alert_level": alert_match.group(1).upper(),
        "confidence": conf_match.group(1).upper(),
    }

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
        print(f"Days 1-5: {summary.get('days_1_5_expert', 'N/A')[:100]}...")
        print(f"Days 6-10: {summary.get('days_6_10_expert', 'N/A')[:100]}...")
        print(f"Days 11-15: {summary.get('days_11_15_expert', 'N/A')[:100]}...")
        print(f"dRisk/dt: {summary.get('key_drisk_statement', 'N/A')[:150]}...")
    else:
        print(f"Failed to parse: {test_path}")
