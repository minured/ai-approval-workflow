"""Tests for health, approval page, and decision API."""


def test_healthz(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


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
