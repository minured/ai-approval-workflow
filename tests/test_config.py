"""Tests for settings and YAML workflow loading."""

from pathlib import Path

from ai_approval_workflow.config import AppSettings, load_workflow_file, load_workflows


def test_settings_defaults_use_local_safe_values(monkeypatch):
    monkeypatch.delenv("AAW_PUBLIC_BASE_URL", raising=False)
    settings = AppSettings(_env_file=None)
    assert settings.public_base_url == "http://127.0.0.1:8787"
    assert settings.notification_channel == "ops-default"
    assert settings.ai_timeout_seconds == 30
    assert settings.ai_fallback_enabled is True
    assert settings.message_max_chars == 100


def test_settings_load_ai_timeout_and_fallback_flags(monkeypatch):
    """AI timeout and fallback behavior are deployment configuration, not code."""

    monkeypatch.setenv("AAW_AI_TIMEOUT_SECONDS", "90")
    monkeypatch.setenv("AAW_AI_FALLBACK_ENABLED", "false")

    settings = AppSettings(_env_file=None)

    assert settings.ai_timeout_seconds == 90
    assert settings.ai_fallback_enabled is False


def test_settings_load_message_max_chars(monkeypatch):
    """Outbound AI message length is configurable per deployment."""

    monkeypatch.setenv("AAW_MESSAGE_MAX_CHARS", "42")

    settings = AppSettings(_env_file=None)

    assert settings.message_max_chars == 42


def test_load_workflow_file_parses_demo_config(tmp_path: Path):
    workflow_path = tmp_path / "demo.yaml"
    workflow_path.write_text(
        """
id: demo-daily-summary
enabled: true
trigger:
  type: schedule
  cron: "0 9 * * *"
  timezone: Asia/Shanghai
steps:
  - id: collect
    type: demo_summary
  - id: approval
    type: approval
    title: Demo approval
    risk: low
notify:
  channel: ops-default
""".strip(),
        encoding="utf-8",
    )

    workflow = load_workflow_file(workflow_path)

    assert workflow.id == "demo-daily-summary"
    assert workflow.enabled is True
    assert workflow.trigger["cron"] == "0 9 * * *"
    assert workflow.steps[0].type == "demo_summary"
    assert workflow.notify["channel"] == "ops-default"


def test_load_workflows_ignores_disabled_configs(tmp_path: Path):
    (tmp_path / "enabled.yaml").write_text(
        """
id: enabled
enabled: true
trigger: {type: schedule, cron: "*/5 * * * *", timezone: UTC}
steps: [{id: collect, type: demo_summary}]
""".strip(),
        encoding="utf-8",
    )
    (tmp_path / "disabled.yaml").write_text(
        """
id: disabled
enabled: false
trigger: {type: schedule, cron: "*/5 * * * *", timezone: UTC}
steps: [{id: collect, type: demo_summary}]
""".strip(),
        encoding="utf-8",
    )

    workflows = load_workflows(tmp_path, include_disabled=False)

    assert [workflow.id for workflow in workflows] == ["enabled"]
