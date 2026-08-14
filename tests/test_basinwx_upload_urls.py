"""Tests for BasinWx upload URL resolution (clyfar#20).

`export/to_basinwx.py` previously read only the singular BASINWX_API_URL, so every
product it pushed — images, llm_outlooks, forecast JSON — reached basinwx.com alone
and never appeared on the basinwx.dev rehearsal mirror.

These pin the resolution order so that regression cannot come back quietly.
"""

import pytest

# to_basinwx pulls in pandas/numpy/brc_tools; skip cleanly where they are absent.
to_basinwx = pytest.importorskip(
    "export.to_basinwx",
    reason="requires the full clyfar runtime (pandas, numpy, brc_tools)",
)

resolve_upload_urls = to_basinwx.resolve_upload_urls

BOTH = "https://basinwx.com,https://basinwx.dev"


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch):
    monkeypatch.delenv("BASINWX_API_URLS", raising=False)
    monkeypatch.delenv("BASINWX_API_URL", raising=False)


def test_plural_fans_out_and_preserves_order(monkeypatch):
    """First entry is primary; order matters and must be preserved."""
    monkeypatch.setenv("BASINWX_API_URLS", BOTH)
    assert resolve_upload_urls() == ["https://basinwx.com", "https://basinwx.dev"]


def test_plural_takes_precedence_over_singular(monkeypatch):
    monkeypatch.setenv("BASINWX_API_URLS", BOTH)
    monkeypatch.setenv("BASINWX_API_URL", "https://basinwx.com")
    assert resolve_upload_urls() == ["https://basinwx.com", "https://basinwx.dev"]


def test_plural_tolerates_whitespace_slashes_and_blanks(monkeypatch):
    monkeypatch.setenv(
        "BASINWX_API_URLS", " https://basinwx.com/ ,, https://basinwx.dev/ ,"
    )
    assert resolve_upload_urls() == ["https://basinwx.com", "https://basinwx.dev"]


def test_singular_still_works_for_un_updated_cron(monkeypatch):
    """CHPC wrappers that only set the legacy var must keep uploading."""
    monkeypatch.setenv("BASINWX_API_URL", "https://basinwx.com")
    assert resolve_upload_urls() == ["https://basinwx.com"]


def test_blank_plural_falls_through_to_singular(monkeypatch):
    monkeypatch.setenv("BASINWX_API_URLS", "   ")
    monkeypatch.setenv("BASINWX_API_URL", "https://basinwx.dev")
    assert resolve_upload_urls() == ["https://basinwx.dev"]


def test_env_beats_config_file(monkeypatch):
    monkeypatch.setattr(
        to_basinwx, "load_config_urls", lambda: ("key", ["https://from-config"])
    )
    monkeypatch.setenv("BASINWX_API_URLS", "https://from-env")
    assert resolve_upload_urls() == ["https://from-env"]


def test_config_file_used_when_no_env(monkeypatch):
    monkeypatch.setattr(
        to_basinwx,
        "load_config_urls",
        lambda: ("key", ["https://cfg-a", "https://cfg-b"]),
    )
    assert resolve_upload_urls() == ["https://cfg-a", "https://cfg-b"]


def test_defaults_to_com_when_nothing_configured(monkeypatch):
    def _raise():
        raise RuntimeError("no config file")

    monkeypatch.setattr(to_basinwx, "load_config_urls", _raise)
    assert resolve_upload_urls() == ["https://basinwx.com"]
