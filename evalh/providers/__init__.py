from __future__ import annotations

from evalh.providers.base import Provider

_INSTANCES: dict[str, Provider] = {}


def get_provider(name: str) -> Provider:
    """Return a cached provider instance so each one's client is built once."""
    if name not in _INSTANCES:
        if name == "openai":
            from evalh.providers.openai_provider import OpenAIProvider as cls
        elif name == "anthropic":
            from evalh.providers.anthropic_provider import AnthropicProvider as cls
        elif name == "ollama":
            from evalh.providers.ollama_provider import OllamaProvider as cls
        else:
            raise ValueError(f"unknown provider {name!r}; expected openai, anthropic or ollama")
        _INSTANCES[name] = cls()
    return _INSTANCES[name]


__all__ = ["Provider", "get_provider"]
