from pathlib import Path

from scripts.validate_llm_outlook import validate_outlook


def _write_outlook(path: Path, body: str) -> Path:
    path.write_text(body, encoding="utf-8")
    return path


def _valid_outlook_body(data_path: Path) -> str:
    return f"""---
> - **EXPERIMENTAL AI-GENERATED FORECAST**
> - Forecaster: **Ffion v1.1.1** (ffion@jrl.ac), using **Clyfar v1.0.2** and GEFS ensemble inputs.
---

# Clyfar Ozone Outlook
## Data Logger
- `{data_path}`

```text
AlertLevel_D1_5: BACKGROUND
Confidence_D1_5: HIGH
AlertLevel_D6_10: BACKGROUND
Confidence_D6_10: MEDIUM
AlertLevel_D11_15: MODERATE
Confidence_D11_15: LOW
```
"""


def test_validate_outlook_passes_for_valid_content(tmp_path):
    referenced = tmp_path / "source.json"
    referenced.write_text("{}", encoding="utf-8")
    outlook = _write_outlook(
        tmp_path / "LLM-OUTLOOK-test.md",
        _valid_outlook_body(referenced),
    )

    ok, errors = validate_outlook(outlook, expected_clyfar="1.0.2", expected_ffion="1.1.1")
    assert ok
    assert errors == []


def test_validate_outlook_fails_on_version_mismatch(tmp_path):
    referenced = tmp_path / "source.json"
    referenced.write_text("{}", encoding="utf-8")
    outlook = _write_outlook(
        tmp_path / "LLM-OUTLOOK-test.md",
        _valid_outlook_body(referenced),
    )

    ok, errors = validate_outlook(outlook, expected_clyfar="1.0.3", expected_ffion="1.1.1")
    assert not ok
    assert any("Clyfar version mismatch" in err for err in errors)


def test_validate_outlook_fails_without_required_markers(tmp_path):
    referenced = tmp_path / "source.json"
    referenced.write_text("{}", encoding="utf-8")
    body = _valid_outlook_body(referenced).replace("AlertLevel_D11_15: MODERATE\n", "")
    outlook = _write_outlook(tmp_path / "LLM-OUTLOOK-test.md", body)

    ok, errors = validate_outlook(outlook, expected_clyfar="1.0.2", expected_ffion="1.1.1")
    assert not ok
    assert any("Missing marker: AlertLevel_D11_15" in err for err in errors)


def test_validate_outlook_fails_on_missing_data_logger_path(tmp_path):
    missing = tmp_path / "missing.json"
    outlook = _write_outlook(
        tmp_path / "LLM-OUTLOOK-test.md",
        _valid_outlook_body(missing),
    )

    ok, errors = validate_outlook(outlook, expected_clyfar="1.0.2", expected_ffion="1.1.1")
    assert not ok
    assert any("Data Logger path does not exist" in err for err in errors)


def test_validate_outlook_accepts_case_relative_data_logger_paths(tmp_path):
    case_root = tmp_path / "CASE_20260101_0000Z"
    llm_dir = case_root / "llm_text"
    llm_dir.mkdir(parents=True)

    rel_file = case_root / "probs" / "forecast_exceedance_probabilities_20260101_0000Z.json"
    rel_file.parent.mkdir(parents=True)
    rel_file.write_text("{}", encoding="utf-8")

    body = _valid_outlook_body(Path("probs/forecast_exceedance_probabilities_20260101_0000Z.json"))
    outlook = _write_outlook(llm_dir / "LLM-OUTLOOK-20260101_0000Z.md", body)

    ok, errors = validate_outlook(outlook, expected_clyfar="1.0.2", expected_ffion="1.1.1")
    assert ok
    assert errors == []
