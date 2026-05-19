"""Shared pytest fixtures for ai-approval-workflow."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ai_approval_workflow.config import AppSettings
from ai_approval_workflow.main import create_app


@pytest.fixture
def test_settings(tmp_path: Path) -> AppSettings:
    return AppSettings(
        _env_file=None,
        database_path=str(tmp_path / "app.db"),
        workflows_dir=str(tmp_path / "workflows"),
        scheduler_enabled=False,
        public_base_url="http://testserver",
        notification_webhook_url="",
    )


@pytest.fixture
def client(test_settings: AppSettings) -> TestClient:
    app = create_app(test_settings)
    with TestClient(app) as test_client:
        yield test_client
