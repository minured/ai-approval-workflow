"""Shared domain models for workflow, approval, and audit state."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class ApprovalStatus(str, Enum):
    """Persisted lifecycle states for approval requests."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    SNOOZED = "snoozed"
    EXPIRED = "expired"


class ApprovalDecision(str, Enum):
    """Decision values accepted from the mobile approval page."""

    APPROVE = "approve"
    REJECT = "reject"
    SNOOZE = "snooze"


class RiskLevel(str, Enum):
    """Small fixed risk taxonomy shown on approval cards."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class RunStatus(str, Enum):
    """Workflow run states persisted in SQLite."""

    CREATED = "created"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    SNOOZED = "snoozed"
    FAILED = "failed"


@dataclass(frozen=True)
class WorkflowStep:
    """One configured workflow step loaded from YAML."""

    id: str
    type: str
    config: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class WorkflowDefinition:
    """Workflow definition loaded from a YAML file."""

    id: str
    enabled: bool
    trigger: dict[str, Any]
    steps: list[WorkflowStep]
    notify: dict[str, Any] = field(default_factory=dict)
    source_path: str | None = None


@dataclass(frozen=True)
class ApprovalRecord:
    """Approval request as read from storage."""

    approval_id: str
    run_id: str
    title: str
    summary: str
    risk: str
    recommendation: str
    status: ApprovalStatus
    token_hash: str
    choices: list[dict[str, str]]
    expires_at: datetime | None
    details: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    decision: str | None = None
    decided_at: datetime | None = None


def utc_now() -> datetime:
    """Return timezone-aware current UTC time."""

    return datetime.now(timezone.utc)
