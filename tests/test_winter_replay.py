import csv
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
    assert "CLYFAR_JSON_TESTS_ROOT=" in joined
    assert "FFION_VERSION=1.1.3" in joined
    assert cmd[-3:] == [
        str(REPO_ROOT / "scripts" / "submit_clyfar.sh"),
        "2025120100",
        "--no-retry",
    ]


def test_poll_seconds_default_is_30(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["run_winter_replay.py"])
    assert replay.parse_args().poll_seconds == 30


def test_replay_slurm_defaults_match_winter_profile(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["run_winter_replay.py"])
    args = replay.parse_args()

    assert args.cpus == 16
    assert args.mem == "48G"
    assert args.time == "02:00:00"
    assert args.account == "lawson-np"
    assert args.partition == "lawson-np"


def test_wait_for_job_accepts_slurm_derived_job_ids(monkeypatch):
    calls = {"squeue": 0, "sacct": 0, "sleep": []}

    def fake_run(cmd, **kwargs):
        if cmd[0] == "squeue":
            calls["squeue"] += 1
            return replay.subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        if cmd[0] == "sacct":
            calls["sacct"] += 1
            return replay.subprocess.CompletedProcess(
                cmd,
                0,
                stdout="12869709.batch|COMPLETED|0:0|00:10:00\n",
                stderr="",
            )
        raise AssertionError(f"unexpected command: {cmd}")

    monkeypatch.setattr(replay.subprocess, "run", fake_run)
    monkeypatch.setattr(replay.time, "sleep", lambda seconds: calls["sleep"].append(seconds))

    result = replay.wait_for_job("12869709", poll_seconds=1)

    assert result["state"] == "COMPLETED"
    assert result["exit_code"] == "0:0"
    assert result["elapsed"] == "00:10:00"
    assert result["observed_finished_utc"].endswith("Z")
    assert calls["squeue"] == 1
    assert calls["sacct"] == 1
    assert calls["sleep"] == []


def test_wait_for_job_retries_sacct_before_falling_back(monkeypatch):
    calls = {"squeue": 0, "sacct": 0, "sleep": []}

    def fake_run(cmd, **kwargs):
        if cmd[0] == "squeue":
            calls["squeue"] += 1
            return replay.subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        if cmd[0] == "sacct":
            calls["sacct"] += 1
            stdout = "" if calls["sacct"] < 3 else "12869709|COMPLETED|0:0|00:10:00\n"
            return replay.subprocess.CompletedProcess(cmd, 0, stdout=stdout, stderr="")
        raise AssertionError(f"unexpected command: {cmd}")

    monkeypatch.setattr(replay.subprocess, "run", fake_run)
    monkeypatch.setattr(replay.time, "sleep", lambda seconds: calls["sleep"].append(seconds))

    result = replay.wait_for_job("12869709", poll_seconds=1)

    assert result["state"] == "COMPLETED"
    assert result["exit_code"] == "0:0"
    assert result["elapsed"] == "00:10:00"
    assert result["observed_finished_utc"].endswith("Z")
    assert calls["squeue"] == 1
    assert calls["sacct"] == 3
    assert calls["sleep"] == [5, 5]


def test_quicklook_records_replay_timings(tmp_path):
    paths = replay.build_paths(tmp_path / "replay")
    replay.ensure_dirs(paths)
    timings = {
        "started_utc": "2026-05-21T00:00:00Z",
        "submitted_utc": "2026-05-21T00:00:01Z",
        "slurm_finished_utc": "2026-05-21T00:10:01Z",
        "finished_utc": "2026-05-21T00:11:01Z",
        "slurm_elapsed": "00:10:00",
        "driver_wait_seconds": 600.0,
        "postprocess_seconds": 60.0,
        "duration_seconds": 661.0,
    }
    manifest_path = paths.manifest_dir / "20251201_0000Z.json"
    manifest_path.write_text("{}")

    quicklook_path = replay.write_quicklook(
        "2025120100",
        paths,
        validation={
            "status": "SUCCESS",
            "counts": {
                "full_parquets": 0,
                "dailymax_parquets": 0,
                "gefs_representative_files": 0,
                "export_json_files": 0,
                "figure_files": 0,
                "case_files": 0,
            },
            "errors": [],
            "paths": {},
        },
        manifest_path=manifest_path,
        timings=timings,
    )

    text = quicklook_path.read_text()
    assert "Submitted UTC: 2026-05-21T00:00:01Z" in text
    assert "Slurm elapsed: 00:10:00" in text
    assert "Postprocess seconds: 60.0" in text


def test_ledger_appends_replay_timing_fields(tmp_path):
    paths = replay.build_paths(tmp_path / "replay")
    replay.ensure_dirs(paths)

    replay.append_ledger(
        paths,
        {
            "init": "2025120100",
            "job_id": "12345",
            "status": "SUCCESS",
            "slurm_state": "COMPLETED",
            "slurm_exit_code": "0:0",
            "started_utc": "2026-05-21T00:00:00Z",
            "finished_utc": "2026-05-21T00:11:01Z",
            "duration_seconds": 661.0,
            "submitted_utc": "2026-05-21T00:00:01Z",
            "slurm_finished_utc": "2026-05-21T00:10:01Z",
            "slurm_elapsed": "00:10:00",
            "driver_wait_seconds": 600.0,
            "postprocess_seconds": 60.0,
        },
    )

    with paths.ledger_path.open(newline="") as f:
        row = next(csv.DictReader(f))
    assert row["submitted_utc"] == "2026-05-21T00:00:01Z"
    assert row["slurm_elapsed"] == "00:10:00"
    assert row["postprocess_seconds"] == "60.0"


def test_append_ledger_upgrades_existing_header_for_timing_fields(tmp_path):
    paths = replay.build_paths(tmp_path / "replay")
    replay.ensure_dirs(paths)
    paths.ledger_path.write_text(
        "init,job_id,status,slurm_state,slurm_exit_code,started_utc,finished_utc,duration_seconds\n"
        "2025120100,111,SUCCESS,COMPLETED,0:0,old-start,old-finish,10.0\n"
    )

    replay.append_ledger(
        paths,
        {
            "init": "2025120106",
            "job_id": "222",
            "status": "SUCCESS",
            "slurm_state": "COMPLETED",
            "slurm_exit_code": "0:0",
            "submitted_utc": "new-submit",
            "slurm_elapsed": "00:10:00",
        },
    )

    with paths.ledger_path.open(newline="") as f:
        rows = list(csv.DictReader(f))
    assert "submitted_utc" in rows[0]
    assert rows[0]["init"] == "2025120100"
    assert rows[0]["submitted_utc"] == ""
    assert rows[1]["submitted_utc"] == "new-submit"
    assert rows[1]["slurm_elapsed"] == "00:10:00"


def test_validate_artifacts_accepts_complete_fixture(tmp_path):
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

    (paths.fig_root / "heatmap").mkdir(exist_ok=True)
    (paths.fig_root / "meteograms").mkdir(exist_ok=True)
    for member in range(1, expected_members + 1):
        (paths.fig_root / "heatmap" / f"heatmap_UB-poss_ozone_{figure_key}_clyfar{member:03d}.png").write_text("x")
    for variable in replay.VARIABLES:
        (paths.fig_root / "meteograms" / f"meteogram_UB-repr_{variable}_{figure_key}_GEFS.png").write_text("x")

    case_dir = paths.case_work_root / f"CASE_{norm}"
    llm_dir = case_dir / "llm_text"
    llm_dir.mkdir(parents=True)
    (llm_dir / f"LLM-OUTLOOK-{norm}.md").write_text("# outlook\n")
    (llm_dir / f"LLM-OUTLOOK-{norm}.pdf").write_bytes(b"%PDF-1.4\n")

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


def test_validate_artifacts_requires_immediate_previous_outlook_reference(tmp_path):
    paths = replay.build_paths(tmp_path / "replay")
    replay.ensure_dirs(paths)
    init = "2025120106"
    norm = replay.normalise_init(init)
    prev_norm = "20251201_0000Z"
    job_id = "12345"

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

    current_llm = paths.case_work_root / f"CASE_{norm}" / "llm_text"
    previous_llm = paths.case_work_root / f"CASE_{prev_norm}" / "llm_text"
    current_llm.mkdir(parents=True)
    previous_llm.mkdir(parents=True)
    (current_llm / f"LLM-OUTLOOK-{norm}.md").write_text("# outlook without prior\n")
    (current_llm / f"LLM-OUTLOOK-{norm}.pdf").write_bytes(b"%PDF-1.4\n")
    (previous_llm / f"LLM-OUTLOOK-{prev_norm}.md").write_text("# previous\n")

    result = replay.validate_artifacts(
        init,
        paths,
        job_id=job_id,
        expected_members=0,
        skip_validator=True,
    )
    assert result["status"] == "FAILED"
    assert any(prev_norm in error for error in result["errors"])
