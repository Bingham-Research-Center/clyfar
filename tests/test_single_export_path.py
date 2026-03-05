from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_submit_defaults_skip_internal_export():
    text = (REPO_ROOT / "scripts" / "submit_clyfar.sh").read_text()
    assert 'CLYFAR_SKIP_INTERNAL_EXPORT="${CLYFAR_SKIP_INTERNAL_EXPORT:-1}"' in text
    assert "export CLYFAR_SKIP_INTERNAL_EXPORT" in text


def test_run_gefs_honors_skip_internal_export():
    text = (REPO_ROOT / "run_gefs_clyfar.py").read_text()
    assert 'CLYFAR_SKIP_INTERNAL_EXPORT' in text
    assert "Skipping internal BasinWx export in run_gefs_clyfar" in text
