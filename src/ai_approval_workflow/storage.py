"""SQLite storage for workflow runs, approvals, and audit events."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .domain import ApprovalRecord, ApprovalStatus, RunStatus, utc_now


class SQLiteStore:
    """Small SQLite repository used by the MVP runtime."""

    def __init__(self, database_path: str | Path):
        self.database_path = Path(database_path)

    def connect(self) -> sqlite3.Connection:
        """Open a SQLite connection with dict-like row access."""

        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.database_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self) -> None:
        """Create required tables if they do not exist."""

        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS workflow_runs (
                    run_id TEXT PRIMARY KEY,
                    workflow_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    result_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS approvals (
                    approval_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    risk TEXT NOT NULL,
                    recommendation TEXT NOT NULL,
                    status TEXT NOT NULL,
                    token_hash TEXT NOT NULL,
                    choices_json TEXT NOT NULL,
                    expires_at TEXT,
                    details_json TEXT NOT NULL DEFAULT '{}',
                    decision TEXT,
                    decided_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(run_id) REFERENCES workflow_runs(run_id)
                );

                CREATE TABLE IF NOT EXISTS audit_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )

    def create_run(self, workflow_id: str) -> str:
        """Create a workflow run and return its id."""

        run_id = uuid.uuid4().hex
        now = _dt(utc_now())
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO workflow_runs (run_id, workflow_id, status, result_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (run_id, workflow_id, RunStatus.CREATED.value, "{}", now, now),
            )
        return run_id

    def update_run_status(self, run_id: str, status: RunStatus, result: dict[str, Any] | None = None) -> None:
        """Update a workflow run status and optional result."""

        with self.connect() as conn:
            conn.execute(
                """
                UPDATE workflow_runs
                SET status = ?, result_json = ?, updated_at = ?
                WHERE run_id = ?
                """,
                (status.value, _json(result or {}), _dt(utc_now()), run_id),
            )

    def get_run(self, run_id: str) -> dict[str, Any]:
        """Return one workflow run as a plain dictionary."""

        with self.connect() as conn:
            row = conn.execute("SELECT * FROM workflow_runs WHERE run_id = ?", (run_id,)).fetchone()
        if row is None:
            raise KeyError(f"Run not found: {run_id}")
        data = dict(row)
        data["result"] = json.loads(data.pop("result_json"))
        return data

    def create_approval(
        self,
        *,
        approval_id: str,
        run_id: str,
        title: str,
        summary: str,
        risk: str,
        recommendation: str,
        token_hash: str,
        choices: list[dict[str, str]],
        expires_at: datetime | None,
        details: dict[str, Any],
    ) -> str:
        """Persist a pending approval request."""

        now = _dt(utc_now())
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO approvals (
                    approval_id, run_id, title, summary, risk, recommendation, status,
                    token_hash, choices_json, expires_at, details_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    approval_id,
                    run_id,
                    title,
                    summary,
                    risk,
                    recommendation,
                    ApprovalStatus.PENDING.value,
                    token_hash,
                    _json(choices),
                    _dt(expires_at) if expires_at else None,
                    _json(details),
                    now,
                    now,
                ),
            )
        return approval_id

    def get_approval(self, approval_id: str) -> ApprovalRecord:
        """Return one approval request."""

        with self.connect() as conn:
            row = conn.execute("SELECT * FROM approvals WHERE approval_id = ?", (approval_id,)).fetchone()
        if row is None:
            raise KeyError(f"Approval not found: {approval_id}")
        return _approval_from_row(row)

    def decide_approval(self, approval_id: str, status: ApprovalStatus, decision: str) -> None:
        """Store a final or snoozed decision for an approval."""

        now = _dt(utc_now())
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE approvals
                SET status = ?, decision = ?, decided_at = ?, updated_at = ?
                WHERE approval_id = ?
                """,
                (status.value, decision, now, now, approval_id),
            )

    def append_event(self, entity_type: str, entity_id: str, event_type: str, payload: dict[str, Any]) -> None:
        """Append an audit event."""

        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO audit_events (entity_type, entity_id, event_type, payload_json, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (entity_type, entity_id, event_type, _json(payload), _dt(utc_now())),
            )

    def list_events(self, entity_type: str, entity_id: str) -> list[dict[str, Any]]:
        """List audit events for one entity."""

        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM audit_events
                WHERE entity_type = ? AND entity_id = ?
                ORDER BY id ASC
                """,
                (entity_type, entity_id),
            ).fetchall()
        events: list[dict[str, Any]] = []
        for row in rows:
            data = dict(row)
            data["payload"] = json.loads(data.pop("payload_json"))
            events.append(data)
        return events


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _dt(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value)


def _approval_from_row(row: sqlite3.Row) -> ApprovalRecord:
    data = dict(row)
    created_at = _parse_dt(data["created_at"])
    updated_at = _parse_dt(data["updated_at"])
    if created_at is None or updated_at is None:
        raise ValueError("Approval timestamps are required")
    return ApprovalRecord(
        approval_id=data["approval_id"],
        run_id=data["run_id"],
        title=data["title"],
        summary=data["summary"],
        risk=data["risk"],
        recommendation=data["recommendation"],
        status=ApprovalStatus(data["status"]),
        token_hash=data["token_hash"],
        choices=_parse_choices(data["choices_json"]),
        expires_at=_parse_dt(data["expires_at"]),
        details=json.loads(data["details_json"]),
        created_at=created_at,
        updated_at=updated_at,
        decision=data["decision"],
        decided_at=_parse_dt(data["decided_at"]),
    )


def _parse_choices(raw_json: str) -> list[dict[str, str]]:
    raw = json.loads(raw_json)
    if not isinstance(raw, list):
        return []

    choices: list[dict[str, str]] = []
    for item in raw:
        if isinstance(item, str):
            choices.append({"value": item, "label": item, "style": item})
        elif isinstance(item, dict):
            value = str(item.get("value") or "")
            choices.append(
                {
                    "value": value,
                    "label": str(item.get("label") or value),
                    "style": str(item.get("style") or value),
                }
            )
    return choices
