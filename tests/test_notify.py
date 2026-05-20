"""Tests for outbound notification and AI fallback clients."""

import json

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


@pytest.mark.asyncio
async def test_ai_client_instructs_and_reasks_when_summary_exceeds_message_limit():
    """AI output should be constrained at generation time before notifying users."""

    requests = []
    responses = [
        "这是一段明显超过十个字的长摘要",
        "短摘要",
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(json.loads(request.content))
        return httpx.Response(200, json={"choices": [{"message": {"content": responses.pop(0)}}]})

    client = AIClient(
        base_url="https://ai.example/v1",
        api_key="test-key",
        model="test-model",
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )

    summary = await client.summarize("source material", max_chars=10)
    await client.aclose()

    assert summary == "短摘要"
    assert len(requests) == 2
    assert "不超过 10 个字" in requests[0]["messages"][-1]["content"]
    assert "你上一次输出超过 10 个字" in requests[1]["messages"][-1]["content"]


@pytest.mark.asyncio
async def test_ai_client_last_resort_clamps_second_overlong_response():
    """If a model ignores the retry instruction, the client still prevents long AI messages."""

    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"choices": [{"message": {"content": "1234567890"}}]})

    client = AIClient(
        base_url="https://ai.example/v1",
        api_key="test-key",
        model="test-model",
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )

    summary = await client.summarize("source material", max_chars=6)
    await client.aclose()

    assert summary == "12345…"
    assert len(requests) == 2
