"""Tests for SQLite persistence."""

from datetime import timedelta

from ai_approval_workflow.domain import ApprovalStatus, RunStatus, utc_now
from ai_approval_workflow.storage import SQLiteStore


def test_init_db_creates_run_and_audit(tmp_path):
    store = SQLiteStore(tmp_path / "app.db")
    store.init_db()

    run_id = store.create_run("demo")
    store.update_run_status(run_id, RunStatus.COMPLETED, {"ok": True})
    store.append_event("run", run_id, "completed", {"ok": True})

    run = store.get_run(run_id)
    events = store.list_events("run", run_id)

    assert run["workflow_id"] == "demo"
    assert run["status"] == "completed"
    assert run["result"]["ok"] is True
    assert events[0]["event_type"] == "completed"


def test_create_and_decide_approval(tmp_path):
    store = SQLiteStore(tmp_path / "app.db")
    store.init_db()
    run_id = store.create_run("demo")
    approval_id = store.create_approval(
        approval_id="ACT-1",
        run_id=run_id,
        title="Test approval",
        summary="Summary",
        risk="low",
        recommendation="Approve",
        token_hash="hash",
        choices=["approve", "reject", "snooze"],
        expires_at=utc_now() + timedelta(minutes=30),
        details={"action": "demo_action"},
    )

    store.decide_approval(approval_id, ApprovalStatus.APPROVED, "approve")
    approval = store.get_approval(approval_id)

    assert approval.approval_id == "ACT-1"
    assert approval.status == ApprovalStatus.APPROVED
    assert approval.decision == "approve"
    assert approval.details["action"] == "demo_action"
