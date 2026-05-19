"""Allowlisted local commands and queued production actions.

The web app intentionally cannot run arbitrary shell text. Workflow YAML names a
command or action; this module resolves that name through root-managed config and
uses JSON queue files for privileged follow-up work.
"""

from __future__ import annotations

import json
import re
import subprocess
import uuid
from dataclasses import dataclass
from datetime import timezone
from pathlib import Path
from typing import Any

import yaml

from .domain import utc_now

SAFE_NAME_RE = re.compile(r"^[a-z0-9_][a-z0-9_-]{0,80}$")


class UnknownCommand(KeyError):
    """Raised when a workflow references a command not present in config."""


class UnknownAction(ValueError):
    """Raised when an action name is unsafe or not accepted by the queue."""


@dataclass(frozen=True)
class CommandResult:
    """Captured output from an allowlisted command_check step."""

    name: str
    returncode: int
    stdout: str
    stderr: str


class CommandRegistry:
    """Load and run named commands from a YAML allowlist."""

    def __init__(self, config_path: str | Path):
        self.config_path = Path(config_path) if str(config_path or "").strip() else None
        self._config = self._load_config()

    def run(self, name: str) -> CommandResult:
        """Run a named command and return captured output."""

        safe_name = _validate_name(name, UnknownCommand)
        raw_command = self._config.get("commands", {}).get(safe_name)
        if not isinstance(raw_command, dict):
            raise UnknownCommand(safe_name)

        command = raw_command.get("command")
        if not isinstance(command, list) or not command or not all(isinstance(item, str) for item in command):
            raise ValueError(f"Command {safe_name} must be a non-empty string list")

        timeout = int(raw_command.get("timeout_seconds") or 120)
        completed = subprocess.run(
            command,
            check=False,
            text=True,
            capture_output=True,
            timeout=timeout,
        )
        return CommandResult(
            name=safe_name,
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )

    def _load_config(self) -> dict[str, Any]:
        if self.config_path is None:
            return {}
        if not self.config_path.exists():
            return {}
        if not self.config_path.is_file():
            return {}
        raw = yaml.safe_load(self.config_path.read_text(encoding="utf-8")) or {}
        if not isinstance(raw, dict):
            raise ValueError(f"Action config must be a YAML object: {self.config_path}")
        return raw


class ActionQueue:
    """Write approved action requests into a pending queue directory."""

    def __init__(self, queue_dir: str | Path):
        self.queue_dir = Path(queue_dir)

    def enqueue(
        self,
        *,
        action: str,
        run_id: str,
        approval_id: str,
        workflow_id: str,
        payload: dict[str, Any] | None = None,
    ) -> Path:
        """Create one pending action JSON file using atomic rename."""

        safe_action = _validate_name(action, UnknownAction)
        pending_dir = self.queue_dir / "pending"
        pending_dir.mkdir(parents=True, exist_ok=True)

        now = utc_now().astimezone(timezone.utc)
        request_id = f"{now.strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex}"
        request = {
            "request_id": request_id,
            "action": safe_action,
            "run_id": run_id,
            "approval_id": approval_id,
            "workflow_id": workflow_id,
            "payload": payload or {},
            "created_at": now.isoformat(),
        }

        tmp_path = pending_dir / f".{request_id}.tmp"
        final_path = pending_dir / f"{request_id}.json"
        tmp_path.write_text(json.dumps(request, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp_path.replace(final_path)
        return final_path


def _validate_name(name: str, error_type: type[Exception]) -> str:
    safe_name = str(name or "").strip()
    if not SAFE_NAME_RE.match(safe_name):
        raise error_type(safe_name)
    return safe_name
