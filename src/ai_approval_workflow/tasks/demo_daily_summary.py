"""Safe demo summary task used by the MVP workflow."""

from __future__ import annotations

from datetime import timezone
from typing import Any

from ai_approval_workflow.domain import utc_now


def run_demo_summary(config: dict[str, Any]) -> dict[str, Any]:
    """Return deterministic demo data without touching external systems."""

    subject = str(config.get("subject") or "Daily demo summary")
    now = utc_now().astimezone(timezone.utc).isoformat()
    return {
        "subject": subject,
        "observed_at": now,
        "summary": f"{subject}: demo workflow collected safe sample data at {now}.",
        "risk": "low",
    }
