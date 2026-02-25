from pathlib import Path

from scripts.extract_outlook_summary import extract_outlook_summary


def _write_outlook(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "LLM-OUTLOOK-test.md"
    path.write_text(body)
    return path


def test_extract_outlook_summary_parses_block_level_markers(tmp_path):
    path = _write_outlook(
        tmp_path,
        """# Clyfar Ozone Outlook
## Days 1-5
**Expert Summary:**
Steady background signal with little change. Confidence remains high.

## Days 6-10
**Expert Summary:**
Mostly background with a slight tail on one day.

## Days 11-15
**Expert Summary:**
One isolated member shows moderate possibility.

## Full Outlook
Run-to-run signal is consistent and not strengthening.

```
AlertLevel_D1_5: BACKGROUND
Confidence_D1_5: HIGH
AlertLevel_D6_10: BACKGROUND
Confidence_D6_10: MEDIUM
AlertLevel_D11_15: MODERATE
Confidence_D11_15: LOW
```
""",
    )
    summary = extract_outlook_summary(path)
    assert summary is not None
    assert summary["summary_format"] == "block"
    assert summary["alert_level_days_1_5"] == "BACKGROUND"
    assert summary["confidence_days_1_5"] == "HIGH"
    assert summary["alert_level_days_6_10"] == "BACKGROUND"
    assert summary["confidence_days_6_10"] == "MEDIUM"
    assert summary["alert_level_days_11_15"] == "MODERATE"
    assert summary["confidence_days_11_15"] == "LOW"
    # Backward-compatible fallback pair should still be populated.
    assert summary["alert_level"] == "BACKGROUND"
    assert summary["confidence"] == "HIGH"


def test_extract_outlook_summary_parses_legacy_markers(tmp_path):
    path = _write_outlook(
        tmp_path,
        """# Clyfar Ozone Outlook
## Full Outlook
Run-to-run signal is weakening in the extended range.

```
AlertLevel: MODERATE
Confidence: MEDIUM
```
""",
    )
    summary = extract_outlook_summary(path)
    assert summary is not None
    assert summary["summary_format"] == "legacy"
    assert summary["alert_level"] == "MODERATE"
    assert summary["confidence"] == "MEDIUM"


def test_extract_outlook_summary_returns_none_without_markers(tmp_path):
    path = _write_outlook(
        tmp_path,
        """# Clyfar Ozone Outlook
## Full Outlook
Background conditions are likely but no machine-readable markers are present.
""",
    )
    assert extract_outlook_summary(path) is None
