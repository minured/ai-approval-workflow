"""Tests for demo workflow execution and approval continuation."""

from pathlib import Path

import pytest

from ai_approval_workflow.ai import AIClient
from ai_approval_workflow.approvals import ApprovalService
from ai_approval_workflow.config import load_workflow_file
from ai_approval_workflow.domain import ApprovalStatus, RunStatus
from ai_approval_workflow.notify import NotificationClient
from ai_approval_workflow.storage import SQLiteStore
from ai_approval_workflow.workflow import WorkflowEngine


class CapturingNotifier:
    """Test notifier that records outbound notification payloads."""

    def __init__(self):
        self.messages = []

    async def send(self, *, title: str, content: str, channel: str, severity: str = "info"):
        self.messages.append({"title": title, "content": content, "channel": channel, "severity": severity})
        return {"ok": True, "status": "captured"}

    async def aclose(self):
        return None


@pytest.mark.asyncio
async def test_run_demo_workflow_creates_approval(tmp_path: Path):
    workflow_path = tmp_path / "workflow.yaml"
    workflow_path.write_text(
        """
id: demo
enabled: true
trigger: {type: schedule, cron: "0 9 * * *", timezone: UTC}
steps:
  - {id: collect, type: demo_summary, subject: Demo}
  - {id: summarize, type: ai_summary, optional: true}
  - {id: approval, type: approval, title: Demo approval, risk: low, recommendation: Approve}
  - {id: action, type: demo_action, requires_approval: true}
notify: {channel: ops-default}
""".strip(),
        encoding="utf-8",
    )
    workflow = load_workflow_file(workflow_path)
    store = SQLiteStore(tmp_path / "app.db")
    store.init_db()
    notifier = CapturingNotifier()
    engine = WorkflowEngine(
        store=store,
        approvals=ApprovalService(store, "https://approval.example"),
        notifier=notifier,
        ai=AIClient(base_url="", api_key="", model="test"),
        approval_ttl_seconds=1800,
        snooze_seconds=1800,
    )

    result = await engine.run(workflow)

    approval = store.get_approval(result["approval_id"])
    run = store.get_run(result["run_id"])
    await engine.notifier.aclose()
    await engine.ai.aclose()
    assert approval.status == ApprovalStatus.PENDING
    assert run["status"] == RunStatus.WAITING_APPROVAL.value
    assert notifier.messages
    assert "https://approval.example/a/" in notifier.messages[0]["content"]


@pytest.mark.asyncio
async def test_handle_approved_decision_completes_demo_action(tmp_path: Path):
    store = SQLiteStore(tmp_path / "app.db")
    store.init_db()
    engine = WorkflowEngine(
        store=store,
        approvals=ApprovalService(store, "https://approval.example"),
        notifier=NotificationClient(webhook_url="", bearer_token="", source="test"),
        ai=AIClient(base_url="", api_key="", model="test"),
        approval_ttl_seconds=1800,
        snooze_seconds=1800,
    )
    run_id = store.create_run("demo")
    created = engine.approvals.create_pending(
        run_id=run_id,
        title="Demo approval",
        summary="Summary",
        risk="low",
        recommendation="Approve",
        details={"workflow_id": "demo", "action": "demo_action"},
        ttl_seconds=1800,
    )

    approval = engine.approvals.decide(created.approval.approval_id, created.token, "approve")
    result = await engine.continue_after_decision(approval)

    run = store.get_run(run_id)
    await engine.notifier.aclose()
    await engine.ai.aclose()
    assert result["status"] == "completed"
    assert run["status"] == RunStatus.COMPLETED.value
