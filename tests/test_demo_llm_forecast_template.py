import sys
import json
from pathlib import Path

from scripts import demo_llm_forecast_template as template_script
from utils.versioning import get_clyfar_version


def test_prompt_includes_versions_and_local_file_index(tmp_path, monkeypatch):
    repo_root = tmp_path
    data_root = repo_root / "data" / "json_tests"

    current_init = "20260101_0000Z"
    current_case = data_root / f"CASE_{current_init}"
    (current_case / "llm_text").mkdir(parents=True)
    for sub in ("percentiles", "probs", "possibilities", "weather"):
        d = current_case / sub
        d.mkdir(parents=True)
        (d / f"{sub}_sample.json").write_text("{}", encoding="utf-8")

    clustering_path = current_case / f"forecast_clustering_summary_{current_init}.json"
    clustering_path.write_text('{"clusters": []}', encoding="utf-8")

    previous_init = "20251231_1800Z"
    previous_case = data_root / f"CASE_{previous_init}" / "llm_text"
    previous_case.mkdir(parents=True)
    (previous_case / f"LLM-OUTLOOK-{previous_init}.md").write_text(
        """# Clyfar Ozone Outlook
```text
AlertLevel_D1_5: BACKGROUND
Confidence_D1_5: HIGH
AlertLevel_D6_10: BACKGROUND
Confidence_D6_10: MEDIUM
AlertLevel_D11_15: MODERATE
Confidence_D11_15: LOW
```
""",
        encoding="utf-8",
    )

    prompt_template = repo_root / "templates" / "llm" / "versions" / "ffion_prompt_v9.9.0.md"
    prompt_template.parent.mkdir(parents=True)
    prompt_template.write_text(
        (
            "Forecaster: Ffion v{{FFION_VERSION}} and Clyfar v{{CLYFAR_VERSION}} "
            "({{INIT}} {{CASE_ROOT}} {{RECENT_CASE_COUNT}})"
        ),
        encoding="utf-8",
    )

    bias_file = repo_root / "templates" / "llm" / "biases" / "ffion_biases_v9.9.0.json"
    bias_file.parent.mkdir(parents=True, exist_ok=True)
    bias_file.write_text("[]", encoding="utf-8")

    qa_file = repo_root / "templates" / "llm" / "qa" / "ffion_qa_v9.9.0.md"
    qa_file.parent.mkdir(parents=True, exist_ok=True)
    qa_file.write_text("Test QA notes.\n", encoding="utf-8")

    ffion_manifest = repo_root / "templates" / "llm" / "ffion" / "ffion_v9.9.0.json"
    ffion_manifest.parent.mkdir(parents=True, exist_ok=True)
    ffion_manifest.write_text(
        json.dumps(
            {
                "ffion_version": "9.9.0",
                "label": "Test Ffion bundle",
                "prompt_template": "../versions/ffion_prompt_v9.9.0.md",
                "bias_file": "../biases/ffion_biases_v9.9.0.json",
                "qa_file": "../qa/ffion_qa_v9.9.0.md",
                "qa_enabled_by_default": False,
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(template_script, "REPO_ROOT", repo_root)

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "demo_llm_forecast_template.py",
            "2026010100",
            "--ffion-manifest",
            str(ffion_manifest),
        ],
    )

    template_script.main()

    out_path = current_case / "llm_text" / "forecast_prompt_20260101_0000Z.md"
    output = out_path.read_text(encoding="utf-8")

    assert f"- Clyfar version: `{get_clyfar_version()}`" in output
    assert "- Ffion version: `9.9.0`" in output
    assert "- Ffion manifest: " in output
    assert "## Local File Index" in output
    assert "## Ffion Bundle" in output
    assert str(ffion_manifest) in output
    assert str(clustering_path) in output
    assert str(previous_case / f"LLM-OUTLOOK-{previous_init}.md") in output
    assert f"Forecaster: Ffion v9.9.0 and Clyfar v{get_clyfar_version()}" in output
