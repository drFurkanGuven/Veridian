from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

from veridian_api.core.config import Settings


class OpenAiClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def stream_chat(self, messages: list[dict[str, str]]) -> AsyncIterator[str]:
        if not self._settings.ai_enabled:
            yield (
                "Veridian AI is not configured on this server. "
                "Set OPENAI_API_KEY in the API environment to enable assistance."
            )
            return

        headers = {
            "Authorization": f"Bearer {self._settings.openai_api_key}",
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "model": self._settings.ai_model,
            "messages": messages,
            "stream": True,
            "temperature": 0.2,
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    data = line[6:].strip()
                    if data == "[DONE]":
                        break
                    chunk = json.loads(data)
                    delta = chunk["choices"][0].get("delta", {})
                    content = delta.get("content")
                    if content:
                        yield str(content)
