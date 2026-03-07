from pathlib import Path

from utils import ffion_science


def test_resolve_ffion_science_bundle_from_manifest(tmp_path):
    prompt = tmp_path / "prompt.md"
    prompt.write_text("Prompt body\n", encoding="utf-8")

    bias = tmp_path / "bias.json"
    bias.write_text("[]\n", encoding="utf-8")

    qa = tmp_path / "qa.md"
    qa.write_text("QA notes\n", encoding="utf-8")

    manifest = tmp_path / "science.json"
    manifest.write_text(
        (
            '{'
            '"science_version": "2.4.6", '
            '"label": "Unit test bundle", '
            '"prompt_template": "prompt.md", '
            '"bias_file": "bias.json", '
            '"qa_file": "qa.md", '
            '"qa_enabled_by_default": true'
            '}'
        ),
        encoding="utf-8",
    )

    bundle = ffion_science.resolve_ffion_science_bundle(manifest_path=manifest)

    assert bundle.science_version == "2.4.6"
    assert bundle.label == "Unit test bundle"
    assert bundle.prompt_template == prompt
    assert bundle.bias_file == bias
    assert bundle.qa_file == qa
    assert bundle.qa_enabled_by_default is True
    assert len(bundle.prompt_sha256) == 64


def test_get_ffion_science_version_uses_registry_active(tmp_path, monkeypatch):
    registry = tmp_path / "science_registry.json"
    registry.write_text(
        '{"active_science_version": "7.8.9", "versions": {}}',
        encoding="utf-8",
    )
    monkeypatch.delenv("FFION_SCIENCE_VERSION", raising=False)
    monkeypatch.delenv("LLM_SCIENCE_VERSION", raising=False)

    assert ffion_science.get_ffion_science_version(registry_path=registry) == "7.8.9"
