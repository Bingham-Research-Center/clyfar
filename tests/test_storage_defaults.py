from pathlib import Path

from nwp import gefsdata
from utils import utils


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_default_herbie_cache_does_not_fall_back_to_repo(monkeypatch, tmp_path):
    monkeypatch.delenv("CLYFAR_HERBIE_CACHE", raising=False)
    monkeypatch.setenv("USER", "clyfar_no_such_scratch_user")
    monkeypatch.setattr(gefsdata.tempfile, "gettempdir", lambda: str(tmp_path))

    cache_dir = gefsdata._default_herbie_cache_dir()

    assert cache_dir == tmp_path / "clyfar_herbie"
    assert REPO_ROOT not in [cache_dir, *cache_dir.parents]


def test_configured_herbie_cache_still_wins(monkeypatch, tmp_path):
    configured = tmp_path / "configured_cache"
    monkeypatch.setenv("CLYFAR_HERBIE_CACHE", str(configured))

    assert gefsdata._default_herbie_cache_dir() == configured


def test_performance_log_uses_runtime_env_override(monkeypatch, tmp_path):
    output_log = tmp_path / "logs" / "performance_log.txt"
    monkeypatch.setenv("CLYFAR_PERFORMANCE_LOG", str(output_log))

    @utils.configurable_timer(log_file="performance_log.txt")
    def sample():
        return "ok"

    assert sample() == "ok"
    assert output_log.read_text().startswith("sample,")


def test_llm_outlook_default_case_root_is_not_repo_local():
    script = REPO_ROOT / "scripts" / "run_llm_outlook.sh"
    text = script.read_text()

    assert "$CLYFAR_DIR/data/json_tests" not in text
    assert "$OUTPUT_BASE/json_tests" in text
