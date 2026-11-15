from __future__ import annotations

import os
import time

from openai import AsyncOpenAI

from evalh.models import ProviderResponse
from evalh.providers.base import Provider


class OpenAIProvider(Provider):
    def __init__(self) -> None:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set (check your .env file)")
        self._client = AsyncOpenAI(api_key=api_key)

    async def complete(
        self, *, model: str, prompt: str, temperature: float, max_tokens: int
    ) -> ProviderResponse:
        start = time.perf_counter()
        response = await self._client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        latency_ms = (time.perf_counter() - start) * 1000
        choice = response.choices[0]
        usage = response.usage
        return ProviderResponse(
            text=choice.message.content or "",
            tokens_in=usage.prompt_tokens if usage else 0,
            tokens_out=usage.completion_tokens if usage else 0,
            latency_ms=latency_ms,
        )
