"""Tests for APScheduler workflow registration."""

from ai_approval_workflow.config import load_workflow_file
from ai_approval_workflow.scheduler import build_scheduler


def test_build_scheduler_registers_enabled_schedule(tmp_path):
    path = tmp_path / "workflow.yaml"
    path.write_text(
        """
id: demo
enabled: true
trigger: {type: schedule, cron: "*/5 * * * *", timezone: UTC}
steps: [{id: collect, type: demo_summary}]
""".strip(),
        encoding="utf-8",
    )
    workflow = load_workflow_file(path)
    scheduler = build_scheduler([workflow], run_workflow=lambda workflow: None)

    jobs = scheduler.get_jobs()

    assert len(jobs) == 1
    assert jobs[0].id == "workflow:demo"
