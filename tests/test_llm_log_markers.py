from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_llm_generate_exposes_machine_parseable_status_markers():
    script = (REPO_ROOT / "LLM-GENERATE.sh").read_text(encoding="utf-8")

    assert "STATUS_LLM_GENERATION=" in script
    assert "ALERT_LLM_PROMPT_RENDER_FAILED" in script
    assert "STATUS_LLM_UPLOAD_PDF=" in script
    assert "STATUS_LLM_UPLOAD_MARKDOWN=" in script


def test_submit_script_exposes_stage_and_push_markers():
    script = (REPO_ROOT / "scripts" / "submit_clyfar.sh").read_text(encoding="utf-8")

    assert "STATUS_FORECAST_EXPORT=" in script
    assert "STATUS_LLM_STAGE=" in script
    assert "STATUS_SUBMIT_LLM_PDF_PUSH=" in script
    assert "ALERT_LLM_STAGE_FAILED" in script
