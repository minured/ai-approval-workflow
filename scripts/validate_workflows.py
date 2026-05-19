#!/usr/bin/env python3
"""Validate ai-approval-workflow YAML files without printing secrets.

The Codex skill and deployment checks use this helper before restarting the
service. It loads every root-level YAML file and reports workflow ids only.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Keep the helper runnable from a source checkout without requiring installation.
REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ai_approval_workflow.config import load_workflows  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate workflow YAML files.")
    parser.add_argument("workflows_dir", help="Directory containing workflow .yaml/.yml files")
    args = parser.parse_args()

    try:
        workflows = load_workflows(args.workflows_dir, include_disabled=True)
    except Exception as exc:  # noqa: BLE001 - CLI should return readable validation errors.
        print(str(exc), file=sys.stderr)
        return 1

    for workflow in workflows:
        state = "enabled" if workflow.enabled else "disabled"
        print(f"ok {workflow.id} {state} {Path(workflow.source_path or '').name}")
    print(f"validated {len(workflows)} workflow(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
