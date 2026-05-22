#!/bin/bash
set -euo pipefail
umask 022

DEFAULT_ARCHIVE_ROOT="${CLYFAR_REPLAY_ARCHIVE_ROOT:-/uufs/chpc.utah.edu/common/home/lawson-group6/clyfar/replay/winter_2025_2026}"
DEFAULT_WORK_ROOT="${CLYFAR_REPLAY_ROOT:-/scratch/general/vast/u0737349/clyfar_replay/winter_2025_2026}"
DEFAULT_PUBLIC_ROOT="${CLYFAR_PUBLIC_HTML_ROOT:-$HOME/public_html/clyfar/replay/winter_2025_2026}"

usage() {
    cat <<'EOF'
Usage:
  scripts/publish_replay_to_public_html.sh --init YYYYMMDDHH --figstamp HH [OPTIONS]
  scripts/publish_replay_to_public_html.sh --init YYYYMMDD_HHMMZ --figstamp HH [OPTIONS]

Required:
  --init YYYYMMDDHH|YYYYMMDD_HHMMZ   Case init to publish.
  --figstamp HH                      Figure hour stamp used in filenames (00, 06, 12, 18).

Options:
  --src-root PATH        Replay root to copy from. Default: auto-detect archive root, then work root.
  --public-root PATH     Public HTML root. Default: $HOME/public_html/clyfar/replay/winter_2025_2026
  --dry-run              Print planned actions without copying or writing HTML.
  --help                 Show this help.
EOF
}

die() {
    echo "ERROR: $*" >&2
    exit 1
}

normalize_init() {
    local raw="$1"
    if [[ "$raw" =~ ^[0-9]{10}$ ]]; then
        echo "${raw:0:8}_${raw:8:2}00Z"
        return
    fi
    if [[ "$raw" =~ ^[0-9]{8}_[0-9]{4}Z$ ]]; then
        echo "$raw"
        return
    fi
    die "Unsupported init format: $raw"
}

pick_source_root() {
    local explicit="${1:-}"
    local case_id="$2"

    if [[ -n "$explicit" ]]; then
        [[ -d "$explicit" ]] || die "Source root not found: $explicit"
        echo "$explicit"
        return
    fi

    local candidates=(
        "$DEFAULT_ARCHIVE_ROOT"
        "$DEFAULT_WORK_ROOT"
    )

    for root in "${candidates[@]}"; do
        if [[ -d "$root/cases/$case_id" ]]; then
            echo "$root"
            return
        fi
        if [[ -d "$root/data/json_tests/$case_id" ]]; then
            echo "$root"
            return
        fi
    done

    die "Could not locate $case_id under the default replay roots"
}

rsync_tree() {
    local src="$1"
    local dst="$2"
    if [[ ! -d "$src" ]]; then
        return 0
    fi
    mkdir -p "$dst"
    rsync -a --delete --chmod=D755,F644 \
        --exclude='index.html' \
        --exclude='*.tmp' \
        --exclude='llm_text/archive/' \
        "$src"/ "$dst"/
}

rsync_png_subset() {
    local src="$1"
    local dst="$2"
    local fig_key="$3"
    if [[ ! -d "$src" ]]; then
        return 0
    fi
    mkdir -p "$dst"
    rsync -a --delete --prune-empty-dirs --chmod=D755,F644 \
        --include='*/' \
        --include="*${fig_key}*.png" \
        --exclude='*' \
        "$src"/ "$dst"/
}

copy_if_present() {
    local src="$1"
    local dst="$2"
    if [[ -f "$src" ]]; then
        mkdir -p "$(dirname "$dst")"
        cp "$src" "$dst"
        chmod 644 "$dst"
    fi
}

create_html() {
    local public_root="$1"
    local case_dir="$2"
    local source_root="$3"
    local case_id="$4"
    local norm_init="$5"
    local figstamp="$6"

    python3 - "$public_root" "$case_dir" "$source_root" "$case_id" "$norm_init" "$figstamp" <<'PY'
from __future__ import annotations

import html
import json
import re
import sys
from datetime import datetime
from pathlib import Path

public_root = Path(sys.argv[1])
case_dir = Path(sys.argv[2])
source_root = Path(sys.argv[3])
case_id = sys.argv[4]
norm_init = sys.argv[5]
figstamp = sys.argv[6]
cases_root = public_root / "cases"


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def rel(path: Path) -> str:
    return path.relative_to(case_dir).as_posix()


def read_json(path: Path) -> dict[str, object]:
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def fmt_bytes(value: object) -> str:
    try:
        size = float(value)
    except Exception:
        return "n/a"
    units = ["B", "KiB", "MiB", "GiB", "TiB"]
    for unit in units:
        if size < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.1f} {unit}"
        size /= 1024
    return "n/a"


def fmt_duration(value: object) -> str:
    try:
        seconds = float(value)
    except Exception:
        return "n/a"
    if seconds < 60:
        return f"{seconds:.0f}s"
    if seconds < 3600:
        return f"{seconds / 60:.1f}m"
    return f"{seconds / 3600:.1f}h"


def init_from_case(path: Path) -> datetime:
    m = re.match(r"CASE_(\d{8})_(\d{4})Z$", path.name)
    if not m:
        raise ValueError(path.name)
    return datetime.strptime(f"{m.group(1)}{m.group(2)[:2]}", "%Y%m%d%H")


def gallery_cards(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(p for p in root.rglob("*.png") if p.is_file())


def list_files(root: Path, suffixes: tuple[str, ...]) -> list[Path]:
    if not root.exists():
        return []
    return sorted(
        p for p in root.iterdir() if p.is_file() and p.suffix.lower() in suffixes
    )


def render_summary(manifest: dict[str, object], quicklook: dict[str, object]) -> str:
    validation = manifest.get("validation", {})
    counts = validation.get("counts", {}) if isinstance(validation, dict) else {}
    slurm = manifest.get("slurm", {}) if isinstance(manifest.get("slurm", {}), dict) else {}
    timings = manifest.get("timings", {}) if isinstance(manifest.get("timings", {}), dict) else {}
    cleanup = manifest.get("cleanup", {}) if isinstance(manifest.get("cleanup", {}), dict) else {}
    herbie_cache = cleanup.get("herbie_cache") if isinstance(cleanup.get("herbie_cache"), dict) else {}

    items = [
        ("Status", validation.get("status", quicklook.get("status", "n/a"))),
        ("Job ID", manifest.get("job_id", "n/a")),
        ("Slurm state", slurm.get("state", "n/a")),
        ("Exit code", slurm.get("exit_code", "n/a")),
        ("Duration", fmt_duration(timings.get("duration_seconds"))),
        ("Slurm elapsed", timings.get("slurm_elapsed", slurm.get("elapsed", "n/a"))),
        ("Driver wait", fmt_duration(timings.get("driver_wait_seconds"))),
        ("Postprocess", fmt_duration(timings.get("postprocess_seconds"))),
        ("Git commit", manifest.get("git_commit", "n/a")),
        ("Heatmaps", counts.get("figure_heatmaps", counts.get("figure_files", "n/a"))),
        ("Meteograms", counts.get("figure_meteograms", "n/a")),
        ("Export JSON", counts.get("export_json_files", "n/a")),
        ("CASE files", counts.get("case_files", "n/a")),
        ("Cache freed", fmt_bytes(herbie_cache.get("bytes"))),
    ]

    parts = ['<div class="stats">']
    for label, value in items:
        parts.append(
            f'<div class="stat"><span>{esc(label)}</span><strong>{esc(value)}</strong></div>'
        )
    parts.append("</div>")
    return "\n".join(parts)


def render_links(title: str, files: list[Path], *, kind: str = "file") -> str:
    if not files:
        return ""
    items = "\n".join(
        f'<li><a href="{esc(rel(path))}">{esc(path.name)}</a></li>' for path in files
    )
    return (
        f'<section class="panel"><h2>{esc(title)} <span class="badge">{len(files)}</span></h2>'
        f'<ul class="file-list {esc(kind)}">\n{items}\n</ul></section>'
    )


def render_gallery(title: str, roots: list[tuple[str, Path]]) -> str:
    blocks: list[str] = []
    for label, root in roots:
        cards = gallery_cards(root)
        if not cards:
            continue
        thumbs = []
        for path in cards:
            relative = rel(path)
            thumbs.append(
                "<a class=\"thumb\" href=\"{href}\">"
                "<img src=\"{href}\" alt=\"{alt}\" loading=\"lazy\" decoding=\"async\">"
                "<span>{name}</span></a>".format(
                    href=esc(relative),
                    alt=esc(path.name),
                    name=esc(path.name),
                )
            )
        blocks.append(
            f'<section class="panel"><h3>{esc(label)} <span class="badge">{len(cards)}</span></h3>'
            f'<div class="gallery">{"".join(thumbs)}</div></section>'
        )
    if not blocks:
        return ""
    return f'<section class="panel-group"><h2>{esc(title)}</h2>{"".join(blocks)}</section>'


def render_case_page() -> None:
    manifest = read_json(case_dir / "manifest.json")
    quicklook = read_json(case_dir / "quicklook.json")
    generation_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    root_link = "../../index.html"

    core_docs = [
        case_dir / "manifest.json",
        case_dir / "quicklook.md",
        case_dir / "quicklook.json",
        case_dir / f"forecast_clustering_summary_{norm_init}.json",
        case_dir / "llm_text" / f"forecast_prompt_{norm_init}.md",
        case_dir / "llm_text" / f"LLM-OUTLOOK-{norm_init}.md",
        case_dir / "llm_text" / f"LLM-OUTLOOK-{norm_init}.pdf",
    ]
    core_docs = [path for path in core_docs if path.exists()]

    json_groups = [
        ("Possibility JSON", case_dir / "possibilities"),
        ("Percentile JSON", case_dir / "percentiles"),
        ("Probability JSON", case_dir / "probs"),
        ("Weather JSON", case_dir / "weather"),
    ]

    gallery_groups = [
        (
            "Operational figures",
            [
                ("Heatmaps", case_dir / "figures" / "heatmap"),
                ("Meteograms", case_dir / "figures" / "meteograms"),
                ("Optional percentiles", case_dir / "figures" / "optim_pessim"),
            ],
        ),
        (
            "CASE figures",
            [
                ("Quantities", case_dir / "figs" / "quantities"),
                ("Probabilities", case_dir / "figs" / "probabilities"),
                ("Percentile scenarios", case_dir / "figs" / "scenarios_percentiles"),
                ("Possibility scenarios", case_dir / "figs" / "scenarios_possibility"),
                ("Daily-max heatmaps", case_dir / "figs" / "possibility" / "heatmaps"),
                ("Percentile dendrograms", case_dir / "figs" / "dendrograms" / "percentiles"),
                ("Possibility dendrograms", case_dir / "figs" / "dendrograms" / "possibilities"),
            ],
        ),
    ]

    manifest = manifest if isinstance(manifest, dict) else {}
    quicklook = quicklook if isinstance(quicklook, dict) else {}

    slurm = manifest.get("slurm", {}) if isinstance(manifest.get("slurm", {}), dict) else {}
    timings = manifest.get("timings", {}) if isinstance(manifest.get("timings", {}), dict) else {}
    validation = manifest.get("validation", {}) if isinstance(manifest.get("validation", {}), dict) else {}
    counts = validation.get("counts", {}) if isinstance(validation, dict) else {}
    errors = validation.get("errors", []) if isinstance(validation, dict) else []

    html_parts = [
        "<!DOCTYPE html>",
        "<html lang=\"en\">",
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>Clyfar replay review - {esc(case_id)}</title>",
        "<style>",
        """
        :root {
          color-scheme: light;
          --bg: #f5f7fb;
          --panel: rgba(255, 255, 255, 0.92);
          --panel-strong: #ffffff;
          --ink: #102033;
          --muted: #5d6b7b;
          --line: #d8e0ea;
          --accent: #0f766e;
          --accent-2: #7c3aed;
          --shadow: 0 14px 35px rgba(15, 23, 42, 0.08);
          --radius: 18px;
        }
        * { box-sizing: border-box; }
        body {
          margin: 0;
          font-family: "Trebuchet MS", "Segoe UI", Arial, sans-serif;
          background:
            radial-gradient(circle at top left, rgba(15, 118, 110, 0.09), transparent 28%),
            radial-gradient(circle at top right, rgba(124, 58, 237, 0.08), transparent 26%),
            linear-gradient(180deg, #f8fafc 0%, #eef3f8 100%);
          color: var(--ink);
        }
        a { color: var(--accent); text-decoration: none; }
        a:hover { text-decoration: underline; }
        .wrap { max-width: 1500px; margin: 0 auto; padding: 0 1rem 2rem; }
        .hero {
          margin: 0 -1rem 1.5rem;
          padding: 2rem 1rem 1.75rem;
          color: white;
          background: linear-gradient(135deg, #0f172a 0%, #0f766e 52%, #2563eb 100%);
          box-shadow: var(--shadow);
        }
        .hero .eyebrow {
          text-transform: uppercase;
          letter-spacing: 0.18em;
          font-size: 0.75rem;
          opacity: 0.8;
          margin-bottom: 0.5rem;
        }
        .hero h1 {
          margin: 0;
          font-size: clamp(2rem, 4vw, 3.5rem);
          line-height: 1.02;
        }
        .hero .subline {
          margin: 0.65rem 0 0;
          max-width: 1100px;
          color: rgba(255, 255, 255, 0.92);
          font-size: 1rem;
        }
        .hero .links {
          display: flex;
          flex-wrap: wrap;
          gap: 0.65rem;
          margin-top: 1rem;
        }
        .chip {
          display: inline-flex;
          align-items: center;
          gap: 0.35rem;
          padding: 0.45rem 0.75rem;
          border-radius: 999px;
          background: rgba(255, 255, 255, 0.14);
          color: white;
          border: 1px solid rgba(255, 255, 255, 0.16);
          font-size: 0.92rem;
        }
        .stats {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
          gap: 0.85rem;
          margin: 1.1rem 0 1.35rem;
        }
        .stat {
          background: var(--panel-strong);
          border: 1px solid var(--line);
          border-radius: 16px;
          padding: 0.85rem 0.95rem;
          box-shadow: 0 6px 18px rgba(15, 23, 42, 0.05);
        }
        .stat span {
          display: block;
          font-size: 0.78rem;
          text-transform: uppercase;
          letter-spacing: 0.08em;
          color: var(--muted);
        }
        .stat strong {
          display: block;
          margin-top: 0.3rem;
          font-size: 1.05rem;
        }
        .panel, .panel-group > .panel {
          background: var(--panel);
          border: 1px solid var(--line);
          border-radius: var(--radius);
          box-shadow: var(--shadow);
          padding: 1rem;
          margin: 0 0 1rem;
        }
        .panel-group > h2, .panel > h2, .panel > h3 {
          margin: 0 0 0.85rem;
        }
        .panel-group {
          margin-bottom: 1rem;
        }
        .badge {
          display: inline-block;
          padding: 0.15rem 0.55rem;
          border-radius: 999px;
          background: rgba(15, 118, 110, 0.12);
          color: var(--accent);
          font-size: 0.78rem;
          font-weight: 700;
          vertical-align: middle;
        }
        .gallery {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
          gap: 0.75rem;
        }
        .thumb {
          display: flex;
          flex-direction: column;
          gap: 0.45rem;
          padding: 0.6rem;
          border-radius: 14px;
          border: 1px solid var(--line);
          background: white;
          color: var(--ink);
          text-decoration: none;
          transition: transform 120ms ease, box-shadow 120ms ease, border-color 120ms ease;
        }
        .thumb:hover {
          transform: translateY(-2px);
          border-color: rgba(15, 118, 110, 0.45);
          box-shadow: 0 12px 22px rgba(15, 23, 42, 0.08);
          text-decoration: none;
        }
        .thumb img {
          width: 100%;
          height: 180px;
          object-fit: contain;
          border-radius: 10px;
          background: linear-gradient(180deg, #fafcff, #eef3f8);
        }
        .thumb span {
          display: block;
          font-size: 0.8rem;
          line-height: 1.25;
          color: var(--muted);
          word-break: break-word;
        }
        .file-list {
          margin: 0;
          padding-left: 1.2rem;
        }
        .file-list li + li {
          margin-top: 0.35rem;
        }
        .note {
          color: var(--muted);
          font-size: 0.92rem;
        }
        .warning {
          border-left: 4px solid #d97706;
          padding-left: 0.75rem;
          color: #7c2d12;
        }
        footer {
          color: var(--muted);
          font-size: 0.9rem;
          margin-top: 1.5rem;
          padding: 1rem 0 0.5rem;
        }
        @media (max-width: 640px) {
          .hero { margin-left: -1rem; margin-right: -1rem; }
          .gallery { grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); }
          .thumb img { height: 150px; }
        }
        """,
        "</style>",
        "</head>",
        "<body>",
        '<div class="wrap">',
        '<header class="hero">',
        '<div class="eyebrow">Clyfar replay review</div>',
        f"<h1>{esc(case_id)}</h1>",
        (
            f'<p class="subline">Init {esc(norm_init)} · FIGSTAMP {esc(figstamp)} · '
            f'Source root: {esc(source_root)} · Generated {esc(generation_time)}</p>'
        ),
        '<div class="links">',
        f'<a class="chip" href="{root_link}">Back to replay index</a>',
        f'<a class="chip" href="manifest.json">Manifest</a>',
        f'<a class="chip" href="quicklook.md">Quicklook</a>',
        f'<a class="chip" href="llm_text/LLM-OUTLOOK-{norm_init}.pdf">LLM PDF</a>',
        f'<a class="chip" href="llm_text/LLM-OUTLOOK-{norm_init}.md">LLM Markdown</a>',
        "</div>",
        "</header>",
        render_summary(manifest, quicklook),
        "<section class=\"panel\">",
        "<h2>Key context</h2>",
        (
            f"<p class=\"note\">This page groups the copied case tree, operational figures, "
            f"and case-level diagnostics into one browseable view. The raw files remain "
            f"linkable from their copied locations.</p>"
        ),
        "<div class=\"stats\">",
        f'<div class="stat"><span>Manifest state</span><strong>{esc(validation.get("status", quicklook.get("status", "n/a")) if isinstance(validation, dict) else quicklook.get("status", "n/a"))}</strong></div>',
        f'<div class="stat"><span>Local files</span><strong>{esc(counts.get("figure_files", "n/a"))} figures</strong></div>',
        f'<div class="stat"><span>Raw JSON</span><strong>{esc(counts.get("export_json_files", "n/a"))} exports</strong></div>',
        f'<div class="stat"><span>Errors</span><strong>{esc(len(errors) if isinstance(errors, list) else 0)}</strong></div>',
        "</div>",
        "</section>",
    ]

    if manifest:
        html_parts.extend(
            [
                "<section class=\"panel\">",
                "<h2>Run metadata</h2>",
                "<table>",
                "<tbody>",
                f"<tr><th>Job ID</th><td>{esc(manifest.get('job_id', 'n/a'))}</td></tr>",
                f"<tr><th>Slurm state</th><td>{esc(slurm.get('state', 'n/a'))}</td></tr>",
                f"<tr><th>Slurm exit</th><td>{esc(slurm.get('exit_code', 'n/a'))}</td></tr>",
                f"<tr><th>Duration</th><td>{esc(fmt_duration(timings.get('duration_seconds')))}</td></tr>",
                f"<tr><th>Submitted UTC</th><td>{esc(timings.get('submitted_utc', 'n/a'))}</td></tr>",
                f"<tr><th>Slurm finished UTC</th><td>{esc(timings.get('slurm_finished_utc', 'n/a'))}</td></tr>",
                f"<tr><th>Slurm elapsed</th><td>{esc(timings.get('slurm_elapsed', slurm.get('elapsed', 'n/a')))}</td></tr>",
                f"<tr><th>Driver wait</th><td>{esc(fmt_duration(timings.get('driver_wait_seconds')))}</td></tr>",
                f"<tr><th>Postprocess</th><td>{esc(fmt_duration(timings.get('postprocess_seconds')))}</td></tr>",
                f"<tr><th>Git commit</th><td><code>{esc(manifest.get('git_commit', 'n/a'))}</code></td></tr>",
                f"<tr><th>Replay source</th><td><code>{esc(source_root)}</code></td></tr>",
                f"<tr><th>Replay case</th><td><code>{esc(case_dir)}</code></td></tr>",
                "</tbody>",
                "</table>",
                "</section>",
            ]
        )

    if errors:
        html_parts.extend(
            [
                '<section class="panel warning">',
                "<h2>Validation issues</h2>",
                "<ul class=\"file-list\">",
                "".join(f"<li>{esc(item)}</li>" for item in errors),
                "</ul>",
                "</section>",
            ]
        )

    html_parts.append(render_gallery("Operational figures", gallery_groups[0][1]))
    html_parts.append(render_gallery("CASE figures", gallery_groups[1][1]))

    json_sections = []
    for label, root in json_groups:
        files = list_files(root, (".json",))
        if files:
            json_sections.append(render_links(label, files))
    json_sections.append(render_links("Core documents", core_docs, kind="docs"))
    html_parts.extend(part for part in json_sections if part)

    html_parts.extend(
        [
            "<footer>",
            f"Generated {esc(generation_time)} from {esc(source_root)}.",
            "</footer>",
            "</div>",
            "</body>",
            "</html>",
        ]
    )

    case_dir.mkdir(parents=True, exist_ok=True)
    (case_dir / "index.html").write_text("\n".join(html_parts) + "\n")


def render_root_page() -> None:
    case_dirs = []
    if cases_root.exists():
        for path in sorted(cases_root.iterdir()):
            if path.is_dir() and re.match(r"CASE_\d{8}_\d{4}Z$", path.name):
                case_dirs.append(path)

    case_dirs.sort(key=init_from_case, reverse=True)
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    rows = []
    for path in case_dirs:
        manifest = read_json(path / "manifest.json")
        quicklook = read_json(path / "quicklook.json")
        validation = manifest.get("validation", {}) if isinstance(manifest.get("validation", {}), dict) else {}
        counts = validation.get("counts", {}) if isinstance(validation, dict) else {}
        status = validation.get("status", quicklook.get("status", "n/a")) if isinstance(validation, dict) else quicklook.get("status", "n/a")
        slurm = manifest.get("slurm", {}) if isinstance(manifest.get("slurm", {}), dict) else {}
        timings = manifest.get("timings", {}) if isinstance(manifest.get("timings", {}), dict) else {}
        init_label = path.name.replace("CASE_", "")
        rows.append(
            "<a class=\"case-card\" href=\"cases/{case}/index.html\">"
            "<div class=\"case-card__top\">"
            "<strong>{case}</strong>"
            "<span class=\"badge\">{status}</span>"
            "</div>"
            "<div class=\"case-card__meta\">"
            "<span>Job {job}</span>"
            "<span>Slurm {state}</span>"
            "<span>{duration} total</span>"
            "<span>{heatmaps} heatmaps</span>"
            "<span>{meteograms} meteograms</span>"
            "<span>{jsons} JSON</span>"
            "</div>"
            "</a>".format(
                case=esc(path.name),
                status=esc(status),
                job=esc(manifest.get("job_id", "n/a")),
                state=esc(slurm.get("state", "n/a")),
                duration=esc(fmt_duration(timings.get("duration_seconds"))),
                heatmaps=esc(counts.get("figure_heatmaps", counts.get("figure_files", "n/a"))),
                meteograms=esc(counts.get("figure_meteograms", "n/a")),
                jsons=esc(counts.get("export_json_files", "n/a")),
            )
        )

    root_html = [
        "<!DOCTYPE html>",
        "<html lang=\"en\">",
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        "<title>Clyfar replay review index</title>",
        "<style>",
        """
        :root {
          color-scheme: light;
          --bg: #f5f7fb;
          --panel: rgba(255, 255, 255, 0.92);
          --ink: #102033;
          --muted: #5d6b7b;
          --line: #d8e0ea;
          --accent: #0f766e;
          --shadow: 0 14px 35px rgba(15, 23, 42, 0.08);
          --radius: 18px;
        }
        * { box-sizing: border-box; }
        body {
          margin: 0;
          font-family: "Trebuchet MS", "Segoe UI", Arial, sans-serif;
          background:
            radial-gradient(circle at top left, rgba(15, 118, 110, 0.09), transparent 28%),
            radial-gradient(circle at top right, rgba(124, 58, 237, 0.08), transparent 26%),
            linear-gradient(180deg, #f8fafc 0%, #eef3f8 100%);
          color: var(--ink);
        }
        a { color: var(--accent); text-decoration: none; }
        .wrap { max-width: 1200px; margin: 0 auto; padding: 0 1rem 2rem; }
        .hero {
          margin: 0 -1rem 1.5rem;
          padding: 2rem 1rem 1.75rem;
          color: white;
          background: linear-gradient(135deg, #0f172a 0%, #0f766e 52%, #2563eb 100%);
          box-shadow: var(--shadow);
        }
        .hero .eyebrow {
          text-transform: uppercase;
          letter-spacing: 0.18em;
          font-size: 0.75rem;
          opacity: 0.8;
          margin-bottom: 0.5rem;
        }
        .hero h1 {
          margin: 0;
          font-size: clamp(2rem, 4vw, 3.25rem);
          line-height: 1.02;
        }
        .hero p {
          margin: 0.65rem 0 0;
          max-width: 1000px;
          color: rgba(255, 255, 255, 0.92);
        }
        .panel {
          background: var(--panel);
          border: 1px solid var(--line);
          border-radius: var(--radius);
          box-shadow: var(--shadow);
          padding: 1rem;
          margin: 0 0 1rem;
        }
        .case-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
          gap: 0.85rem;
        }
        .case-card {
          display: block;
          padding: 0.9rem;
          border-radius: 16px;
          border: 1px solid var(--line);
          background: white;
          color: var(--ink);
          box-shadow: 0 6px 18px rgba(15, 23, 42, 0.05);
          transition: transform 120ms ease, box-shadow 120ms ease, border-color 120ms ease;
        }
        .case-card:hover {
          transform: translateY(-2px);
          border-color: rgba(15, 118, 110, 0.45);
          box-shadow: 0 12px 22px rgba(15, 23, 42, 0.08);
          text-decoration: none;
        }
        .case-card__top {
          display: flex;
          justify-content: space-between;
          gap: 0.5rem;
          align-items: center;
          margin-bottom: 0.65rem;
        }
        .case-card__top strong {
          font-size: 1.02rem;
        }
        .case-card__meta {
          display: flex;
          flex-wrap: wrap;
          gap: 0.5rem 0.75rem;
          color: var(--muted);
          font-size: 0.88rem;
        }
        .badge {
          display: inline-block;
          padding: 0.15rem 0.55rem;
          border-radius: 999px;
          background: rgba(15, 118, 110, 0.12);
          color: var(--accent);
          font-size: 0.78rem;
          font-weight: 700;
        }
        .note { color: var(--muted); }
        footer { color: var(--muted); font-size: 0.9rem; padding: 0.75rem 0 0.25rem; }
        """,
        "</style>",
        "</head>",
        "<body>",
        '<div class="wrap">',
        '<header class="hero">',
        '<div class="eyebrow">Clyfar replay index</div>',
        "<h1>Browse published replay cases</h1>",
        (
            "<p>Open a case card for the copied figures, raw JSON diagnostics, Ffion PDFs, "
            "quicklook, and manifest. This root page stays small; each case has its own "
            "browseable subfolder.</p>"
        ),
        "</header>",
        "<section class=\"panel\">",
        f"<p class=\"note\">Published {esc(now)} under <code>{esc(public_root)}</code>.</p>",
        "</section>",
        "<section class=\"panel\">",
        "<div class=\"case-grid\">",
        "".join(rows) if rows else "<p class=\"note\">No published cases found yet.</p>",
        "</div>",
        "</section>",
        "<footer>Generated by scripts/publish_replay_to_public_html.sh.</footer>",
        "</div>",
        "</body>",
        "</html>",
    ]

    public_root.mkdir(parents=True, exist_ok=True)
    (public_root / "index.html").write_text("\n".join(root_html) + "\n")


render_case_page()
render_root_page()
PY
}

main() {
    local init=""
    local figstamp=""
    local src_root=""
    local public_root="$DEFAULT_PUBLIC_ROOT"
    local dry_run=false

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --init)
                init="${2:-}"
                shift 2
                ;;
            --figstamp)
                figstamp="${2:-}"
                shift 2
                ;;
            --src-root)
                src_root="${2:-}"
                shift 2
                ;;
            --public-root)
                public_root="${2:-}"
                shift 2
                ;;
            --dry-run)
                dry_run=true
                shift
                ;;
            --help|-h)
                usage
                return 0
                ;;
            *)
                die "Unknown argument: $1"
                ;;
        esac
    done

    [[ -n "$init" ]] || die "--init is required"
    [[ -n "$figstamp" ]] || die "--figstamp is required"

    local norm_init
    norm_init="$(normalize_init "$init")"
    local init_date="${norm_init:0:8}"
    local init_hour="${norm_init:9:2}"
    local case_id="CASE_${norm_init}"
    local figure_key="${init_date}-${figstamp}00"

    [[ "$figstamp" =~ ^(00|06|12|18)$ ]] || die "--figstamp must be one of 00, 06, 12, or 18"
    [[ "$figstamp" == "$init_hour" ]] || die "--figstamp ($figstamp) must match the init hour ($init_hour)"

    local source_root
    source_root="$(pick_source_root "$src_root" "$case_id")"
    local source_case_dir="$source_root/cases/$case_id"
    local alt_source_case_dir="$source_root/data/json_tests/$case_id"
    if [[ ! -d "$source_case_dir" && -d "$alt_source_case_dir" ]]; then
        source_case_dir="$alt_source_case_dir"
    fi
    [[ -d "$source_case_dir" ]] || die "Case directory not found: $source_case_dir"

    local public_case_dir="$public_root/cases/$case_id"

    echo "Init:         $norm_init"
    echo "FIGSTAMP:     $figstamp"
    echo "Figure key:   $figure_key"
    echo "Source root:   $source_root"
    echo "Source case:   $source_case_dir"
    echo "Public root:   $public_root"
    echo "Public case:   $public_case_dir"
    echo "URL root:      http://home.chpc.utah.edu/~${USER}/clyfar/replay/winter_2025_2026/"
    echo "URL case:      http://home.chpc.utah.edu/~${USER}/clyfar/replay/winter_2025_2026/cases/${case_id}/"

    if [[ "$dry_run" == "true" ]]; then
        echo "Dry run only; no files copied and no HTML written."
        return 0
    fi

    mkdir -p "$public_case_dir"

    rsync_tree "$source_case_dir" "$public_case_dir"
    rsync_png_subset "$source_root/figures/heatmap" "$public_case_dir/figures/heatmap" "$figure_key"
    rsync_png_subset "$source_root/figures/meteograms" "$public_case_dir/figures/meteograms" "$figure_key"
    rsync_png_subset "$source_root/figures/optim_pessim" "$public_case_dir/figures/optim_pessim" "$figure_key"

    copy_if_present "$source_root/manifests/${norm_init}.json" "$public_case_dir/manifest.json"
    copy_if_present "$source_root/quicklooks/${norm_init}.md" "$public_case_dir/quicklook.md"
    copy_if_present "$source_root/quicklooks/${norm_init}.json" "$public_case_dir/quicklook.json"

    create_html "$public_root" "$public_case_dir" "$source_root" "$case_id" "$norm_init" "$figstamp"
}

main "$@"
