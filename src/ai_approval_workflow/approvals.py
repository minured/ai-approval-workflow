"""Approval request creation, secure links, and decision validation."""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import timedelta
from urllib.parse import urlencode

from .domain import ApprovalDecision, ApprovalRecord, ApprovalStatus, utc_now
from .storage import SQLiteStore

DEFAULT_CHOICES = [
    {"value": ApprovalDecision.APPROVE.value, "label": "Execute", "style": "approve"},
    {"value": ApprovalDecision.REJECT.value, "label": "Skip", "style": "reject"},
    {"value": ApprovalDecision.SNOOZE.value, "label": "Snooze", "style": "snooze"},
]


class InvalidApprovalToken(ValueError):
    """Raised when an approval token does not match storage."""


class InvalidApprovalDecision(ValueError):
    """Raised when a decision is not accepted by the MVP."""


@dataclass(frozen=True)
class CreatedApproval:
    """Approval plus raw token and URL returned once at creation time."""

    approval: ApprovalRecord
    token: str
    url: str


class ApprovalService:
    """Service layer for mobile approval records."""

    def __init__(self, store: SQLiteStore, public_base_url: str):
        self.store = store
        self.public_base_url = public_base_url.rstrip("/")

    def create_pending(
        self,
        *,
        run_id: str,
        title: str,
        summary: str,
        risk: str,
        recommendation: str,
        details: dict,
        ttl_seconds: int,
        choices: list[dict[str, str]] | None = None,
    ) -> CreatedApproval:
        """Create a pending approval and return its public URL."""

        normalized_choices = normalize_choices(choices)
        token = secrets.token_urlsafe(24)
        approval_id = "ACT-" + utc_now().strftime("%Y%m%d-") + secrets.token_hex(4).upper()
        expires_at = utc_now() + timedelta(seconds=ttl_seconds)
        self.store.create_approval(
            approval_id=approval_id,
            run_id=run_id,
            title=title,
            summary=summary,
            risk=risk,
            recommendation=recommendation,
            token_hash=hash_token(token),
            choices=normalized_choices,
            expires_at=expires_at,
            details=details,
        )
        self.store.append_event("approval", approval_id, "created", {"run_id": run_id, "risk": risk})
        approval = self.store.get_approval(approval_id)
        url = f"{self.public_base_url}/a/{approval_id}?{urlencode({'token': token})}"
        return CreatedApproval(approval=approval, token=token, url=url)

    def decide(self, approval_id: str, token: str, decision: str) -> ApprovalRecord:
        """Validate token and record a user decision."""

        approval = self.store.get_approval(approval_id)
        if not secrets.compare_digest(approval.token_hash, hash_token(token)):
            raise InvalidApprovalToken("Approval token is invalid")
        if approval.status != ApprovalStatus.PENDING:
            return approval
        if approval.expires_at and approval.expires_at < utc_now():
            self.store.decide_approval(approval_id, ApprovalStatus.EXPIRED, "expired")
            self.store.append_event("approval", approval_id, "expired", {})
            return self.store.get_approval(approval_id)

        normalized = decision.strip().lower()
        allowed_values = {choice["value"] for choice in approval.choices}
        if normalized not in allowed_values:
            raise InvalidApprovalDecision(f"Unsupported decision: {decision}")

        if normalized == ApprovalDecision.APPROVE.value:
            status = ApprovalStatus.APPROVED
        elif normalized == ApprovalDecision.REJECT.value:
            status = ApprovalStatus.REJECTED
        elif normalized == ApprovalDecision.SNOOZE.value:
            status = ApprovalStatus.SNOOZED
        else:
            raise InvalidApprovalDecision(f"Unsupported decision: {decision}")

        self.store.decide_approval(approval_id, status, normalized)
        self.store.append_event("approval", approval_id, "decided", {"decision": normalized})
        return self.store.get_approval(approval_id)


def hash_token(token: str) -> str:
    """Hash a URL token before storing it."""

    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def normalize_choices(choices: list[dict[str, str]] | None) -> list[dict[str, str]]:
    """Return safe approval choices with stable decision values and labels."""

    if not choices:
        return [dict(choice) for choice in DEFAULT_CHOICES]

    normalized: list[dict[str, str]] = []
    allowed = {item.value for item in ApprovalDecision}
    for item in choices:
        value = str(item.get("value") or "").strip().lower()
        if value not in allowed:
            raise InvalidApprovalDecision(f"Unsupported decision: {value}")
        label = str(item.get("label") or value).strip()
        style = str(item.get("style") or value).strip()
        normalized.append({"value": value, "label": label, "style": style})
    return normalized
