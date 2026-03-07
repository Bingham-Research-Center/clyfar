#!/usr/bin/env python3
"""Prune generated Ffion CASE artifacts to reduce disk/repo working-tree bloat.

This script targets generated artifacts under ignored data roots, not source
files. It is intentionally dry-run by default.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path


def iter_archive_victims(data_root: Path, keep_archive: int) -> list[Path]:
    victims: list[Path] = []
    for archive_dir in data_root.glob("CASE_*/llm_text/archive"):
        files = sorted(
            [path for path in archive_dir.iterdir() if path.is_file()],
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        victims.extend(files[keep_archive:])
    return victims


def iter_temp_attempt_victims(data_root: Path) -> list[Path]:
    victims: list[Path] = []
    for llm_dir in data_root.glob("CASE_*/llm_text"):
        victims.extend(
            path for path in llm_dir.glob("archive/.*.attempt*.tmp") if path.is_file()
        )
    return victims


def iter_rendered_prompt_victims(data_root: Path, keep_prompt: int) -> list[Path]:
    victims: list[Path] = []
    by_case: dict[Path, list[Path]] = defaultdict(list)
    for prompt in data_root.glob("CASE_*/llm_text/forecast_prompt_*.md"):
        by_case[prompt.parent].append(prompt)
    for prompts in by_case.values():
        ordered = sorted(prompts, key=lambda path: path.stat().st_mtime, reverse=True)
        victims.extend(ordered[keep_prompt:])
    return victims


def main() -> None:
    parser = argparse.ArgumentParser(description="Prune generated Ffion CASE artifacts.")
    parser.add_argument(
        "--data-root",
        type=Path,
        default=Path("data/json_tests"),
        help="CASE root containing CASE_*/llm_text directories.",
    )
    parser.add_argument(
        "--keep-archive",
        type=int,
        default=5,
        help="Keep this many newest archive files per CASE (default: 5).",
    )
    parser.add_argument(
        "--keep-prompts",
        type=int,
        default=1,
        help="Keep this many newest rendered forecast_prompt files per CASE (default: 1).",
    )
    parser.add_argument(
        "--remove-prompts",
        action="store_true",
        help="Allow old rendered forecast_prompt_*.md files to be removed.",
    )
    parser.add_argument(
        "--remove-legacy-qa",
        action="store_true",
        help="Also remove legacy generated data/llm_qa_context.md if present.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually delete files. Default is dry-run.",
    )
    args = parser.parse_args()

    data_root = args.data_root.expanduser()
    if not data_root.exists():
        raise SystemExit(f"Data root not found: {data_root}")

    victims: list[Path] = []
    victims.extend(iter_archive_victims(data_root, args.keep_archive))
    victims.extend(iter_temp_attempt_victims(data_root))
    if args.remove_prompts:
        victims.extend(iter_rendered_prompt_victims(data_root, args.keep_prompts))

    repo_root = Path(__file__).resolve().parents[1]
    legacy_qa = repo_root / "data" / "llm_qa_context.md"
    if args.remove_legacy_qa and legacy_qa.exists():
        victims.append(legacy_qa)

    victims = sorted(set(victims))
    total_bytes = sum(path.stat().st_size for path in victims if path.exists())
    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"{mode}: {len(victims)} files, {total_bytes} bytes")
    for path in victims:
        print(path)

    if not args.apply:
        return

    for path in victims:
        if path.exists():
            path.unlink()


if __name__ == "__main__":
    main()
