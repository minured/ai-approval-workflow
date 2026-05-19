"""OpenAI-compatible summarization client with configurable fallback behavior."""

from __future__ import annotations

import httpx


class AIClient:
    """Small OpenAI-compatible chat completions wrapper."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: float = 30,
        fallback_enabled: bool = True,
        http_client: httpx.AsyncClient | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key.strip()
        self.model = model
        # Keep the timeout visible for diagnostics and tests; production
        # deployments can raise it for longer summaries without code changes.
        self.timeout_seconds = timeout_seconds
        # Local demos can use deterministic fallback text, while production
        # deployments can disable it to avoid sending raw source material.
        self.fallback_enabled = fallback_enabled
        self.http_client = http_client or httpx.AsyncClient(timeout=timeout_seconds)

    async def summarize(self, text: str) -> str:
        """Summarize text with AI, or return deterministic fallback text."""

        clean = text.strip()
        if not self.base_url or not self.api_key:
            if not self.fallback_enabled:
                raise ValueError("AI configuration is required but AAW_AI_BASE_URL or AAW_AI_API_KEY is missing.")
            return f"AI summary fallback: {clean[:500]}"

        response = await self.http_client.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "你是一个简洁的工作流审批摘要助手。"},
                    {"role": "user", "content": clean},
                ],
                "temperature": 0.2,
            },
        )
        response.raise_for_status()
        payload = response.json()
        return str(payload["choices"][0]["message"]["content"]).strip()

    async def aclose(self) -> None:
        """Close the underlying async HTTP client."""

        await self.http_client.aclose()
