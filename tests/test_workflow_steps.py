"""Tests for generic workflow steps used by natural-language generated tasks."""

import json

import httpx
import pytest

from ai_approval_workflow.approvals import ApprovalService
from ai_approval_workflow.domain import WorkflowDefinition, WorkflowStep
from ai_approval_workflow.storage import SQLiteStore
from ai_approval_workflow.workflow import WorkflowEngine


class RecordingAI:
    """Fake summarizer that keeps the input text for assertions."""

    def __init__(self):
        self.inputs = []
        self.max_chars = []

    async def summarize(self, text: str, max_chars: int | None = None) -> str:
        self.inputs.append(text)
        self.max_chars.append(max_chars)
        return f"AI summary: {text[:80]}"


class RecordingNotifier:
    """Fake notifier that records outgoing messages."""

    def __init__(self):
        self.messages = []

    async def send(self, *, title: str, content: str, channel: str, severity: str):
        self.messages.append({"title": title, "content": content, "channel": channel, "severity": severity})
        return {"ok": True, "status": "sent"}


def make_engine(tmp_path, *, http_client=None):
    store = SQLiteStore(tmp_path / "app.db")
    store.init_db()
    ai = RecordingAI()
    notifier = RecordingNotifier()
    engine = WorkflowEngine(
        store=store,
        approvals=ApprovalService(store, public_base_url="http://testserver"),
        notifier=notifier,
        ai=ai,
        approval_ttl_seconds=1800,
        snooze_seconds=1800,
        http_client=http_client,
    )
    return engine, ai, notifier


def make_limited_engine(tmp_path, *, message_max_chars: int):
    """Create an engine with a configured outbound AI message limit."""

    store = SQLiteStore(tmp_path / "app.db")
    store.init_db()
    ai = RecordingAI()
    notifier = RecordingNotifier()
    engine = WorkflowEngine(
        store=store,
        approvals=ApprovalService(store, public_base_url="http://testserver"),
        notifier=notifier,
        ai=ai,
        approval_ttl_seconds=1800,
        snooze_seconds=1800,
        message_max_chars=message_max_chars,
    )
    return engine, ai, notifier


@pytest.mark.asyncio
async def test_notify_step_sends_ai_summary_without_approval(tmp_path):
    """A workflow can finish by pushing the latest AI summary to WeChat."""

    engine, ai, notifier = make_engine(tmp_path)
    workflow = WorkflowDefinition(
        id="daily-summary",
        enabled=True,
        trigger={"type": "schedule", "cron": "0 9 * * *", "timezone": "UTC"},
        steps=[
            WorkflowStep(id="collect", type="demo_summary", config={"subject": "Daily"}),
            WorkflowStep(id="summarize", type="ai_summary", config={"prompt": "请简洁总结"}),
            WorkflowStep(id="notify", type="notify", config={"title": "Daily summary"}),
        ],
        notify={"channel": "ops-default"},
    )

    result = await engine.run(workflow)
    await engine.aclose()

    assert result["status"] == "completed"
    assert "请简洁总结" in ai.inputs[0]
    assert notifier.messages == [
        {
            "title": "Daily summary",
            "content": ai.inputs and "AI summary: " + ai.inputs[0][:80],
            "channel": "ops-default",
            "severity": "info",
        }
    ]


@pytest.mark.asyncio
async def test_http_fetch_step_feeds_response_body_to_ai_summary(tmp_path):
    """Natural-language generated tasks can fetch public data before AI summarization."""

    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, text="repo-a 100 stars\nrepo-b 80 stars")

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    engine, ai, notifier = make_engine(tmp_path, http_client=http_client)
    workflow = WorkflowDefinition(
        id="github-trending",
        enabled=True,
        trigger={"type": "schedule", "cron": "0 9 * * *", "timezone": "UTC"},
        steps=[
            WorkflowStep(id="fetch", type="http_fetch", config={"url": "https://example.com/trending"}),
            WorkflowStep(id="summarize", type="ai_summary", config={"prompt": "总结 GitHub Trending"}),
            WorkflowStep(id="notify", type="notify", config={"title": "GitHub Trending"}),
        ],
        notify={"channel": "ops-default"},
    )

    result = await engine.run(workflow)
    await engine.aclose()

    assert result["status"] == "completed"
    assert str(requests[0].url) == "https://example.com/trending"
    assert "repo-a 100 stars" in ai.inputs[0]
    assert notifier.messages[0]["title"] == "GitHub Trending"


@pytest.mark.asyncio
async def test_ai_summary_step_passes_message_limit_to_ai_client(tmp_path):
    """Workflow summaries should generate within the configured notification budget."""

    engine, ai, _notifier = make_limited_engine(tmp_path, message_max_chars=25)
    workflow = WorkflowDefinition(
        id="limited-summary",
        enabled=True,
        trigger={"type": "schedule", "cron": "0 9 * * *", "timezone": "UTC"},
        steps=[
            WorkflowStep(id="collect", type="demo_summary", config={"subject": "Daily"}),
            WorkflowStep(id="summarize", type="ai_summary", config={"prompt": "请简洁总结"}),
            WorkflowStep(id="notify", type="notify", config={"title": "Daily summary"}),
        ],
        notify={"channel": "ops-default"},
    )

    result = await engine.run(workflow)
    await engine.aclose()

    assert result["status"] == "completed"
    assert ai.max_chars == [25]

from ai_approval_workflow.actions import ActionQueue, CommandResult


class FakeCommandRegistry:
    """Fake command registry for command_check workflow tests."""

    def __init__(self):
        self.names = []

    def run(self, name: str) -> CommandResult:
        self.names.append(name)
        return CommandResult(name=name, returncode=0, stdout="current service v1.0.0 latest v1.1.0", stderr="")


def make_engine_with_actions(tmp_path):
    store = SQLiteStore(tmp_path / "app.db")
    store.init_db()
    ai = RecordingAI()
    notifier = RecordingNotifier()
    command_registry = FakeCommandRegistry()
    action_queue = ActionQueue(tmp_path / "actions")
    engine = WorkflowEngine(
        store=store,
        approvals=ApprovalService(store, public_base_url="http://testserver"),
        notifier=notifier,
        ai=ai,
        approval_ttl_seconds=1800,
        snooze_seconds=1800,
        command_registry=command_registry,
        action_queue=action_queue,
    )
    return engine, ai, notifier, command_registry, action_queue


@pytest.mark.asyncio
async def test_command_check_feeds_output_to_approval_summary(tmp_path):
    """A service watcher can run a named read-only check before asking for approval."""

    engine, ai, notifier, command_registry, _queue = make_engine_with_actions(tmp_path)
    workflow = WorkflowDefinition(
        id="service-upgrade-watch",
        enabled=True,
        trigger={"type": "schedule", "cron": "0 9 * * *", "timezone": "Asia/Shanghai"},
        steps=[
            WorkflowStep(id="check", type="command_check", config={"name": "service_version_check"}),
            WorkflowStep(id="summarize", type="ai_summary", config={"prompt": "判断是否值得升级"}),
            WorkflowStep(
                id="approval",
                type="approval",
                config={
                    "title": "Service upgrade approval",
                    "risk": "medium",
                    "choices": [
                        {"value": "approve", "label": "升级", "style": "approve"},
                        {"value": "reject", "label": "不升级", "style": "reject"},
                    ],
                },
            ),
            WorkflowStep(id="upgrade", type="queued_action", config={"action": "service_bundle_upgrade"}),
        ],
        notify={"channel": "ops-default"},
    )

    result = await engine.run(workflow)
    await engine.aclose()
    approval = engine.store.get_approval(result["approval_id"])

    assert result["status"] == "waiting_approval"
    assert command_registry.names == ["service_version_check"]
    assert "current service v1.0.0" in ai.inputs[0]
    assert approval.choices[0]["label"] == "升级"
    assert approval.details["action"] == "service_bundle_upgrade"


@pytest.mark.asyncio
async def test_approved_queued_action_writes_action_request(tmp_path):
    """Approving the service watcher should enqueue the fixed bundle upgrade action."""

    engine, _ai, _notifier, _registry, action_queue = make_engine_with_actions(tmp_path)
    run_id = engine.store.create_run("service-upgrade-watch")
    created = engine.approvals.create_pending(
        run_id=run_id,
        title="Service upgrade approval",
        summary="Upgrade available",
        risk="medium",
        recommendation="升级",
        details={"workflow_id": "service-upgrade-watch", "action": "service_bundle_upgrade", "channel": "ops-default"},
        ttl_seconds=1800,
        choices=[{"value": "approve", "label": "升级", "style": "approve"}],
    )

    approval = engine.approvals.decide(created.approval.approval_id, created.token, "approve")
    result = await engine.continue_after_decision(approval)
    await engine.aclose()

    pending = list((action_queue.queue_dir / "pending").glob("*.json"))
    assert result["status"] == "queued"
    assert len(pending) == 1
    queued_payload = json.loads(pending[0].read_text(encoding="utf-8"))
    assert queued_payload["action"] == "service_bundle_upgrade"
    assert queued_payload["run_id"] == run_id
    assert queued_payload["approval_id"] == created.approval.approval_id
    assert queued_payload["workflow_id"] == "service-upgrade-watch"
