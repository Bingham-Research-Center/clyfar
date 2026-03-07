from utils import ffion_bundle


def test_resolve_ffion_bundle_from_manifest(tmp_path):
    prompt = tmp_path / "prompt.md"
    prompt.write_text("Prompt body\n", encoding="utf-8")

    bias = tmp_path / "bias.json"
    bias.write_text("[]\n", encoding="utf-8")

    qa = tmp_path / "qa.md"
    qa.write_text("QA notes\n", encoding="utf-8")

    manifest = tmp_path / "ffion.json"
    manifest.write_text(
        (
            "{"
            '"ffion_version": "2.4.6", '
            '"label": "Unit test bundle", '
            '"prompt_template": "prompt.md", '
            '"bias_file": "bias.json", '
            '"qa_file": "qa.md", '
            '"qa_enabled_by_default": true'
            "}"
        ),
        encoding="utf-8",
    )

    bundle = ffion_bundle.resolve_ffion_bundle(manifest_path=manifest)

    assert bundle.ffion_version == "2.4.6"
    assert bundle.label == "Unit test bundle"
    assert bundle.prompt_template == prompt
    assert bundle.bias_file == bias
    assert bundle.qa_file == qa
    assert bundle.qa_enabled_by_default is True
    assert len(bundle.prompt_sha256) == 64


def test_resolve_ffion_bundle_uses_registry_version(tmp_path):
    prompt = tmp_path / "prompt.md"
    prompt.write_text("Prompt body\n", encoding="utf-8")

    manifest = tmp_path / "ffion_v7.8.9.json"
    manifest.write_text(
        (
            "{"
            '"ffion_version": "7.8.9", '
            '"prompt_template": "prompt.md"'
            "}"
        ),
        encoding="utf-8",
    )

    registry = tmp_path / "ffion_registry.json"
    registry.write_text(
        '{"versions": {"7.8.9": {"manifest": "ffion_v7.8.9.json"}}}',
        encoding="utf-8",
    )

    bundle = ffion_bundle.resolve_ffion_bundle(ffion_version="7.8.9", registry_path=registry)
    assert bundle.ffion_version == "7.8.9"


def test_resolve_ffion_bundle_accepts_repo_relative_manifest_paths(tmp_path, monkeypatch):
    repo_root = tmp_path / "repo"
    manifest_dir = repo_root / "templates" / "llm" / "ffion"
    manifest_dir.mkdir(parents=True)

    prompt = manifest_dir / "prompt.md"
    prompt.write_text("Prompt body\n", encoding="utf-8")

    manifest = manifest_dir / "ffion_v7.8.9.json"
    manifest.write_text(
        (
            "{"
            '"ffion_version": "7.8.9", '
            '"prompt_template": "prompt.md"'
            "}"
        ),
        encoding="utf-8",
    )

    registry = tmp_path / "ffion_registry.json"
    registry.write_text(
        '{"versions": {"7.8.9": {"manifest": "templates/llm/ffion/ffion_v7.8.9.json"}}}',
        encoding="utf-8",
    )

    monkeypatch.setattr(ffion_bundle, "_REPO_ROOT", repo_root)

    bundle = ffion_bundle.resolve_ffion_bundle(ffion_version="7.8.9", registry_path=registry)
    assert bundle.manifest_path == manifest
    assert bundle.prompt_template == prompt
