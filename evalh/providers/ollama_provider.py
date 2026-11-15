from __future__ import annotations

import os
import time

import httpx

from evalh.models import ProviderResponse
from evalh.providers.base import Provider


class OllamaProvider(Provider):
    """Zero-cost local inference via a running Ollama server."""

    def __init__(self) -> None:
        self._host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")

    async def complete(
        self, *, model: str, prompt: str, temperature: float, max_tokens: int
    ) -> ProviderResponse:
        start = time.perf_counter()
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                f"{self._host}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": temperature, "num_predict": max_tokens},
                },
            )
            response.raise_for_status()
            data = response.json()
        latency_ms = (time.perf_counter() - start) * 1000
        return ProviderResponse(
            text=data.get("response", ""),
            tokens_in=data.get("prompt_eval_count", 0),
            tokens_out=data.get("eval_count", 0),
            latency_ms=latency_ms,
        )
