"""Tests for allowlisted commands and queued production actions."""

import json
from pathlib import Path

import pytest

from ai_approval_workflow.actions import ActionQueue, CommandRegistry, UnknownAction, UnknownCommand


def test_command_registry_runs_allowlisted_command(tmp_path):
    """Only named commands from the YAML config should run."""

    script = tmp_path / "check.sh"
    script.write_text("#!/bin/sh\necho service=v1\n", encoding="utf-8")
    script.chmod(0o755)
    config = tmp_path / "actions.yaml"
    config.write_text(
        f"""
commands:
  service_version_check:
    command: ["{script}"]
    timeout_seconds: 5
""".strip(),
        encoding="utf-8",
    )

    registry = CommandRegistry(config)
    result = registry.run("service_version_check")

    assert result.name == "service_version_check"
    assert result.returncode == 0
    assert result.stdout.strip() == "service=v1"


def test_command_registry_rejects_unknown_command(tmp_path):
    config = tmp_path / "actions.yaml"
    config.write_text("commands: {}\n", encoding="utf-8")

    with pytest.raises(UnknownCommand):
        CommandRegistry(config).run("not-allowed")


def test_action_queue_writes_pending_json_atomically(tmp_path):
    queue = ActionQueue(tmp_path)

    path = queue.enqueue(
        action="service_bundle_upgrade",
        run_id="run-1",
        approval_id="ACT-1",
        workflow_id="service-upgrade-watch",
        payload={"target": "latest"},
    )

    assert path.parent == tmp_path / "pending"
    assert path.suffix == ".json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["action"] == "service_bundle_upgrade"
    assert payload["run_id"] == "run-1"
    assert payload["payload"] == {"target": "latest"}


def test_action_queue_rejects_bad_action_name(tmp_path):
    queue = ActionQueue(tmp_path)

    with pytest.raises(UnknownAction):
        queue.enqueue(action="../../bad", run_id="run-1", approval_id="ACT-1", workflow_id="wf", payload={})
