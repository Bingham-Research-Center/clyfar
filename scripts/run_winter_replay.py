#!/usr/bin/env python3
"""Serial Slurm replay driver for the winter 2025-2026 Clyfar/Ffion archive.

The driver submits exactly one ``scripts/submit_clyfar.sh`` job at a time,
waits for it to leave Slurm, validates the replay artifacts, writes a manifest
and ledger row, archives the CASE directory, and then cleans the isolated
Herbie cache before moving to the next init.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_START = "2025120100"
DEFAULT_END = "2026031518"
VARIABLES = ("snow", "wind", "solar", "mslp", "temp")
LEDGER_FIELDS = (
    "init",
    "job_id",
    "status",
    "slurm_state",
    "slurm_exit_code",
    "started_utc",
    "finished_utc",
    "duration_seconds",
    "full_parquets",
    "dailymax_parquets",
    "gefs_representative_files",
    "export_json_files",
    "figure_files",
    "case_files",
    "cache_deleted_bytes",
    "manifest",
    "quicklook",
    "notes",
)


@dataclass(frozen=True)
class ReplayPaths:
    root: Path
    data_root: Path
    fig_root: Path
    export_dir: Path
    log_dir: Path
    case_archive_root: Path
    manifest_dir: Path
    quicklook_dir: Path
    herbie_cache: Path
    ledger_path: Path


def parse_init(init: str) -> dt.datetime:
    if len(init) != 10 or not init.isdigit():
        raise ValueError(f"Init must be YYYYMMDDHH, got {init!r}")
    parsed = dt.datetime.strptime(init, "%Y%m%d%H")
    if parsed.hour not in (0, 6, 12, 18):
        raise ValueError(f"Init hour must be one of 00/06/12/18Z, got {init!r}")
    return parsed


def normalise_init(init: str) -> str:
    parsed = parse_init(init)
    return parsed.strftime("%Y%m%d_%H00Z")


def init_for_figure_glob(init: str) -> str:
    return parse_init(init).strftime("%Y%m%d-%H00")


def build_init_list(start: str, end: str) -> list[str]:
    start_dt = parse_init(start)
    end_dt = parse_init(end)
    if end_dt < start_dt:
        raise ValueError("End init must be after start init")
    inits: list[str] = []
    cur = start_dt
    while cur <= end_dt:
        inits.append(cur.strftime("%Y%m%d%H"))
        cur += dt.timedelta(hours=6)
    return inits


def default_replay_root() -> Path:
    return Path(
        os.environ.get(
            "CLYFAR_REPLAY_ROOT",
            Path.home() / "basinwx-data" / "clyfar_replay" / "winter_2025_2026",
        )
    )


def build_paths(root: Path) -> ReplayPaths:
    root = root.expanduser().resolve()
    return ReplayPaths(
        root=root,
        data_root=root / "data",
        fig_root=root / "figures",
        export_dir=root / "basinwx_export",
        log_dir=root / "logs",
        case_archive_root=root / "cases",
        manifest_dir=root / "manifests",
        quicklook_dir=root / "quicklooks",
        herbie_cache=root / "herbie_cache",
        ledger_path=root / "ledger.csv",
    )


def ensure_dirs(paths: ReplayPaths) -> None:
    for path in (
        paths.data_root,
        paths.fig_root,
        paths.export_dir,
        paths.log_dir,
        paths.case_archive_root,
        paths.manifest_dir,
        paths.quicklook_dir,
        paths.herbie_cache,
    ):
        path.mkdir(parents=True, exist_ok=True)


def run_checked(cmd: list[str], *, cwd: Path = REPO_ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )


def git_commit() -> str | None:
    try:
        return run_checked(["git", "rev-parse", "HEAD"]).stdout.strip()
    except Exception:
        return None


def build_sbatch_command(
    init: str,
    paths: ReplayPaths,
    *,
    cpus: int,
    mem: str,
    walltime: str,
    account: str | None = None,
    partition: str | None = None,
    ffion_version: str | None = None,
    ffion_manifest: str | None = None,
) -> list[str]:
    exports = {
        "CLYFAR_DIR": str(REPO_ROOT),
        "DATA_ROOT": str(paths.data_root),
        "FIG_ROOT": str(paths.fig_root),
        "EXPORT_DIR": str(paths.export_dir),
        "LOG_DIR": str(paths.log_dir),
        "CLYFAR_ENABLE_UPLOAD": "0",
        "CLYFAR_SKIP_INTERNAL_EXPORT": "1",
        "LLM_SKIP_UPLOAD": "1",
        "CLYFAR_HERBIE_CACHE": str(paths.herbie_cache),
        "CLYFAR_GEFS_DATA_ROOT": str(paths.data_root / "gefs_representative"),
    }
    if ffion_version:
        exports["FFION_VERSION"] = ffion_version
    if ffion_manifest:
        exports["FFION_MANIFEST"] = ffion_manifest
    cmd = [
        "sbatch",
        "--parsable",
        "--cpus-per-task",
        str(cpus),
        "--mem",
        mem,
        "--time",
        walltime,
        "--output",
        str(paths.log_dir / "clyfar_%j.out"),
        "--error",
        str(paths.log_dir / "clyfar_%j.err"),
        "--export=" + ",".join(["ALL", *[f"{key}={value}" for key, value in exports.items()]]),
    ]
    if account:
        cmd.extend(["--account", account])
    if partition:
        cmd.extend(["--partition", partition])
    cmd.extend([str(REPO_ROOT / "scripts" / "submit_clyfar.sh"), init, "--no-retry"])
    return cmd


def submit_job(cmd: list[str]) -> str:
    result = run_checked(cmd)
    job_id = result.stdout.strip().split(";")[0]
    if not job_id:
        raise RuntimeError(f"sbatch did not return a job id. stderr={result.stderr}")
    return job_id


def wait_for_job(job_id: str, poll_seconds: int) -> dict[str, str]:
    while True:
        result = subprocess.run(
            ["squeue", "-j", job_id, "-h"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(f"squeue failed for job {job_id}: {result.stderr.strip()}")
        if not result.stdout.strip():
            break
        time.sleep(poll_seconds)

    time.sleep(5)
    sacct = subprocess.run(
        ["sacct", "-j", job_id, "--format=JobIDRaw,State,ExitCode,Elapsed", "-P", "-n"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if sacct.returncode != 0:
        return {"state": "UNKNOWN", "exit_code": "UNKNOWN", "elapsed": "UNKNOWN"}
    for line in sacct.stdout.splitlines():
        parts = line.split("|")
        if len(parts) >= 4 and parts[0] == job_id:
            return {"state": parts[1], "exit_code": parts[2], "elapsed": parts[3]}
    return {"state": "UNKNOWN", "exit_code": "UNKNOWN", "elapsed": "UNKNOWN"}


def count_files(path: Path, pattern: str) -> int:
    if not path.exists():
        return 0
    return sum(1 for item in path.glob(pattern) if item.is_file())


def read_text_if_exists(path: Path) -> str:
    try:
        return path.read_text(errors="replace")
    except FileNotFoundError:
        return ""


def validate_logs(init: str, out_log: Path, err_log: Path) -> list[str]:
    text = "\n".join([read_text_if_exists(out_log), read_text_if_exists(err_log)])
    errors: list[str] = []
    required = (
        f"STATUS_FORECAST_EXPORT=SUCCESS init={init}",
        f"STATUS_LLM_STAGE=SUCCESS init={init}",
        f"STATUS_SUBMIT_LLM_PDF_PUSH=SKIPPED init={init} reason=upload_disabled",
    )
    for marker in required:
        if marker not in text:
            errors.append(f"missing log marker: {marker}")
    alerts = [line for line in text.splitlines() if "ALERT_" in line]
    if alerts:
        errors.append(f"alert markers present: {'; '.join(alerts[:5])}")
    return errors


def run_llm_validator(markdown_path: Path) -> tuple[bool, str]:
    validator = REPO_ROOT / "scripts" / "validate_llm_outlook.py"
    if not validator.exists():
        return False, f"validator not found: {validator}"
    result = subprocess.run(
        [sys.executable, str(validator), str(markdown_path)],
        cwd=str(REPO_ROOT),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    return result.returncode == 0, result.stdout.strip()


def validate_artifacts(
    init: str,
    paths: ReplayPaths,
    *,
    job_id: str,
    expected_members: int,
    skip_validator: bool = False,
) -> dict[str, Any]:
    norm = normalise_init(init)
    figure_key = init_for_figure_glob(init)
    out_log = paths.log_dir / f"clyfar_{job_id}.out"
    err_log = paths.log_dir / f"clyfar_{job_id}.err"
    case_dir = REPO_ROOT / "data" / "json_tests" / f"CASE_{norm}"
    llm_dir = case_dir / "llm_text"
    markdown_path = llm_dir / f"LLM-OUTLOOK-{norm}.md"
    pdf_path = llm_dir / f"LLM-OUTLOOK-{norm}.pdf"
    run_dir = paths.data_root / f"{norm}_run"
    parquets_dir = run_dir / "parquets"
    dailymax_dir = parquets_dir / "dailymax"
    gefs_dir = paths.data_root / "gefs_representative" / norm

    counts: dict[str, Any] = {
        "full_parquets": count_files(parquets_dir, "clyfar*_df.parquet"),
        "dailymax_parquets": count_files(dailymax_dir, "clyfar*_dailymax.parquet"),
        "gefs_representative_files": count_files(gefs_dir, "*.parquet"),
        "export_possibility": count_files(paths.export_dir, f"forecast_possibility_heatmap_*_{norm}.json"),
        "export_percentiles": count_files(paths.export_dir, f"forecast_percentile_scenarios_*_{norm}.json"),
        "export_probabilities": count_files(paths.export_dir, f"forecast_exceedance_probabilities_{norm}.json"),
        "export_clustering": count_files(paths.export_dir, f"forecast_clustering_summary_{norm}.json"),
        "export_weather": count_files(paths.export_dir, f"forecast_gefs_weather_*_{norm}.json"),
        "figure_heatmaps": count_files(paths.fig_root / "heatmap", f"*{figure_key}*.png"),
        "figure_meteograms": count_files(paths.fig_root / "meteograms", f"*{figure_key}*.png"),
        "case_files": count_files(case_dir, "**/*"),
    }
    counts["export_json_files"] = (
        counts["export_possibility"]
        + counts["export_percentiles"]
        + counts["export_probabilities"]
        + counts["export_clustering"]
        + counts["export_weather"]
    )
    counts["figure_files"] = counts["figure_heatmaps"] + counts["figure_meteograms"]

    errors = validate_logs(init, out_log, err_log)
    if counts["full_parquets"] < expected_members:
        errors.append(f"expected at least {expected_members} full parquets, found {counts['full_parquets']}")
    if counts["dailymax_parquets"] < expected_members:
        errors.append(f"expected at least {expected_members} dailymax parquets, found {counts['dailymax_parquets']}")
    for variable in VARIABLES:
        found = count_files(gefs_dir, f"{norm}_{variable}_*_df.parquet")
        counts[f"gefs_{variable}"] = found
        if found < expected_members:
            errors.append(f"expected at least {expected_members} representative {variable} files, found {found}")
    for key in ("export_possibility", "export_percentiles"):
        if counts[key] < expected_members:
            errors.append(f"expected at least {expected_members} {key} JSON files, found {counts[key]}")
    if counts["export_probabilities"] < 1:
        errors.append("missing exceedance probability JSON")
    if counts["export_clustering"] < 1:
        errors.append("missing clustering summary JSON")
    if counts["export_weather"] < 1:
        errors.append("missing GEFS weather export JSON")
    if counts["figure_heatmaps"] < expected_members:
        errors.append(f"expected at least {expected_members} Clyfar heatmap PNGs, found {counts['figure_heatmaps']}")
    if counts["figure_meteograms"] < len(VARIABLES):
        errors.append(f"expected at least {len(VARIABLES)} GEFS meteogram PNGs, found {counts['figure_meteograms']}")
    if not markdown_path.is_file() or markdown_path.stat().st_size == 0:
        errors.append(f"missing or empty Ffion markdown: {markdown_path}")
    if not pdf_path.is_file() or pdf_path.stat().st_size == 0:
        errors.append(f"missing or empty Ffion PDF: {pdf_path}")
    if markdown_path.exists() and not skip_validator:
        ok, output = run_llm_validator(markdown_path)
        counts["llm_validator_output"] = output
        if not ok:
            errors.append(f"Ffion validator failed: {output}")

    return {
        "init": init,
        "normalised_init": norm,
        "status": "SUCCESS" if not errors else "FAILED",
        "errors": errors,
        "counts": counts,
        "paths": {
            "out_log": str(out_log),
            "err_log": str(err_log),
            "run_dir": str(run_dir),
            "gefs_representative_dir": str(gefs_dir),
            "export_dir": str(paths.export_dir),
            "figure_root": str(paths.fig_root),
            "case_dir": str(case_dir),
            "markdown": str(markdown_path),
            "pdf": str(pdf_path),
        },
    }


def archive_case(init: str, paths: ReplayPaths) -> Path:
    norm = normalise_init(init)
    source = REPO_ROOT / "data" / "json_tests" / f"CASE_{norm}"
    dest = paths.case_archive_root / f"CASE_{norm}"
    if not source.exists():
        raise FileNotFoundError(f"CASE source not found: {source}")
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(source, dest)
    return dest


def prune_temp_llm_attempts(init: str) -> dict[str, int]:
    norm = normalise_init(init)
    llm_dir = REPO_ROOT / "data" / "json_tests" / f"CASE_{norm}" / "llm_text"
    victims: list[Path] = []
    if llm_dir.exists():
        victims.extend(path for path in llm_dir.glob("archive/.*.attempt*.tmp") if path.is_file())
        victims.extend(path for path in llm_dir.glob(".*.attempt*.tmp") if path.is_file())
    deleted_bytes = sum(path.stat().st_size for path in victims)
    for path in victims:
        path.unlink()
    return {"files": len(victims), "bytes": deleted_bytes}


def clean_cache(paths: ReplayPaths, *, allow_shared_cache_cleanup: bool) -> dict[str, int]:
    cache_root = paths.herbie_cache.resolve()
    replay_root = paths.root.resolve()
    if not cache_root.exists():
        return {"files": 0, "dirs": 0, "bytes": 0}
    if not allow_shared_cache_cleanup and not cache_root.is_relative_to(replay_root):
        raise RuntimeError(
            f"Refusing to clean cache outside replay root: {cache_root}. "
            "Use --allow-shared-cache-cleanup only for an intentional isolated cache."
        )

    files = [path for path in cache_root.rglob("*") if path.is_file()]
    dirs = [path for path in cache_root.iterdir() if path.is_dir()]
    deleted_bytes = sum(path.stat().st_size for path in files)
    for child in cache_root.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()
    return {"files": len(files), "dirs": len(dirs), "bytes": deleted_bytes}


def write_manifest(
    init: str,
    paths: ReplayPaths,
    *,
    job_id: str,
    slurm: dict[str, str],
    validation: dict[str, Any],
    timings: dict[str, str | float],
    cache_cleanup: dict[str, int],
    llm_prune: dict[str, int],
    command: list[str],
) -> Path:
    norm = normalise_init(init)
    manifest_path = paths.manifest_dir / f"{norm}.json"
    manifest = {
        "init": init,
        "normalised_init": norm,
        "job_id": job_id,
        "status": validation["status"],
        "git_commit": git_commit(),
        "paths": {key: str(value) for key, value in asdict(paths).items()},
        "slurm": slurm,
        "timings": timings,
        "validation": validation,
        "cleanup": {
            "herbie_cache": cache_cleanup,
            "llm_temp_attempts": llm_prune,
        },
        "command": command,
        "upload_control": {
            "CLYFAR_ENABLE_UPLOAD": "0",
            "LLM_SKIP_UPLOAD": "1",
            "CLYFAR_SKIP_INTERNAL_EXPORT": "1",
        },
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True))
    return manifest_path


def write_quicklook(
    init: str,
    paths: ReplayPaths,
    *,
    validation: dict[str, Any],
    manifest_path: Path,
) -> Path:
    norm = normalise_init(init)
    quicklook_path = paths.quicklook_dir / f"{norm}.md"
    counts = validation["counts"]
    errors = validation["errors"]
    lines = [
        f"# Clyfar Replay Quicklook {norm}",
        "",
        f"- Status: {validation['status']}",
        f"- Manifest: {manifest_path}",
        f"- Full parquets: {counts.get('full_parquets', 0)}",
        f"- Dailymax parquets: {counts.get('dailymax_parquets', 0)}",
        f"- Representative GEFS files: {counts.get('gefs_representative_files', 0)}",
        f"- Export JSON files: {counts.get('export_json_files', 0)}",
        f"- Figure PNG files: {counts.get('figure_files', 0)}",
        f"- CASE files: {counts.get('case_files', 0)}",
        "",
    ]
    if errors:
        lines.append("## Errors")
        lines.extend(f"- {error}" for error in errors)
        lines.append("")
    lines.append("## Key Paths")
    for key, value in validation["paths"].items():
        lines.append(f"- {key}: `{value}`")
    quicklook_path.write_text("\n".join(lines) + "\n")

    json_path = paths.quicklook_dir / f"{norm}.json"
    json_path.write_text(json.dumps(validation, indent=2, sort_keys=True))
    return quicklook_path


def append_ledger(paths: ReplayPaths, row: dict[str, Any]) -> None:
    exists = paths.ledger_path.exists()
    with paths.ledger_path.open("a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=LEDGER_FIELDS)
        if not exists:
            writer.writeheader()
        writer.writerow({field: row.get(field, "") for field in LEDGER_FIELDS})


def successful_inits_from_ledger(ledger_path: Path) -> set[str]:
    if not ledger_path.exists():
        return set()
    with ledger_path.open(newline="") as f:
        return {
            row["init"]
            for row in csv.DictReader(f)
            if row.get("status") == "SUCCESS" and row.get("init")
        }


def process_init(
    init: str,
    paths: ReplayPaths,
    *,
    cpus: int,
    mem: str,
    walltime: str,
    account: str | None,
    partition: str | None,
    ffion_version: str | None,
    ffion_manifest: str | None,
    poll_seconds: int,
    expected_members: int,
    clean_after_success: bool,
    allow_shared_cache_cleanup: bool,
    skip_validator: bool,
) -> None:
    started = dt.datetime.utcnow()
    command = build_sbatch_command(
        init,
        paths,
        cpus=cpus,
        mem=mem,
        walltime=walltime,
        account=account,
        partition=partition,
        ffion_version=ffion_version,
        ffion_manifest=ffion_manifest,
    )
    job_id = submit_job(command)
    print(f"[{init}] submitted Slurm job {job_id}", flush=True)
    slurm = wait_for_job(job_id, poll_seconds)
    print(f"[{init}] Slurm state={slurm['state']} exit={slurm['exit_code']}", flush=True)

    validation = validate_artifacts(
        init,
        paths,
        job_id=job_id,
        expected_members=expected_members,
        skip_validator=skip_validator,
    )
    llm_prune = prune_temp_llm_attempts(init) if validation["status"] == "SUCCESS" else {"files": 0, "bytes": 0}
    if validation["status"] == "SUCCESS":
        archive_dest = archive_case(init, paths)
        validation["paths"]["case_archive"] = str(archive_dest)

    cache_cleanup = (
        clean_cache(paths, allow_shared_cache_cleanup=allow_shared_cache_cleanup)
        if clean_after_success and validation["status"] == "SUCCESS"
        else {"files": 0, "dirs": 0, "bytes": 0}
    )
    finished = dt.datetime.utcnow()
    timings = {
        "started_utc": started.isoformat() + "Z",
        "finished_utc": finished.isoformat() + "Z",
        "duration_seconds": (finished - started).total_seconds(),
    }
    manifest_path = write_manifest(
        init,
        paths,
        job_id=job_id,
        slurm=slurm,
        validation=validation,
        timings=timings,
        cache_cleanup=cache_cleanup,
        llm_prune=llm_prune,
        command=command,
    )
    quicklook_path = write_quicklook(
        init,
        paths,
        validation=validation,
        manifest_path=manifest_path,
    )
    counts = validation["counts"]
    append_ledger(
        paths,
        {
            "init": init,
            "job_id": job_id,
            "status": validation["status"],
            "slurm_state": slurm["state"],
            "slurm_exit_code": slurm["exit_code"],
            "started_utc": timings["started_utc"],
            "finished_utc": timings["finished_utc"],
            "duration_seconds": timings["duration_seconds"],
            "full_parquets": counts.get("full_parquets", 0),
            "dailymax_parquets": counts.get("dailymax_parquets", 0),
            "gefs_representative_files": counts.get("gefs_representative_files", 0),
            "export_json_files": counts.get("export_json_files", 0),
            "figure_files": counts.get("figure_files", 0),
            "case_files": counts.get("case_files", 0),
            "cache_deleted_bytes": cache_cleanup["bytes"],
            "manifest": manifest_path,
            "quicklook": quicklook_path,
            "notes": "; ".join(validation["errors"]),
        },
    )
    if validation["status"] != "SUCCESS":
        raise RuntimeError(f"[{init}] validation failed: {'; '.join(validation['errors'])}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the winter 2025-2026 Clyfar/Ffion replay serially via Slurm."
    )
    parser.add_argument("--start", default=DEFAULT_START, help="First init YYYYMMDDHH.")
    parser.add_argument("--end", default=DEFAULT_END, help="Last init YYYYMMDDHH.")
    parser.add_argument("--root", type=Path, default=default_replay_root(), help="Replay archive root.")
    parser.add_argument("--cpus", type=int, default=16, help="Slurm CPUs per task.")
    parser.add_argument("--mem", default="48G", help="Slurm memory request.")
    parser.add_argument("--time", default="01:00:00", help="Slurm walltime request.")
    parser.add_argument("--account", help="Optional Slurm account override.")
    parser.add_argument("--partition", help="Optional Slurm partition override.")
    parser.add_argument("--ffion-version", help="Fixed Ffion version to export for all replay jobs.")
    parser.add_argument("--ffion-manifest", help="Fixed Ffion manifest path to export for all replay jobs.")
    parser.add_argument("--poll-seconds", type=int, default=60, help="Slurm polling interval.")
    parser.add_argument("--expected-members", type=int, default=31, help="Expected Clyfar/GEFS member count.")
    parser.add_argument("--max-inits", type=int, help="Limit the number of inits, useful for pilot runs.")
    parser.add_argument("--resume", action="store_true", help="Skip successful inits already in the ledger.")
    parser.add_argument("--dry-run", action="store_true", help="Print planned inits and first sbatch command only.")
    parser.add_argument("--no-clean-cache", action="store_true", help="Do not clean isolated Herbie cache after success.")
    parser.add_argument(
        "--allow-shared-cache-cleanup",
        action="store_true",
        help="Allow cache cleanup even when CLYFAR_HERBIE_CACHE is outside replay root.",
    )
    parser.add_argument(
        "--skip-validator",
        action="store_true",
        help="Skip re-running validate_llm_outlook.py in the outer driver.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    paths = build_paths(args.root)
    ensure_dirs(paths)
    inits = build_init_list(args.start, args.end)
    if args.max_inits is not None:
        inits = inits[: args.max_inits]
    if args.resume:
        done = successful_inits_from_ledger(paths.ledger_path)
        inits = [init for init in inits if init not in done]

    print(f"Replay root: {paths.root}")
    print(f"Inits: {len(inits)} ({inits[0] if inits else 'none'} -> {inits[-1] if inits else 'none'})")
    print("Uploads: disabled via CLYFAR_ENABLE_UPLOAD=0 and LLM_SKIP_UPLOAD=1")

    if args.dry_run:
        if inits:
            cmd = build_sbatch_command(
                inits[0],
                paths,
                cpus=args.cpus,
                mem=args.mem,
                walltime=args.time,
                account=args.account,
                partition=args.partition,
                ffion_version=args.ffion_version,
                ffion_manifest=args.ffion_manifest,
            )
            print("First sbatch command:")
            print(" ".join(cmd))
        return

    for init in inits:
        process_init(
            init,
            paths,
            cpus=args.cpus,
            mem=args.mem,
            walltime=args.time,
            account=args.account,
            partition=args.partition,
            ffion_version=args.ffion_version,
            ffion_manifest=args.ffion_manifest,
            poll_seconds=args.poll_seconds,
            expected_members=args.expected_members,
            clean_after_success=not args.no_clean_cache,
            allow_shared_cache_cleanup=args.allow_shared_cache_cleanup,
            skip_validator=args.skip_validator,
        )
        print(f"[{init}] validated, ledger updated, cache cleanup complete", flush=True)


if __name__ == "__main__":
    main()
