#!/usr/bin/env python3
"""Validate generated LLM outlook markdown for operational integrity."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from utils.versioning import get_clyfar_version, get_ffion_version


REQUIRED_MARKERS = (
    "AlertLevel_D1_5",
    "Confidence_D1_5",
    "AlertLevel_D6_10",
    "Confidence_D6_10",
    "AlertLevel_D11_15",
    "Confidence_D11_15",
)


def _normalise_version(version: str) -> str:
    value = version.strip()
    if value.lower().startswith("ffion-v"):
        return value.split("ffion-v", 1)[1].strip()
    if value.lower().startswith("v"):
        return value[1:].strip()
    return value


def extract_header_versions(text: str) -> Tuple[str | None, str | None]:
    """Return ``(ffion_version, clyfar_version)`` from outlook banner."""
    pattern = re.compile(
        r"Forecaster:\s*\*\*Ffion\s+v(?P<ffion>[^*]+)\*\*.*?\*\*Clyfar\s+v(?P<clyfar>[^*]+)\*\*",
        re.IGNORECASE,
    )
    match = pattern.search(text)
    if not match:
        return None, None
    return _normalise_version(match.group("ffion")), _normalise_version(match.group("clyfar"))


def _find_data_logger_section(lines: Sequence[str]) -> Sequence[str]:
    start_idx = -1
    for i, line in enumerate(lines):
        if re.search(r"^\s{0,3}#{1,6}\s*Data Logger\b", line, re.IGNORECASE):
            start_idx = i
            break
    if start_idx == -1:
        for i, line in enumerate(lines):
            if re.search(r"\bData Logger\b", line, re.IGNORECASE):
                start_idx = i
                break
    if start_idx == -1:
        return []

    section = lines[start_idx + 1 :]
    next_heading = len(section)
    for i, line in enumerate(section):
        if re.match(r"^\s{0,3}#{1,6}\s+", line):
            next_heading = i
            break
    return section[:next_heading]


def extract_local_paths(text: str) -> List[str]:
    """Extract local file paths from Data Logger section."""
    lines = text.splitlines()
    section = _find_data_logger_section(lines)
    if not section:
        return []

    candidates: List[str] = []
    backtick_pattern = re.compile(r"`([^`]+)`")
    abs_pattern = re.compile(r"(?<![A-Za-z0-9_])(/[^\s,;`'\"\\]\)]+)")

    for line in section:
        for match in backtick_pattern.findall(line):
            item = match.strip().rstrip(".,;:)]}")
            if item.startswith(("http://", "https://")):
                continue
            if "/" in item:
                candidates.append(item)

        for match in abs_pattern.findall(line):
            item = match.strip().rstrip(".,;:)]}")
            if item.startswith(("http://", "https://")):
                continue
            candidates.append(item)

    unique: List[str] = []
    seen = set()
    for item in candidates:
        if item not in seen:
            seen.add(item)
            unique.append(item)
    return unique


def marker_errors(text: str) -> List[str]:
    errors: List[str] = []
    for marker in REQUIRED_MARKERS:
        if not re.search(rf"^{re.escape(marker)}:\s+", text, re.MULTILINE):
            errors.append(f"Missing marker: {marker}")
    return errors


def _path_exists(raw: str, outlook_path: Path) -> bool:
    path = Path(raw)
    if path.is_absolute():
        return path.exists()

    # Relative paths are resolved against common report contexts.
    outlook_dir = outlook_path.parent
    case_root = outlook_dir.parent
    json_tests_root = case_root.parent
    candidates = (
        (outlook_dir / path).resolve(),
        (case_root / path).resolve(),
        (json_tests_root / path).resolve(),
        (REPO_ROOT / path).resolve(),
    )
    return any(candidate.exists() for candidate in candidates)


def validate_outlook(
    outlook_path: Path,
    expected_clyfar: str,
    expected_ffion: str,
) -> Tuple[bool, List[str]]:
    errors: List[str] = []

    if not outlook_path.exists():
        return False, [f"Outlook file does not exist: {outlook_path}"]
    if outlook_path.stat().st_size == 0:
        return False, [f"Outlook file is empty: {outlook_path}"]

    text = outlook_path.read_text(encoding="utf-8", errors="replace")

    stripped = text.lstrip()
    if not stripped.startswith("---"):
        errors.append("Outlook does not start with YAML/disclaimer fence '---'.")

    ffion_found, clyfar_found = extract_header_versions(text)
    if ffion_found is None or clyfar_found is None:
        errors.append("Could not find Forecaster banner with Ffion/Clyfar versions.")
    else:
        if ffion_found != _normalise_version(expected_ffion):
            errors.append(
                f"Ffion version mismatch: found {ffion_found}, expected {_normalise_version(expected_ffion)}"
            )
        if clyfar_found != _normalise_version(expected_clyfar):
            errors.append(
                f"Clyfar version mismatch: found {clyfar_found}, expected {_normalise_version(expected_clyfar)}"
            )

    errors.extend(marker_errors(text))

    data_logger_section = _find_data_logger_section(text.splitlines())
    if not data_logger_section:
        errors.append("Missing Data Logger section.")
    else:
        local_paths = extract_local_paths(text)
        if not local_paths:
            errors.append("Data Logger section contains no local file paths.")
        else:
            for raw in local_paths:
                if not _path_exists(raw, outlook_path):
                    errors.append(f"Data Logger path does not exist: {raw}")

    return len(errors) == 0, errors


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate LLM outlook banner versions, markers, and Data Logger links."
    )
    parser.add_argument("outlook_file", type=Path, help="Path to LLM-OUTLOOK-*.md")
    parser.add_argument(
        "--expected-clyfar",
        default=get_clyfar_version(),
        help="Expected Clyfar version (default: runtime resolver)",
    )
    parser.add_argument(
        "--expected-ffion",
        default=get_ffion_version(),
        help="Expected Ffion version (default: runtime resolver)",
    )
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    ok, errors = validate_outlook(
        outlook_path=args.outlook_file,
        expected_clyfar=args.expected_clyfar,
        expected_ffion=args.expected_ffion,
    )
    if ok:
        print(f"VALIDATION PASSED: {args.outlook_file}")
        return 0

    print(f"VALIDATION FAILED: {args.outlook_file}", file=sys.stderr)
    for err in errors:
        print(f"  - {err}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
