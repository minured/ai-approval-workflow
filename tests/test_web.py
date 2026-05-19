"""Tests for health, approval page, and decision API."""

from ai_approval_workflow.config import AppSettings
from ai_approval_workflow.main import create_app


def test_healthz(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_create_app_passes_ai_runtime_settings(tmp_path):
    """Runtime AI client should receive deployment-managed timeout and fallback flags."""

    settings = AppSettings(
        _env_file=None,
        database_path=str(tmp_path / "app.db"),
        workflows_dir=str(tmp_path / "workflows"),
        ai_timeout_seconds=75,
        ai_fallback_enabled=False,
    )

    app = create_app(settings)

    assert app.state.runtime.ai.timeout_seconds == 75
    assert app.state.runtime.ai.fallback_enabled is False


def test_approval_page_and_decision_flow(client):
    app_state = client.app.state.runtime
    run_id = app_state.store.create_run("demo")
    created = app_state.approvals.create_pending(
        run_id=run_id,
        title="Demo approval",
        summary="Summary",
        risk="low",
        recommendation="Approve",
        details={"action": "demo_action", "channel": "ops-default"},
        ttl_seconds=1800,
    )

    page = client.get(f"/a/{created.approval.approval_id}", params={"token": created.token})
    assert page.status_code == 200
    assert "Demo approval" in page.text
    assert "Execute" in page.text

    decision = client.post(
        f"/api/approvals/{created.approval.approval_id}/decision",
        json={"token": created.token, "decision": "approve"},
    )
    assert decision.status_code == 200
    assert decision.json()["status"] == "completed"
