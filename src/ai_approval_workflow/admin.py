"""Workflow administration helpers for the minimal web console.

The admin surface intentionally stays small: list configured workflow YAML files
and soft-delete a workflow by moving its YAML into a local archive directory.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from .config import load_workflows
from .domain import WorkflowDefinition


class WorkflowNotFound(KeyError):
    """Raised when an admin action targets an unknown workflow id."""


class WorkflowAdminError(RuntimeError):
    """Raised when a workflow file cannot be safely managed."""


def list_workflow_summaries(
    workflows_dir: str | Path,
    scheduler: AsyncIOScheduler | None = None,
) -> list[dict[str, Any]]:
    """Return UI-safe summaries for all enabled and disabled workflows."""

    next_runs = _next_run_map(scheduler)
    summaries: list[dict[str, Any]] = []
    for workflow in load_workflows(workflows_dir, include_disabled=True):
        summaries.append(_workflow_summary(workflow, next_runs.get(workflow.id)))
    return summaries


def soft_delete_workflow(workflows_dir: str | Path, workflow_id: str) -> dict[str, Any]:
    """Archive the YAML file for a workflow and return delete metadata.

    Moving files into ``.deleted`` avoids irreversible mistakes while removing
    the task from normal workflow loading, because only root-level YAML files are
    discovered by the runtime.
    """

    base_dir = Path(workflows_dir).resolve()
    workflow = _find_workflow(base_dir, workflow_id)
    source_path = _safe_source_path(base_dir, workflow)
    deleted_dir = base_dir / ".deleted"
    deleted_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target_path = _unique_archive_path(deleted_dir / f"{timestamp}-{source_path.name}")
    source_path.rename(target_path)

    return {
        "id": workflow.id,
        "source_file": source_path.name,
        "deleted_file": target_path.name,
    }


def _find_workflow(base_dir: Path, workflow_id: str) -> WorkflowDefinition:
    for workflow in load_workflows(base_dir, include_disabled=True):
        if workflow.id == workflow_id:
            return workflow
    raise WorkflowNotFound(workflow_id)


def _safe_source_path(base_dir: Path, workflow: WorkflowDefinition) -> Path:
    if not workflow.source_path:
        raise WorkflowAdminError(f"Workflow {workflow.id} has no source file")

    source_path = Path(workflow.source_path).resolve()
    if source_path.parent != base_dir:
        raise WorkflowAdminError(f"Workflow {workflow.id} is outside the workflows directory")
    if source_path.suffix.lower() not in {".yaml", ".yml"}:
        raise WorkflowAdminError(f"Workflow {workflow.id} is not a YAML file")
    if not source_path.exists():
        raise WorkflowNotFound(workflow.id)
    return source_path


def _unique_archive_path(target_path: Path) -> Path:
    if not target_path.exists():
        return target_path

    stem = target_path.stem
    suffix = target_path.suffix
    for index in range(2, 1000):
        candidate = target_path.with_name(f"{stem}-{index}{suffix}")
        if not candidate.exists():
            return candidate
    raise WorkflowAdminError("Could not allocate a workflow archive filename")


def _workflow_summary(workflow: WorkflowDefinition, next_run_at: str | None) -> dict[str, Any]:
    trigger = workflow.trigger
    return {
        "id": workflow.id,
        "enabled": workflow.enabled,
        "trigger_type": str(trigger.get("type") or ""),
        "cron": str(trigger.get("cron") or ""),
        "timezone": str(trigger.get("timezone") or "UTC"),
        "notify_channel": str(workflow.notify.get("channel") or "ops-default"),
        "step_count": len(workflow.steps),
        "steps": [{"id": step.id, "type": step.type} for step in workflow.steps],
        "source_file": Path(workflow.source_path or "").name,
        "next_run_at": next_run_at,
    }


def _next_run_map(scheduler: AsyncIOScheduler | None) -> dict[str, str | None]:
    if scheduler is None:
        return {}

    next_runs: dict[str, str | None] = {}
    for job in scheduler.get_jobs():
        if not job.id.startswith("workflow:"):
            continue
        workflow_id = job.id.removeprefix("workflow:")
        next_runs[workflow_id] = job.next_run_time.isoformat() if job.next_run_time else None
    return next_runs
