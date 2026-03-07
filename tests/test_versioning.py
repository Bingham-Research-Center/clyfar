from pathlib import Path

from utils import versioning


def test_get_clyfar_version_from_init_file(tmp_path, monkeypatch):
    fake_init = tmp_path / "__init__.py"
    fake_init.write_text("__version__ = '9.9.9'\n", encoding="utf-8")

    monkeypatch.delenv("CLYFAR_VERSION", raising=False)
    monkeypatch.setattr(versioning, "_INIT_PATH", fake_init)

    assert versioning.get_clyfar_version(default="0.0.0") == "9.9.9"


def test_get_clyfar_version_env_override(monkeypatch):
    monkeypatch.setenv("CLYFAR_VERSION", "v2.3.4")
    assert versioning.get_clyfar_version(default="0.0.0") == "2.3.4"


def test_get_ffion_version_repo_default(monkeypatch):
    monkeypatch.delenv("FFION_VERSION", raising=False)
    assert versioning.get_ffion_version(default="0.0.0") == "1.1.3"


def test_get_ffion_version_env_override(monkeypatch):
    monkeypatch.setenv("FFION_VERSION", "ffion-v1.1.7")
    assert versioning.get_ffion_version(default="0.0.0") == "1.1.7"


def test_normalise_version_variants():
    assert versioning._normalise_version("v1.2.3") == "1.2.3"
    assert versioning._normalise_version("ffion-v1.2.3") == "1.2.3"
    assert versioning._normalise_version("1.2.3") == "1.2.3"
