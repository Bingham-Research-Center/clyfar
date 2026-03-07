from pathlib import Path

from utils.ffion_bundle import resolve_ffion_bundle

TEMPLATE_PATH = Path(__file__).resolve().parents[1] / "templates" / "llm" / "prompt_body.md"


def test_prompt_body_uses_runtime_ffion_placeholder():
    text = TEMPLATE_PATH.read_text(encoding="utf-8")
    assert "Ffion v{{FFION_VERSION}}" in text
    assert "Ffion Science" not in text


def test_prompt_body_uses_uinta_geographic_term():
    text = TEMPLATE_PATH.read_text(encoding="utf-8")
    assert "Uinta Basin" in text
    assert "ozone outlook for the Uinta Basin" in text


def test_prompt_body_non_null_cluster_read_rule():
    text = TEMPLATE_PATH.read_text(encoding="utf-8")
    assert "read all members in non-null clusters" in text
    assert "cluster IDs 1+" in text


def test_prompt_body_matches_active_ffion_prompt():
    text = TEMPLATE_PATH.read_text(encoding="utf-8")
    active = resolve_ffion_bundle().prompt_template.read_text(encoding="utf-8")
    assert text == active
