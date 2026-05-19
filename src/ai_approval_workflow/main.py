"""FastAPI entrypoint for ai-approval-workflow."""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from .actions import ActionQueue, CommandRegistry
from .admin import WorkflowAdminError, WorkflowNotFound, list_workflow_summaries, soft_delete_workflow
from .ai import AIClient
from .approvals import ApprovalService, InvalidApprovalDecision, InvalidApprovalToken
from .config import AppSettings, load_workflows
from .notify import NotificationClient
from .scheduler import build_scheduler
from .storage import SQLiteStore
from .workflow import WorkflowEngine


@dataclass
class Runtime:
    """Objects shared by FastAPI routes."""

    settings: AppSettings
    store: SQLiteStore
    approvals: ApprovalService
    notifier: NotificationClient
    ai: AIClient
    engine: WorkflowEngine
    scheduler: AsyncIOScheduler | None = None


class DecisionRequest(BaseModel):
    """JSON body for mobile approval decisions."""

    token: str
    decision: str


def create_runtime(settings: AppSettings) -> Runtime:
    """Create runtime dependencies from settings."""

    store = SQLiteStore(settings.database_path)
    store.init_db()
    approvals = ApprovalService(store, settings.public_base_url)
    notifier = NotificationClient(
        webhook_url=settings.notification_webhook_url,
        bearer_token=settings.notification_bearer_token,
        source=settings.notification_source,
    )
    ai = AIClient(
        base_url=settings.ai_base_url,
        api_key=settings.ai_api_key,
        model=settings.ai_model,
        timeout_seconds=settings.ai_timeout_seconds,
        fallback_enabled=settings.ai_fallback_enabled,
    )
    command_registry = CommandRegistry(settings.actions_config_path)
    action_queue = ActionQueue(settings.action_queue_dir)
    engine = WorkflowEngine(
        store=store,
        approvals=approvals,
        notifier=notifier,
        ai=ai,
        approval_ttl_seconds=settings.approval_default_ttl_seconds,
        snooze_seconds=settings.snooze_seconds,
        command_registry=command_registry,
        action_queue=action_queue,
    )
    scheduler = None
    if settings.scheduler_enabled:
        workflows = load_workflows(settings.workflows_dir, include_disabled=False)
        scheduler = build_scheduler(workflows, run_workflow=engine.run)
    return Runtime(
        settings=settings,
        store=store,
        approvals=approvals,
        notifier=notifier,
        ai=ai,
        engine=engine,
        scheduler=scheduler,
    )


def reload_scheduler(runtime: Runtime) -> None:
    """Reload scheduled jobs after workflow YAML changes."""

    if runtime.scheduler and runtime.scheduler.running:
        runtime.scheduler.shutdown(wait=False)
    runtime.scheduler = None

    if runtime.settings.scheduler_enabled:
        workflows = load_workflows(runtime.settings.workflows_dir, include_disabled=False)
        runtime.scheduler = build_scheduler(workflows, run_workflow=runtime.engine.run)
        runtime.scheduler.start()


def create_app(settings: AppSettings | None = None) -> FastAPI:
    """Create and configure the FastAPI app."""

    resolved_settings = settings or AppSettings()
    runtime = create_runtime(resolved_settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if runtime.scheduler and not runtime.scheduler.running:
            runtime.scheduler.start()
        try:
            yield
        finally:
            if runtime.scheduler and runtime.scheduler.running:
                runtime.scheduler.shutdown(wait=False)
            await runtime.engine.aclose()
            await runtime.notifier.aclose()
            await runtime.ai.aclose()

    app = FastAPI(title="ai-approval-workflow", version="0.1.0", lifespan=lifespan)
    app.state.runtime = runtime
    templates = Jinja2Templates(directory=str(Path(__file__).with_name("templates")))

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok", "app": "ai-approval-workflow"}

    @app.get("/admin", response_class=HTMLResponse)
    async def admin_page(request: Request) -> HTMLResponse:
        workflows = list_workflow_summaries(runtime.settings.workflows_dir, runtime.scheduler)
        return templates.TemplateResponse(request, "admin.html", {"workflows": workflows})

    @app.get("/api/admin/workflows")
    async def admin_list_workflows() -> dict[str, list[dict]]:
        return {"workflows": list_workflow_summaries(runtime.settings.workflows_dir, runtime.scheduler)}

    @app.delete("/api/admin/workflows/{workflow_id}")
    async def admin_delete_workflow(workflow_id: str) -> dict[str, str]:
        try:
            deleted = soft_delete_workflow(runtime.settings.workflows_dir, workflow_id)
        except WorkflowNotFound as exc:
            raise HTTPException(status_code=404, detail="Workflow not found") from exc
        except WorkflowAdminError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        reload_scheduler(runtime)
        return {"status": "deleted", **deleted}

    @app.get("/a/{approval_id}", response_class=HTMLResponse)
    async def approval_page(request: Request, approval_id: str, token: str) -> HTMLResponse:
        try:
            approval = runtime.store.get_approval(approval_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Approval not found") from exc
        return templates.TemplateResponse(
            request,
            "approval.html",
            {
                "approval": approval,
                "token": token,
                "details_json": json.dumps(approval.details, ensure_ascii=False, indent=2),
            },
        )

    @app.get("/api/approvals/{approval_id}")
    async def get_approval(approval_id: str) -> dict:
        try:
            approval = runtime.store.get_approval(approval_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Approval not found") from exc
        return {
            "approval_id": approval.approval_id,
            "title": approval.title,
            "summary": approval.summary,
            "risk": approval.risk,
            "recommendation": approval.recommendation,
            "status": approval.status.value,
            "choices": approval.choices,
        }

    @app.post("/api/approvals/{approval_id}/decision")
    async def decide_approval(approval_id: str, body: DecisionRequest) -> dict:
        try:
            approval = runtime.approvals.decide(approval_id, body.token, body.decision)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Approval not found") from exc
        except InvalidApprovalToken as exc:
            raise HTTPException(status_code=403, detail="Invalid approval token") from exc
        except InvalidApprovalDecision as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        result = await runtime.engine.continue_after_decision(approval)
        return {"approval_id": approval.approval_id, "decision": approval.decision, **result}

    @app.post("/api/workflows/{workflow_id}/run")
    async def run_workflow(workflow_id: str) -> dict:
        workflows = {workflow.id: workflow for workflow in load_workflows(runtime.settings.workflows_dir, include_disabled=True)}
        workflow = workflows.get(workflow_id)
        if workflow is None:
            raise HTTPException(status_code=404, detail="Workflow not found")
        return await runtime.engine.run(workflow)

    return app


app = create_app()
