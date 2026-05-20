"""OpenAI-compatible summarization client with configurable fallback behavior."""

from __future__ import annotations

import httpx


def normalize_max_chars(max_chars: int | None) -> int:
    """Return a safe positive message length limit, or 0 when disabled."""

    if max_chars is None:
        return 0
    return max(0, int(max_chars))


def clamp_text(text: str, max_chars: int | None) -> str:
    """Last-resort character clamp for outbound AI-generated text."""

    limit = normalize_max_chars(max_chars)
    if not limit or len(text) <= limit:
        return text
    if limit == 1:
        return "…"
    return text[: limit - 1].rstrip() + "…"


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

    async def summarize(self, text: str, max_chars: int | None = None) -> str:
        """Summarize text with AI, or return deterministic fallback text."""

        limit = normalize_max_chars(max_chars)
        clean = text.strip()
        if not self.base_url or not self.api_key:
            if not self.fallback_enabled:
                raise ValueError("AI configuration is required but AAW_AI_BASE_URL or AAW_AI_API_KEY is missing.")
            return clamp_text(f"AI summary fallback: {clean[:500]}", limit)

        summary = await self._complete_chat(self._append_message_limit(clean, limit))
        if limit and len(summary) > limit:
            summary = await self._complete_chat(self._build_compression_prompt(summary, limit))
        return clamp_text(summary, limit)

    async def _complete_chat(self, text: str) -> str:
        """Call an OpenAI-compatible chat completions endpoint once."""

        response = await self.http_client.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "你是一个简洁的工作流审批摘要助手。"},
                    {"role": "user", "content": text},
                ],
                "temperature": 0.2,
            },
        )
        response.raise_for_status()
        payload = response.json()
        return str(payload["choices"][0]["message"]["content"]).strip()

    def _append_message_limit(self, text: str, max_chars: int) -> str:
        """Append a hard output budget to the user prompt when configured."""

        if not max_chars:
            return text
        return "\n\n".join(
            [
                text,
                (
                    "硬性输出限制：最终用于通知或审批摘要的消息正文必须不超过 "
                    f"{max_chars} 个字。优先保留结论、关键变化和必要动作；不要输出解释、长列表或原始材料。"
                ),
            ]
        ).strip()

    def _build_compression_prompt(self, summary: str, max_chars: int) -> str:
        """Build a retry prompt that asks the model to compress its own output."""

        return "\n".join(
            [
                f"你上一次输出超过 {max_chars} 个字。",
                f"请把下面内容改写成不超过 {max_chars} 个字的最终消息正文。",
                "只输出改写后的正文，不要解释，不要保留长列表。",
                "",
                summary,
            ]
        )

    async def aclose(self) -> None:
        """Close the underlying async HTTP client."""

        await self.http_client.aclose()
