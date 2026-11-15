from __future__ import annotations

import os
import time

from anthropic import AsyncAnthropic

from evalh.models import ProviderResponse
from evalh.providers.base import Provider


class AnthropicProvider(Provider):
    def __init__(self) -> None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set (check your .env file)")
        self._client = AsyncAnthropic(api_key=api_key)

    async def complete(
        self, *, model: str, prompt: str, temperature: float, max_tokens: int
    ) -> ProviderResponse:
        start = time.perf_counter()
        response = await self._client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}],
        )
        latency_ms = (time.perf_counter() - start) * 1000
        text = "".join(block.text for block in response.content if block.type == "text")
        return ProviderResponse(
            text=text,
            tokens_in=response.usage.input_tokens,
            tokens_out=response.usage.output_tokens,
            latency_ms=latency_ms,
        )
