"""Tests for read-only workflow administration routes."""

from pathlib import Path

from fastapi.testclient import TestClient

from ai_approval_workflow.main import create_app


WORKFLOW_YAML = """
id: daily-demo
enabled: true
trigger: {type: schedule, cron: "0 9 * * *", timezone: UTC}
steps:
  - {id: collect, type: demo_summary, subject: Demo}
notify: {channel: ops-default}
""".strip()


def test_admin_page_lists_workflows(test_settings):
    """The admin page should be a simple task inventory, not a task editor."""

    workflows_dir = Path(test_settings.workflows_dir)
    workflows_dir.mkdir(parents=True)
    (workflows_dir / "daily-demo.yaml").write_text(WORKFLOW_YAML, encoding="utf-8")

    app = create_app(test_settings)
    with TestClient(app) as client:
        response = client.get("/admin")

    assert response.status_code == 200
    assert "daily-demo" in response.text
    assert "0 9 * * *" in response.text
    assert "Create" not in response.text


def test_admin_api_lists_enabled_and_disabled_workflows(test_settings):
    """The JSON admin API should show disabled workflows for cleanup visibility."""

    workflows_dir = Path(test_settings.workflows_dir)
    workflows_dir.mkdir(parents=True)
    (workflows_dir / "daily-demo.yaml").write_text(WORKFLOW_YAML, encoding="utf-8")
    (workflows_dir / "disabled.yaml").write_text(
        WORKFLOW_YAML.replace("daily-demo", "disabled-demo").replace("enabled: true", "enabled: false"),
        encoding="utf-8",
    )

    app = create_app(test_settings)
    with TestClient(app) as client:
        response = client.get("/api/admin/workflows")

    assert response.status_code == 200
    payload = response.json()
    assert [item["id"] for item in payload["workflows"]] == ["daily-demo", "disabled-demo"]
    assert payload["workflows"][1]["enabled"] is False


def test_admin_delete_soft_deletes_workflow_and_reloads_scheduler(test_settings):
    """Deleting from admin should archive YAML and remove the scheduled job immediately."""

    settings = test_settings.model_copy(update={"scheduler_enabled": True})
    workflows_dir = Path(settings.workflows_dir)
    workflows_dir.mkdir(parents=True)
    workflow_path = workflows_dir / "daily-demo.yaml"
    workflow_path.write_text(WORKFLOW_YAML, encoding="utf-8")

    app = create_app(settings)
    with TestClient(app) as client:
        runtime = client.app.state.runtime
        assert runtime.scheduler is not None
        assert [job.id for job in runtime.scheduler.get_jobs()] == ["workflow:daily-demo"]

        response = client.delete("/api/admin/workflows/daily-demo")

        assert response.status_code == 200
        assert response.json()["status"] == "deleted"
        assert not workflow_path.exists()
        assert list((workflows_dir / ".deleted").glob("*.yaml"))
        assert runtime.scheduler is not None
        assert runtime.scheduler.get_jobs() == []


def test_admin_delete_returns_404_for_missing_workflow(test_settings):
    """Unknown workflow ids should be explicit 404s."""

    Path(test_settings.workflows_dir).mkdir(parents=True)
    app = create_app(test_settings)
    with TestClient(app) as client:
        response = client.delete("/api/admin/workflows/missing")

    assert response.status_code == 404
