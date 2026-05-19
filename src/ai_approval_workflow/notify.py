"""Outbound notification client for generic webhook delivery."""

from __future__ import annotations

from typing import Any

import httpx


class NotificationClient:
    """Send approval and result messages to a configured HTTP webhook."""

    def __init__(
        self,
        *,
        webhook_url: str,
        bearer_token: str,
        source: str,
        http_client: httpx.AsyncClient | None = None,
    ):
        self.webhook_url = webhook_url.strip()
        self.bearer_token = bearer_token.strip()
        self.source = source
        self.http_client = http_client or httpx.AsyncClient(timeout=15)

    async def send(self, *, title: str, content: str, channel: str, severity: str = "info") -> dict[str, Any]:
        """Send a notification or no-op when no webhook is configured."""

        if not self.webhook_url:
            return {"ok": True, "status": "disabled"}

        headers = {"Content-Type": "application/json"}
        if self.bearer_token:
            headers["Authorization"] = f"Bearer {self.bearer_token}"

        payload = {
            "title": title,
            "content": content,
            "message": content,
            "source": self.source,
            "channel": channel,
            "severity": severity,
        }
        response = await self.http_client.post(self.webhook_url, json=payload, headers=headers)
        response.raise_for_status()
        try:
            return response.json()
        except ValueError:
            return {"ok": True, "status": "sent", "body": response.text}

    async def aclose(self) -> None:
        """Close the underlying async HTTP client."""

        await self.http_client.aclose()
