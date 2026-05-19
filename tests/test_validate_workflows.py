"""Tests for the workflow validation helper used by the Codex skill."""

import subprocess
import sys


VALID_WORKFLOW = """
id: valid-demo
enabled: false
trigger: {type: schedule, cron: "0 9 * * *", timezone: UTC}
steps:
  - {id: fetch, type: http_fetch, url: "https://example.com"}
  - {id: summarize, type: ai_summary, prompt: "总结"}
  - {id: notify, type: notify, title: "Demo"}
notify: {channel: ops-default}
""".strip()


def test_validate_workflows_script_accepts_valid_configs(tmp_path):
    (tmp_path / "valid.yaml").write_text(VALID_WORKFLOW, encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "scripts/validate_workflows.py", str(tmp_path)],
        check=False,
        cwd=".",
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0
    assert "valid-demo" in result.stdout


def test_validate_workflows_script_rejects_invalid_configs(tmp_path):
    (tmp_path / "invalid.yaml").write_text("id: broken\nenabled: true\n", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "scripts/validate_workflows.py", str(tmp_path)],
        check=False,
        cwd=".",
        text=True,
        capture_output=True,
    )

    assert result.returncode == 1
    assert "Workflow trigger is required" in result.stderr
