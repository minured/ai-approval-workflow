#!/usr/bin/env python3
"""Root-side action runner for ai-approval-workflow.

The FastAPI app only writes approved JSON requests. This runner validates each
request against a root-owned allowlist before executing one fixed command.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

SAFE_NAME_RE = re.compile(r"^[a-z0-9_][a-z0-9_-]{0,80}$")


def process_pending(config_path: str | Path) -> dict[str, int]:
    """Process all pending action requests and return counters."""

    config = _load_config(config_path)
    queue_dir = Path(config.get("queue_dir") or "/var/lib/ai-approval-workflow/actions")
    pending_dir = queue_dir / "pending"
    running_dir = queue_dir / "running"
    done_dir = queue_dir / "done"
    failed_dir = queue_dir / "failed"
    for directory in [pending_dir, running_dir, done_dir, failed_dir]:
        directory.mkdir(parents=True, exist_ok=True)

    processed = 0
    failed = 0
    for pending_path in sorted(pending_dir.glob("*.json")):
        processed += 1
        running_path = running_dir / pending_path.name
        pending_path.replace(running_path)
        try:
            envelope = json.loads(running_path.read_text(encoding="utf-8"))
            result = _run_one(envelope, config, running_path)
            envelope["result"] = result
            envelope["finished_at"] = _now()
            target_dir = done_dir if result["returncode"] == 0 else failed_dir
            if result["returncode"] != 0:
                failed += 1
            _write_final(envelope, target_dir / running_path.name)
            running_path.unlink(missing_ok=True)
            _notify(config, envelope)
        except Exception as exc:  # noqa: BLE001 - runner must preserve failed requests.
            failed += 1
            envelope = _safe_envelope(running_path)
            envelope["result"] = {"returncode": 1, "stdout": "", "stderr": str(exc)}
            envelope["finished_at"] = _now()
            _write_final(envelope, failed_dir / running_path.name)
            running_path.unlink(missing_ok=True)
            _notify(config, envelope)
    return {"processed": processed, "failed": failed}


def _run_one(envelope: dict[str, Any], config: dict[str, Any], request_path: Path) -> dict[str, Any]:
    action = str(envelope.get("action") or "")
    if not SAFE_NAME_RE.match(action):
        return {"returncode": 1, "stdout": "", "stderr": f"Unsafe action name: {action}"}

    raw_action = (config.get("actions") or {}).get(action)
    if not isinstance(raw_action, dict):
        return {"returncode": 1, "stdout": "", "stderr": f"Action not allowlisted: {action}"}

    command = raw_action.get("command")
    if not isinstance(command, list) or not command or not all(isinstance(item, str) for item in command):
        return {"returncode": 1, "stdout": "", "stderr": f"Invalid command for action: {action}"}

    timeout = int(raw_action.get("timeout_seconds") or 1800)
    env = os.environ.copy()
    env["AAW_ACTION_REQUEST"] = str(request_path)
    completed = subprocess.run(command, check=False, text=True, capture_output=True, timeout=timeout, env=env)
    return {"returncode": completed.returncode, "stdout": completed.stdout, "stderr": completed.stderr}


def _notify(config: dict[str, Any], envelope: dict[str, Any]) -> None:
    notify_command = config.get("notify_command")
    if not isinstance(notify_command, list) or not notify_command:
        return
    if not all(isinstance(item, str) for item in notify_command):
        return

    result = envelope.get("result") or {}
    status = "成功" if result.get("returncode") == 0 else "失败"
    title = f"AI审批动作{status}: {envelope.get('action')}"
    body = "\n".join(
        [
            f"request_id: {envelope.get('request_id')}",
            f"workflow: {envelope.get('workflow_id')}",
            f"returncode: {result.get('returncode')}",
            "",
            str(result.get("stdout") or result.get("stderr") or "")[-3500:],
        ]
    )
    subprocess.run([*notify_command, title, body], check=False, timeout=60)


def _load_config(config_path: str | Path) -> dict[str, Any]:
    path = Path(config_path)
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"Config must be a YAML object: {path}")
    return raw


def _write_final(envelope: dict[str, Any], target_path: Path) -> None:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    if target_path.exists():
        target_path = target_path.with_name(f"{target_path.stem}-{uuid.uuid4().hex}{target_path.suffix}")
    target_path.write_text(json.dumps(envelope, ensure_ascii=False, indent=2), encoding="utf-8")


def _safe_envelope(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 - corrupted request still needs a failure record.
        return {"request_id": path.stem, "action": "unknown", "workflow_id": "unknown"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> int:
    parser = argparse.ArgumentParser(description="Process ai-approval-workflow queued actions.")
    parser.add_argument("--config", default="/etc/ai-approval-workflow/actions.yaml")
    args = parser.parse_args()
    result = process_pending(args.config)
    print(json.dumps(result, ensure_ascii=False))
    return 1 if result["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
