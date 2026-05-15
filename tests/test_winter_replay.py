import importlib.util
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "run_winter_replay.py"

spec = importlib.util.spec_from_file_location("run_winter_replay", SCRIPT_PATH)
replay = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = replay
spec.loader.exec_module(replay)


def test_build_init_list_is_six_hourly_inclusive():
    assert replay.build_init_list("2025120100", "2025120112") == [
        "2025120100",
        "2025120106",
        "2025120112",
    ]


def test_sbatch_command_disables_uploads(tmp_path):
    paths = replay.build_paths(tmp_path / "replay")
    cmd = replay.build_sbatch_command(
        "2025120100",
        paths,
        cpus=16,
        mem="48G",
        walltime="01:00:00",
        ffion_version="1.1.3",
    )
    joined = " ".join(cmd)
    assert "--parsable" in cmd
    assert "CLYFAR_ENABLE_UPLOAD=0" in joined
    assert "LLM_SKIP_UPLOAD=1" in joined
    assert "CLYFAR_SKIP_INTERNAL_EXPORT=1" in joined
    assert "CLYFAR_GEFS_DATA_ROOT=" in joined
    assert "FFION_VERSION=1.1.3" in joined
    assert cmd[-3:] == [
        str(REPO_ROOT / "scripts" / "submit_clyfar.sh"),
        "2025120100",
        "--no-retry",
    ]


def test_validate_artifacts_accepts_complete_fixture(tmp_path, monkeypatch):
    paths = replay.build_paths(tmp_path / "replay")
    replay.ensure_dirs(paths)
    init = "2025120100"
    norm = replay.normalise_init(init)
    figure_key = replay.init_for_figure_glob(init)
    job_id = "12345"
    expected_members = 2

    (paths.log_dir / f"clyfar_{job_id}.out").write_text(
        "\n".join(
            [
                f"STATUS_FORECAST_EXPORT=SUCCESS init={init}",
                f"STATUS_LLM_STAGE=SUCCESS init={init}",
                f"STATUS_SUBMIT_LLM_PDF_PUSH=SKIPPED init={init} reason=upload_disabled",
            ]
        )
    )
    (paths.log_dir / f"clyfar_{job_id}.err").write_text("")

    parquets = paths.data_root / f"{norm}_run" / "parquets"
    dailymax = parquets / "dailymax"
    gefs = paths.data_root / "gefs_representative" / norm
    parquets.mkdir(parents=True)
    dailymax.mkdir()
    gefs.mkdir(parents=True)
    for member in range(1, expected_members + 1):
        clyfar_name = f"clyfar{member:03d}"
        gefs_name = f"p{member:02d}"
        (parquets / f"{clyfar_name}_df.parquet").write_text("x")
        (dailymax / f"{clyfar_name}_dailymax.parquet").write_text("x")
        for variable in replay.VARIABLES:
            (gefs / f"{norm}_{variable}_{gefs_name}_df.parquet").write_text("x")
        (paths.export_dir / f"forecast_possibility_heatmap_{clyfar_name}_{norm}.json").write_text("{}")
        (paths.export_dir / f"forecast_percentile_scenarios_{clyfar_name}_{norm}.json").write_text("{}")
    (paths.export_dir / f"forecast_exceedance_probabilities_{norm}.json").write_text("{}")
    (paths.export_dir / f"forecast_clustering_summary_{norm}.json").write_text("{}")
    (paths.export_dir / f"forecast_gefs_weather_members_{norm}.json").write_text("{}")

    (paths.fig_root / "heatmap").mkdir()
    (paths.fig_root / "meteograms").mkdir()
    for member in range(1, expected_members + 1):
        (paths.fig_root / "heatmap" / f"heatmap_UB-poss_ozone_{figure_key}_clyfar{member:03d}.png").write_text("x")
    for variable in replay.VARIABLES:
        (paths.fig_root / "meteograms" / f"meteogram_UB-repr_{variable}_{figure_key}_GEFS.png").write_text("x")

    fake_repo = tmp_path / "repo"
    case_dir = fake_repo / "data" / "json_tests" / f"CASE_{norm}"
    llm_dir = case_dir / "llm_text"
    llm_dir.mkdir(parents=True)
    (llm_dir / f"LLM-OUTLOOK-{norm}.md").write_text("# outlook\n")
    (llm_dir / f"LLM-OUTLOOK-{norm}.pdf").write_bytes(b"%PDF-1.4\n")
    monkeypatch.setattr(replay, "REPO_ROOT", fake_repo)

    result = replay.validate_artifacts(
        init,
        paths,
        job_id=job_id,
        expected_members=expected_members,
        skip_validator=True,
    )
    assert result["status"] == "SUCCESS"
    assert result["errors"] == []
    assert result["counts"]["gefs_representative_files"] == expected_members * len(replay.VARIABLES)
