"""APScheduler integration for scheduled workflows."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from .domain import WorkflowDefinition


def build_scheduler(
    workflows: list[WorkflowDefinition],
    run_workflow: Callable[[WorkflowDefinition], Coroutine[Any, Any, Any] | Any],
) -> AsyncIOScheduler:
    """Build an AsyncIOScheduler and register enabled schedule triggers."""

    scheduler = AsyncIOScheduler(timezone="UTC")
    for workflow in workflows:
        trigger_config = workflow.trigger
        if trigger_config.get("type") != "schedule":
            continue
        cron = str(trigger_config.get("cron") or "").strip()
        if not cron:
            raise ValueError(f"Workflow {workflow.id} schedule trigger requires cron")
        timezone = str(trigger_config.get("timezone") or "UTC")
        trigger = CronTrigger.from_crontab(cron, timezone=timezone)
        scheduler.add_job(
            _run_job,
            trigger=trigger,
            id=f"workflow:{workflow.id}",
            replace_existing=True,
            args=[run_workflow, workflow],
        )
    return scheduler


async def _run_job(run_workflow: Callable[[WorkflowDefinition], Any], workflow: WorkflowDefinition) -> None:
    """Execute a scheduled workflow regardless of sync or async callable shape."""

    result = run_workflow(workflow)
    if asyncio.iscoroutine(result):
        await result
