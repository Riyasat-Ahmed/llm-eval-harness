from __future__ import annotations

from abc import ABC, abstractmethod

from evalh.models import ProviderResponse


class Provider(ABC):
    """A thin async wrapper around one API. Must return text, token counts and
    latency in the same shape regardless of the underlying SDK."""

    @abstractmethod
    async def complete(
        self, *, model: str, prompt: str, temperature: float, max_tokens: int
    ) -> ProviderResponse: ...
