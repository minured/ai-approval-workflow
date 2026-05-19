"""Tests for outbound notification and AI fallback clients."""

import httpx
import pytest

from ai_approval_workflow.ai import AIClient
from ai_approval_workflow.notify import NotificationClient


@pytest.mark.asyncio
async def test_notification_client_posts_json_payload():
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"ok": True, "status": "sent"})

    client = NotificationClient(
        webhook_url="https://notify.example/simple/secret",
        bearer_token="",
        source="ai-approval-workflow",
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )

    result = await client.send(title="Title", content="Body", channel="ops-default", severity="info")
    await client.aclose()

    assert result["status"] == "sent"
    assert requests[0].headers["content-type"] == "application/json"
    assert requests[0].read()


@pytest.mark.asyncio
async def test_notification_client_noops_without_url():
    client = NotificationClient(webhook_url="", bearer_token="", source="test")
    result = await client.send(title="Title", content="Body", channel="ops-default", severity="info")
    await client.aclose()
    assert result == {"ok": True, "status": "disabled"}


@pytest.mark.asyncio
async def test_ai_client_uses_fallback_without_api_key():
    client = AIClient(base_url="", api_key="", model="test-model")
    summary = await client.summarize("hello")
    await client.aclose()
    assert "AI summary fallback" in summary
    assert "hello" in summary


@pytest.mark.asyncio
async def test_ai_client_can_disable_fallback_without_api_key():
    """Production deployments can fail fast instead of notifying raw source text."""

    client = AIClient(base_url="", api_key="", model="test-model", fallback_enabled=False)

    with pytest.raises(ValueError, match="AI configuration is required"):
        await client.summarize("private source material")

    await client.aclose()
