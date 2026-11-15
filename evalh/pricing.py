from __future__ import annotations

from pathlib import Path

import yaml

PRICES_PATH = Path(__file__).resolve().parent.parent / "prices.yaml"


class PricingError(ValueError):
    pass


def _load_table() -> dict:
    return yaml.safe_load(PRICES_PATH.read_text()) or {}


def cost_usd(provider: str, model: str, tokens_in: int, tokens_out: int) -> float:
    """Cost of one call, from prices.yaml. Local (ollama) calls always cost $0."""
    if provider == "ollama":
        return 0.0

    table = _load_table()
    provider_prices = table.get(provider)
    if provider_prices is None or model not in provider_prices:
        raise PricingError(
            f"no price entry for provider={provider!r} model={model!r} in {PRICES_PATH}"
        )
    rates = provider_prices[model]
    return (tokens_in * rates["input_per_1m"] + tokens_out * rates["output_per_1m"]) / 1_000_000
