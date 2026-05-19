"""Tests for the root-side action runner script."""

import importlib.util
import json
from pathlib import Path


def load_runner_module():
    spec = importlib.util.spec_from_file_location("aaw_action_runner", Path("scripts/aaw_action_runner.py"))
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def write_request(queue_dir: Path, action: str) -> Path:
    pending = queue_dir / "pending"
    pending.mkdir(parents=True)
    request = pending / "request.json"
    request.write_text(
        json.dumps(
            {
                "request_id": "request",
                "action": action,
                "run_id": "run-1",
                "approval_id": "ACT-1",
                "workflow_id": "wf",
                "payload": {},
            }
        ),
        encoding="utf-8",
    )
    return request


def test_runner_moves_successful_action_to_done(tmp_path):
    runner = load_runner_module()
    script = tmp_path / "ok.sh"
    script.write_text("#!/bin/sh\necho upgraded\n", encoding="utf-8")
    script.chmod(0o755)
    config = tmp_path / "actions.yaml"
    config.write_text(
        f"""
queue_dir: {tmp_path / 'queue'}
actions:
  service_bundle_upgrade:
    command: ["{script}"]
    timeout_seconds: 5
""".strip(),
        encoding="utf-8",
    )
    write_request(tmp_path / "queue", "service_bundle_upgrade")

    result = runner.process_pending(config)

    done_files = list((tmp_path / "queue" / "done").glob("*.json"))
    assert result == {"processed": 1, "failed": 0}
    assert len(done_files) == 1
    payload = json.loads(done_files[0].read_text(encoding="utf-8"))
    assert payload["result"]["stdout"].strip() == "upgraded"


def test_runner_moves_unknown_action_to_failed(tmp_path):
    runner = load_runner_module()
    config = tmp_path / "actions.yaml"
    config.write_text(f"queue_dir: {tmp_path / 'queue'}\nactions: {{}}\n", encoding="utf-8")
    write_request(tmp_path / "queue", "not_allowed")

    result = runner.process_pending(config)

    failed_files = list((tmp_path / "queue" / "failed").glob("*.json"))
    assert result == {"processed": 1, "failed": 1}
    assert len(failed_files) == 1
    payload = json.loads(failed_files[0].read_text(encoding="utf-8"))
    assert "not allowlisted" in payload["result"]["stderr"]
