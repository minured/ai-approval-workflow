"""Workflow execution engine for the MVP runtime."""

from __future__ import annotations

from typing import Any

import httpx

from .actions import ActionQueue, CommandRegistry
from .ai import AIClient
from .approvals import ApprovalService
from .domain import ApprovalRecord, ApprovalStatus, RunStatus, WorkflowDefinition, WorkflowStep
from .notify import NotificationClient
from .storage import SQLiteStore
from .tasks.demo_daily_summary import run_demo_summary


class WorkflowEngine:
    """Run configured workflows and continue after mobile decisions."""

    def __init__(
        self,
        *,
        store: SQLiteStore,
        approvals: ApprovalService,
        notifier: NotificationClient,
        ai: AIClient,
        approval_ttl_seconds: int,
        snooze_seconds: int,
        http_client: httpx.AsyncClient | None = None,
        command_registry: CommandRegistry | None = None,
        action_queue: ActionQueue | None = None,
    ):
        self.store = store
        self.approvals = approvals
        self.notifier = notifier
        self.ai = ai
        self.approval_ttl_seconds = approval_ttl_seconds
        self.snooze_seconds = snooze_seconds
        self.http_client = http_client or httpx.AsyncClient(timeout=30, follow_redirects=True)
        self.command_registry = command_registry
        self.action_queue = action_queue

    async def aclose(self) -> None:
        """Close HTTP resources owned by generic workflow steps."""

        await self.http_client.aclose()

    async def run(self, workflow: WorkflowDefinition) -> dict[str, Any]:
        """Run workflow until completion or pending approval."""

        run_id = self.store.create_run(workflow.id)
        self.store.append_event("run", run_id, "started", {"workflow_id": workflow.id})
        context: dict[str, Any] = {"workflow_id": workflow.id, "run_id": run_id}

        try:
            for step in workflow.steps:
                await self._run_step(step, workflow, context)
                if context.get("approval_id"):
                    self.store.update_run_status(run_id, RunStatus.WAITING_APPROVAL, context)
                    return {"status": "waiting_approval", "run_id": run_id, "approval_id": context["approval_id"]}

            self.store.update_run_status(run_id, RunStatus.COMPLETED, context)
            self.store.append_event("run", run_id, "completed", context)
            return {"status": "completed", "run_id": run_id}
        except Exception as exc:
            self.store.update_run_status(run_id, RunStatus.FAILED, {"error": str(exc), **context})
            self.store.append_event("run", run_id, "failed", {"error": str(exc)})
            raise

    async def continue_after_decision(self, approval: ApprovalRecord) -> dict[str, Any]:
        """Continue a waiting workflow after a mobile approval decision."""

        current_run = self.store.get_run(approval.run_id)
        if current_run["status"] in {RunStatus.COMPLETED.value, RunStatus.SKIPPED.value, RunStatus.SNOOZED.value}:
            return {"status": current_run["status"], "result": current_run["result"]}

        if approval.status == ApprovalStatus.APPROVED:
            action_result = self._execute_allowlisted_action(approval)
            if action_result.get("status") == "queued":
                self.store.update_run_status(approval.run_id, RunStatus.COMPLETED, action_result)
                self.store.append_event("run", approval.run_id, "action_queued", action_result)
                await self.notifier.send(
                    title="AI approval queued",
                    content=f"Approval {approval.approval_id} queued action {action_result.get('action')}.",
                    channel=str(approval.details.get("channel") or "ops-default"),
                    severity="info",
                )
                return {"status": "queued", "result": action_result}

            self.store.update_run_status(approval.run_id, RunStatus.COMPLETED, action_result)
            self.store.append_event("run", approval.run_id, "action_completed", action_result)
            await self.notifier.send(
                title="AI approval completed",
                content=f"Approval {approval.approval_id} executed successfully.",
                channel=str(approval.details.get("channel") or "ops-default"),
                severity="info",
            )
            return {"status": "completed", "result": action_result}

        if approval.status == ApprovalStatus.REJECTED:
            self.store.update_run_status(approval.run_id, RunStatus.SKIPPED, {"approval_id": approval.approval_id})
            await self.notifier.send(
                title="AI approval skipped",
                content=f"Approval {approval.approval_id} was skipped.",
                channel=str(approval.details.get("channel") or "ops-default"),
                severity="info",
            )
            return {"status": "skipped"}

        if approval.status == ApprovalStatus.SNOOZED:
            self.store.update_run_status(
                approval.run_id,
                RunStatus.SNOOZED,
                {"approval_id": approval.approval_id, "snooze_seconds": self.snooze_seconds},
            )
            await self.notifier.send(
                title="AI approval snoozed",
                content=f"Approval {approval.approval_id} was snoozed for {self.snooze_seconds} seconds.",
                channel=str(approval.details.get("channel") or "ops-default"),
                severity="info",
            )
            return {"status": "snoozed"}

        return {"status": approval.status.value}

    async def _run_step(self, step: WorkflowStep, workflow: WorkflowDefinition, context: dict[str, Any]) -> None:
        if step.type == "demo_summary":
            context["task"] = run_demo_summary(step.config)
            return

        if step.type == "command_check":
            if self.command_registry is None:
                raise ValueError("command_check requires a configured command registry")
            command_name = str(step.config.get("name") or "").strip()
            command_result = self.command_registry.run(command_name)
            if command_result.returncode != 0:
                raise ValueError(f"Command {command_name} failed: {command_result.stderr.strip()}")
            context.setdefault("command_checks", {})[step.id] = {
                "name": command_result.name,
                "stdout": command_result.stdout,
                "stderr": command_result.stderr,
            }
            context["task"] = {"summary": command_result.stdout, "risk": "medium"}
            return

        if step.type == "http_fetch":
            fetch_result = await self._run_http_fetch(step)
            context.setdefault("http_fetches", {})[step.id] = fetch_result
            context["http_fetch"] = fetch_result
            context["task"] = {"summary": fetch_result["body"], "risk": "low"}
            return

        if step.type == "ai_summary":
            context["ai_summary"] = await self.ai.summarize(self._build_ai_input(step, context))
            return

        if step.type == "notify":
            channel = str(step.config.get("channel") or workflow.notify.get("channel") or "ops-default")
            content = str(
                step.config.get("content")
                or context.get("ai_summary")
                or context.get("task", {}).get("summary")
                or "Workflow completed."
            )
            context["notification"] = await self.notifier.send(
                title=str(step.config.get("title") or workflow.id),
                content=content,
                channel=channel,
                severity=str(step.config.get("severity") or "info"),
            )
            return

        if step.type == "approval":
            channel = str(workflow.notify.get("channel") or "ops-default")
            summary = str(context.get("ai_summary") or context.get("task", {}).get("summary") or "Approval requested")
            created = self.approvals.create_pending(
                run_id=context["run_id"],
                title=str(step.config.get("title") or "AI approval"),
                summary=summary,
                risk=str(step.config.get("risk") or context.get("task", {}).get("risk") or "low"),
                recommendation=str(step.config.get("recommendation") or "Review this request."),
                details={
                    "workflow_id": workflow.id,
                    "action": self._find_action(workflow),
                    "action_payload": self._find_action_payload(workflow),
                    "channel": channel,
                    "context": context,
                },
                ttl_seconds=self.approval_ttl_seconds,
                choices=step.config.get("choices"),
            )
            context["approval_id"] = created.approval.approval_id
            context["approval_url"] = created.url
            await self.notifier.send(
                title=f"AI approval: {created.approval.title}",
                content=self._render_approval_message(created.approval.title, summary, created.url),
                channel=channel,
                severity="info",
            )
            return

        if step.type == "demo_action":
            context["action"] = "demo_action"
            return

        if step.type == "queued_action":
            context["action"] = str(step.config.get("action") or "")
            return

        raise ValueError(f"Unsupported workflow step type: {step.type}")

    def _find_action(self, workflow: WorkflowDefinition) -> str:
        for step in workflow.steps:
            if step.type == "demo_action":
                return "demo_action"
            if step.type == "queued_action":
                return str(step.config.get("action") or "")
        return "none"

    def _find_action_payload(self, workflow: WorkflowDefinition) -> dict[str, Any]:
        for step in workflow.steps:
            if step.type == "queued_action":
                payload = step.config.get("payload") or {}
                if isinstance(payload, dict):
                    return dict(payload)
        return {}

    def _execute_allowlisted_action(self, approval: ApprovalRecord) -> dict[str, Any]:
        action = approval.details.get("action")
        if action == "demo_action":
            return {"action": "demo_action", "ok": True, "message": "Safe demo action executed."}
        if action and action != "none" and self.action_queue is not None:
            # The root runner performs the final allowlist validation before any
            # privileged command runs. The app only records an approved request.
            action_path = self.action_queue.enqueue(
                action=str(action),
                run_id=approval.run_id,
                approval_id=approval.approval_id,
                workflow_id=str(approval.details.get("workflow_id") or ""),
                payload=dict(approval.details.get("action_payload") or {}),
            )
            return {"action": str(action), "status": "queued", "path": str(action_path)}
        raise ValueError(f"Action is not allowlisted: {action}")

    async def _run_http_fetch(self, step: WorkflowStep) -> dict[str, Any]:
        url = str(step.config.get("url") or "").strip()
        if not url:
            raise ValueError(f"Step {step.id} requires url")

        method = str(step.config.get("method") or "GET").upper()
        if method != "GET":
            raise ValueError(f"Step {step.id} only supports GET in the MVP")

        raw_headers = step.config.get("headers") or {}
        if not isinstance(raw_headers, dict):
            raise ValueError(f"Step {step.id} headers must be a mapping")
        headers = {str(key): str(value) for key, value in raw_headers.items()}

        timeout = float(step.config.get("timeout_seconds") or 20)
        max_bytes = int(step.config.get("max_bytes") or 200_000)
        response = await self.http_client.request(method, url, headers=headers, timeout=timeout)
        response.raise_for_status()
        body = response.text[:max_bytes]
        return {
            "url": url,
            "status_code": response.status_code,
            "content_type": response.headers.get("content-type", ""),
            "body": body,
        }

    def _build_ai_input(self, step: WorkflowStep, context: dict[str, Any]) -> str:
        parts: list[str] = []
        prompt = str(step.config.get("prompt") or "").strip()
        if prompt:
            parts.append(prompt)

        if context.get("http_fetch"):
            fetch = context["http_fetch"]
            parts.append(
                "\n".join(
                    [
                        f"Fetched URL: {fetch.get('url')}",
                        f"HTTP status: {fetch.get('status_code')}",
                        "",
                        str(fetch.get("body") or ""),
                    ]
                )
            )
        else:
            task_summary = str(context.get("task", {}).get("summary") or context.get("task") or "")
            if task_summary:
                parts.append(task_summary)

        return "\n\n".join(parts).strip()

    def _render_approval_message(self, title: str, summary: str, url: str) -> str:
        return "\n".join(
            [
                "[AI 审批] 有一个待处理事项",
                "",
                f"任务：{title}",
                f"摘要：{summary}",
                "",
                "点击处理：",
                url,
            ]
        )
