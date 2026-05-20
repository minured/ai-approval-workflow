"""Application settings and workflow YAML loading."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from .domain import WorkflowDefinition, WorkflowStep


class AppSettings(BaseSettings):
    """Environment-driven application settings.

    All values use the AAW_ prefix to avoid collisions on shared servers.
    """

    app_env: str = "development"
    bind_host: str = "127.0.0.1"
    bind_port: int = 8787
    public_base_url: str = "http://127.0.0.1:8787"
    database_path: str = "./data/ai-approval-workflow.db"
    workflows_dir: str = "./examples"
    scheduler_enabled: bool = False
    ai_base_url: str = ""
    ai_api_key: str = ""
    ai_model: str = "gpt-4.1-mini"
    ai_timeout_seconds: float = Field(default=30, ge=1)
    ai_fallback_enabled: bool = True
    message_max_chars: int = Field(default=300, ge=0)
    notification_webhook_url: str = ""
    notification_bearer_token: str = ""
    notification_channel: str = "ops-default"
    notification_source: str = "ai-approval-workflow"
    actions_config_path: str = ""
    action_queue_dir: str = "./data/actions"
    approval_default_ttl_seconds: int = Field(default=1800, ge=60)
    snooze_seconds: int = Field(default=1800, ge=60)

    model_config = SettingsConfigDict(
        env_prefix="AAW_",
        env_file=".env",
        extra="ignore",
    )


def load_workflow_file(path: str | Path) -> WorkflowDefinition:
    """Load one workflow definition from YAML."""

    workflow_path = Path(path)
    raw = yaml.safe_load(workflow_path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"Workflow file must contain a YAML object: {workflow_path}")

    workflow_id = str(raw.get("id") or "").strip()
    if not workflow_id:
        raise ValueError(f"Workflow id is required: {workflow_path}")

    trigger = raw.get("trigger") or {}
    if not isinstance(trigger, dict) or not trigger.get("type"):
        raise ValueError(f"Workflow trigger is required: {workflow_path}")

    raw_steps = raw.get("steps") or []
    if not isinstance(raw_steps, list) or not raw_steps:
        raise ValueError(f"Workflow steps must be a non-empty list: {workflow_path}")

    steps: list[WorkflowStep] = []
    for index, raw_step in enumerate(raw_steps):
        if not isinstance(raw_step, dict):
            raise ValueError(f"Step {index} must be an object in {workflow_path}")
        step_id = str(raw_step.get("id") or f"step-{index + 1}").strip()
        step_type = str(raw_step.get("type") or "").strip()
        if not step_type:
            raise ValueError(f"Step {step_id} is missing type in {workflow_path}")
        config = {key: value for key, value in raw_step.items() if key not in {"id", "type"}}
        steps.append(WorkflowStep(id=step_id, type=step_type, config=config))

    notify = raw.get("notify") or {}
    if not isinstance(notify, dict):
        raise ValueError(f"Workflow notify must be an object: {workflow_path}")

    return WorkflowDefinition(
        id=workflow_id,
        enabled=bool(raw.get("enabled", True)),
        trigger=dict(trigger),
        steps=steps,
        notify=dict(notify),
        source_path=str(workflow_path),
    )


def load_workflows(directory: str | Path, include_disabled: bool = False) -> list[WorkflowDefinition]:
    """Load all YAML workflows from a directory in stable filename order."""

    workflows_dir = Path(directory)
    if not workflows_dir.exists():
        return []

    workflows: list[WorkflowDefinition] = []
    for path in sorted([*workflows_dir.glob("*.yaml"), *workflows_dir.glob("*.yml")]):
        workflow = load_workflow_file(path)
        if workflow.enabled or include_disabled:
            workflows.append(workflow)
    return workflows
