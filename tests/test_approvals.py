"""Tests for approval creation and decision validation."""

import pytest

from ai_approval_workflow.approvals import ApprovalService, InvalidApprovalToken
from ai_approval_workflow.domain import ApprovalStatus
from ai_approval_workflow.storage import SQLiteStore


def test_create_approval_returns_link_safe_token(tmp_path):
    store = SQLiteStore(tmp_path / "app.db")
    store.init_db()
    run_id = store.create_run("demo")
    service = ApprovalService(store, public_base_url="https://approval.example")

    created = service.create_pending(
        run_id=run_id,
        title="Approve demo",
        summary="Summary",
        risk="low",
        recommendation="Approve",
        details={"action": "demo_action"},
        ttl_seconds=1800,
    )

    assert created.approval.approval_id.startswith("ACT-")
    assert created.token not in created.approval.token_hash
    assert created.url.startswith("https://approval.example/a/")
    assert "token=" in created.url


def test_decide_rejects_wrong_token(tmp_path):
    store = SQLiteStore(tmp_path / "app.db")
    store.init_db()
    run_id = store.create_run("demo")
    service = ApprovalService(store, public_base_url="https://approval.example")
    created = service.create_pending(
        run_id=run_id,
        title="Approve demo",
        summary="Summary",
        risk="low",
        recommendation="Approve",
        details={},
        ttl_seconds=1800,
    )

    with pytest.raises(InvalidApprovalToken):
        service.decide(created.approval.approval_id, "bad-token", "approve")


def test_decide_approve_updates_status(tmp_path):
    store = SQLiteStore(tmp_path / "app.db")
    store.init_db()
    run_id = store.create_run("demo")
    service = ApprovalService(store, public_base_url="https://approval.example")
    created = service.create_pending(
        run_id=run_id,
        title="Approve demo",
        summary="Summary",
        risk="low",
        recommendation="Approve",
        details={},
        ttl_seconds=1800,
    )

    decided = service.decide(created.approval.approval_id, created.token, "approve")

    assert decided.status == ApprovalStatus.APPROVED
    assert decided.decision == "approve"


def test_create_pending_accepts_custom_choice_labels(tmp_path):
    store = SQLiteStore(tmp_path / "app.db")
    store.init_db()
    run_id = store.create_run("service")
    service = ApprovalService(store, public_base_url="https://approval.example")

    created = service.create_pending(
        run_id=run_id,
        title="Service upgrade",
        summary="Upgrade available",
        risk="medium",
        recommendation="Review and approve",
        details={},
        ttl_seconds=1800,
        choices=[
            {"value": "approve", "label": "升级", "style": "approve"},
            {"value": "reject", "label": "不升级", "style": "reject"},
        ],
    )

    assert created.approval.choices == [
        {"value": "approve", "label": "升级", "style": "approve"},
        {"value": "reject", "label": "不升级", "style": "reject"},
    ]
    decided = service.decide(created.approval.approval_id, created.token, "approve")
    assert decided.status == ApprovalStatus.APPROVED
