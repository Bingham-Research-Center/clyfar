import sys
from pathlib import Path

from scripts import demo_llm_forecast_template as template_script


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

    prompt_template = repo_root / "templates" / "llm" / "prompt_body.md"
    prompt_template.parent.mkdir(parents=True)
    prompt_template.write_text(
        "Forecaster: Ffion v{{FFION_VERSION}} and Clyfar v{{CLYFAR_VERSION}} ({{INIT}} {{CASE_ROOT}} {{RECENT_CASE_COUNT}})",
        encoding="utf-8",
    )

    bias_file = repo_root / "templates" / "llm" / "short_term_biases.json"
    bias_file.write_text("[]", encoding="utf-8")

    monkeypatch.setattr(template_script, "REPO_ROOT", repo_root)
    monkeypatch.setattr(template_script, "DEFAULT_PROMPT_TEMPLATE", prompt_template)
    monkeypatch.setattr(template_script, "DEFAULT_BIAS_FILE", bias_file)
    monkeypatch.setattr(template_script, "CLYFAR_VERSION", "1.0.3")
    monkeypatch.setattr(template_script, "FFION_VERSION", "1.1.2")

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "demo_llm_forecast_template.py",
            "2026010100",
            "--prompt-template",
            str(prompt_template),
            "--bias-file",
            str(bias_file),
        ],
    )

    template_script.main()

    out_path = current_case / "llm_text" / "forecast_prompt_20260101_0000Z.md"
    output = out_path.read_text(encoding="utf-8")

    assert "- Clyfar version: `1.0.3`" in output
    assert "- Ffion version: `1.1.2`" in output
    assert "## Local File Index" in output
    assert str(clustering_path) in output
    assert str(previous_case / f"LLM-OUTLOOK-{previous_init}.md") in output
    assert "Forecaster: Ffion v1.1.2 and Clyfar v1.0.3" in output
